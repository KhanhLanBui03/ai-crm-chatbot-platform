"""Thử LLM thật trên 10 câu của bộ vàng, đi ĐÚNG đường production ``RagAnswerer``. [R&D]

    cd ai-service && source .venv/bin/activate
    AI_MODE=remote EMBED_URL=http://localhost:8091 python -m tests.eval.thu_llm
    python -m tests.eval.thu_llm --model gemini-3.5-flash-lite      # nếu 3.8 Flash quá 2.500 ms

Mục đích (kế hoạch 08/10, bước 5b): kiểm model đã chọn có đạt yêu cầu tiếng Việt + trích dẫn +
độ trễ không, TRƯỚC khi dựng phần còn lại lên trên nó. KHÔNG phải phép đo chất lượng của đồ án —
10 câu quá ít để báo một tỉ lệ; số chính thức là eval Ngày 13 trên ≥ 80 câu.

CHỌN CÂU — tất định, seed 42
---------------------------
8 câu có đáp án: mỗi kiểu gõ khác ``co_dau`` một câu (không dấu, viết tắt, dài, tiếng Anh), rồi
mỗi loại câu hỏi chưa có một câu, rồi bù bằng câu có dấu cho đủ 8. Thêm 2 câu KHÔNG có trong kho
(``can_cu: []``) để xem mô hình có chịu trả ``KHONG_DU_CAN_CU`` không. Bộ vàng chỉ đọc — đã đóng
băng (sha256 in trong báo cáo).

HẠN CHÓT 10 S, KHÔNG PHẢI 2,5 S
-------------------------------
Để thấy độ trễ THẬT của model. Với hạn 2,5 s, câu chậm thành câu suy giảm và ta mất luôn câu trả
lời lẫn con số. Báo cáo ghi riêng bao nhiêu câu nằm trong ngân sách 2.500 ms.

HẠN MỨC: bậc miễn phí Gemini 3.8 Flash cho 20 lượt/ngày; mỗi câu tối đa 1 lượt (câu bị sàn liên
quan chặn thì 0 lượt). Giãn ``--gian-s`` giây giữa hai lượt để né giới hạn mỗi phút.
"""

import argparse
import asyncio
import hashlib
import json
import random
import time
import uuid
from datetime import datetime
from pathlib import Path

from src.ai.config import Settings
from src.ai.inference.clients import KetQuaNhung, tao_embed_client
from src.ai.integrations.llm import CircuitBreaker, LLMChiuLoi, tao_llm_client
from src.ai.rag.answerer import RagAnswerer, truy_hoi_csdl
from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from src.ai.schemas import ChatRequest
from tests.eval.bo_vang import de_so

BO_VANG = Path(__file__).resolve().parent / "golden_set.jsonl"
THU_MUC_BAO_CAO = Path(__file__).resolve().parent / "reports"
TENANT = "eeeeeeee-0000-0000-0000-000000000001"  # tenant gốc của gieo_kho.py, như e3_hybrid.yaml
NGAN_SACH_MS = 2500
SEED = 42


def chon_cau(dong: list[dict], so_co_dap_an: int = 8, so_ngoai_kho: int = 2) -> list[dict]:
    rng = random.Random(SEED)
    co = [d for d in dong if d["can_cu"]]
    khong = [d for d in dong if not d["can_cu"]]
    rng.shuffle(co)
    rng.shuffle(khong)
    chon: list[dict] = []

    def lay(dieu_kien) -> None:
        for d in co:
            if d not in chon and dieu_kien(d):
                chon.append(d)
                return

    loai_da_co = lambda: {d["loai"] for d in chon}  # noqa: E731
    for kieu in ("khong_dau", "viet_tat", "dai", "tieng_anh"):
        truoc = len(chon)
        # Ưu tiên câu thuộc loại chưa có, để 8 câu phủ được cả kiểu gõ lẫn loại câu hỏi.
        lay(lambda d, k=kieu: d["kieu_go"] == k and d["loai"] not in loai_da_co())
        if len(chon) == truoc:
            lay(lambda d, k=kieu: d["kieu_go"] == k)
    for loai in sorted({d["loai"] for d in co}):
        if loai not in loai_da_co():
            lay(lambda d, lo=loai: d["loai"] == lo)
    while len(chon) < so_co_dap_an:
        lay(lambda d: d["kieu_go"] == "co_dau")
    return chon[:so_co_dap_an] + khong[:so_ngoai_kho]


def _dung(doan: DoanTimDuoc, can_cu: list[dict]) -> bool:
    noi_dung = de_so(doan.content)
    return any(doan.file_name == c["file"] and de_so(c["quote"]) in noi_dung for c in can_cu)


async def chay(model: str, gian_s: float, han_chot_s: float) -> Path:
    dong = [json.loads(x) for x in BO_VANG.read_text(encoding="utf-8").splitlines() if x.strip()]
    cac_cau = chon_cau(dong)
    settings = Settings(llm_mode="remote", llm_model=model)

    # Đoạn mà lượt vừa rồi lấy về — trích dẫn chỉ mang chunk_id, cần nội dung + tệp để chấm.
    lan_cuoi: list[DoanTimDuoc] = []

    async def truy_hoi_ghi_lai(tenant_id: str, cau_hoi: str, nhung: KetQuaNhung, k: int):
        ket_qua = await truy_hoi_csdl(tenant_id, cau_hoi, nhung, k)
        lan_cuoi[:] = ket_qua
        return ket_qua

    llm_client = tao_llm_client(settings)
    tra_loi = RagAnswerer(
        embed=tao_embed_client(settings),
        # Mạch rộng tay: phép thử muốn thấy từng lỗi, không muốn mạch mở rồi nuốt các câu sau.
        llm=LLMChiuLoi(llm_client, CircuitBreaker(nguong_hong=100), han_chot_s=han_chot_s),
        settings=settings,
        truy_hoi=truy_hoi_ghi_lai,
    )

    ket_qua: list[dict] = []
    so_luot = 0
    try:
        for i, cau in enumerate(cac_cau):
            if so_luot and gian_s:
                await asyncio.sleep(gian_s)
            req = ChatRequest(conversation_id=uuid.uuid4(), message=cau["question"])
            bat_dau = time.perf_counter()
            kq = await tra_loi.answer(tenant_id=TENANT, question=cau["question"], request=req)
            tong_ms = int((time.perf_counter() - bat_dau) * 1000)
            so_luot += int(kq.llm_called)
            lay_ve = list(lan_cuoi)
            theo_id = {d.chunk_id: d for d in lay_ve}
            trich = [theo_id[c.chunk_id] for c in kq.citations if c.chunk_id in theo_id]
            dong_kq = {
                "id": cau["id"],
                "loai": cau["loai"],
                "kieu_go": cau["kieu_go"],
                "question": cau["question"],
                "co_dap_an": bool(cau["can_cu"]),
                "answer": kq.answer,
                "refused": kq.refused,
                "degraded": kq.degraded,
                "llm_called": kq.llm_called,
                "so_trich_dan": len(kq.citations),
                "truy_hoi_trung": any(_dung(d, cau["can_cu"]) for d in lay_ve),
                "trich_dung_can_cu": any(_dung(d, cau["can_cu"]) for d in trich),
                "groundedness": kq.groundedness_score,
                "retrieval_top": round(kq.retrieval_top_score or 0, 3),
                "generate_ms": kq.latency_breakdown.get("generate_ms"),
                "tong_ms": tong_ms,
                "prompt_tokens": kq.prompt_tokens,
                "completion_tokens": kq.completion_tokens,
            }
            ket_qua.append(dong_kq)
            print(f"[{i + 1}/{len(cac_cau)}] {cau['id']} {dong_kq['generate_ms']} ms "
                  f"refused={kq.refused} degraded={kq.degraded} → {kq.answer[:90]!r}")
            if kq.degraded:
                # Phép thử mà suy giảm là cấu hình/nhà cung cấp hỏng — chạy tiếp chỉ đốt hạn mức.
                print("Dừng: LLM không trả lời được (xem log phía trên).")
                break
    finally:
        await tra_loi.aclose()

    return _ghi_bao_cao(model, han_chot_s, ket_qua, so_luot)


def _ghi_bao_cao(model: str, han_chot_s: float, ket_qua: list[dict], so_luot: int) -> Path:
    THU_MUC_BAO_CAO.mkdir(exist_ok=True)
    nhan = datetime.now().strftime("%Y%m%d-%H%M%S")
    duong = THU_MUC_BAO_CAO / f"thu-llm_{model}_{nhan}.md"
    (duong.with_suffix(".jsonl")).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in ket_qua) + "\n", encoding="utf-8"
    )
    co = [r for r in ket_qua if r["co_dap_an"]]
    khong = [r for r in ket_qua if not r["co_dap_an"]]
    sinh = [r for r in ket_qua if r["llm_called"] and r["generate_ms"] is not None]
    ms = sorted(r["generate_ms"] for r in sinh)
    dong = [
        f"# Thử LLM — {model}",
        "",
        f"- **thời điểm:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **bộ vàng:** sha256 `{hashlib.sha256(BO_VANG.read_bytes()).hexdigest()}`",
        f"- **tenant:** `{TENANT}` · hạn chót đo {han_chot_s} s · ngân sách {NGAN_SACH_MS} ms",
        f"- **số lượt gọi LLM:** {so_luot}",
        "",
        "| id | loại | kiểu gõ | trả lời / từ chối | truy hồi trúng | trích đúng căn cứ "
        "| groundedness | generate ms | token vào/ra |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in ket_qua:
        trang_thai = "suy giảm" if r["degraded"] else ("từ chối" if r["refused"] else "trả lời")
        dong.append(
            f"| {r['id']} | {r['loai']} | {r['kieu_go']} | {trang_thai} | "
            f"{'✓' if r['truy_hoi_trung'] else '✗'} | {'✓' if r['trich_dung_can_cu'] else '✗'} | "
            f"{r['groundedness']} | {r['generate_ms']} | "
            f"{r['prompt_tokens']}/{r['completion_tokens']} |"
        )
    dong += [
        "",
        "## Tổng",
        "",
        f"- câu có đáp án được trả lời: {sum(not r['refused'] for r in co)}/{len(co)}; "
        f"trích đúng căn cứ: {sum(r['trich_dung_can_cu'] for r in co)}/{len(co)} "
        f"(truy hồi trúng: {sum(r['truy_hoi_trung'] for r in co)}/{len(co)})",
        f"- câu ngoài kho bị từ chối: {sum(r['refused'] for r in khong)}/{len(khong)}",
        f"- generate trong ngân sách {NGAN_SACH_MS} ms: "
        f"{sum(m <= NGAN_SACH_MS for m in ms)}/{len(ms)}"
        + (f" · trung vị {ms[len(ms) // 2]} ms · lớn nhất {ms[-1]} ms" if ms else ""),
        "",
        "## Câu trả lời",
        "",
    ]
    for r in ket_qua:
        dong += [f"**{r['id']}** — {r['question']}", "", f"> {r['answer']}", ""]
    duong.write_text("\n".join(dong), encoding="utf-8")
    return duong


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default=Settings().llm_model)
    p.add_argument("--gian-s", type=float, default=13.0, help="giãn giữa hai lượt gọi LLM")
    p.add_argument("--han-chot-s", type=float, default=10.0)
    p.add_argument("--chi-in-cau", action="store_true", help="chỉ in 10 câu sẽ chọn, không gọi")
    a = p.parse_args()
    if a.chi_in_cau:
        dong = [json.loads(x) for x in BO_VANG.read_text(encoding="utf-8").splitlines() if x]
        for c in chon_cau(dong):
            print(c["id"], c["loai"], c["kieu_go"], "|", c["question"])
        return
    print(f"Báo cáo: {asyncio.run(chay(a.model, a.gian_s, a.han_chot_s))}")


if __name__ == "__main__":
    main()
