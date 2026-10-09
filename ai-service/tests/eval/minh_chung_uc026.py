"""Minh chứng UC026 với Gemini THẬT: 20 hội thoại mẫu → bốn phần, chạy hai lần. [R&D]

    cd ai-service && source .venv/bin/activate
    LLM_MODE=remote python -m tests.eval.minh_chung_uc026            # ~50 lượt Gemini, ~5 phút

Giãn ``CHO_GIUA_LUOT_S`` giữa hai hội thoại: bậc miễn phí của Flash-Lite giới hạn SỐ LƯỢT MỖI PHÚT
— chạy dồn, lượt thứ 16 trong ~20 giây đã nhận 429 (đo 09/10). Worker thật xử lý từng bản tin một
và thử lại sau 10 s / 60 s nên tự giãn; script đo thì phải giãn tay.

Đi ĐÚNG đường của worker: ``service.summarize`` (trigger ``CLOSING``) → java-core GIẢ trả lịch sử
và nhận PATCH (endpoint ``/internal/*`` của java-core chưa có — kế hoạch Ngày 12, dự phòng) → dòng
``ai_interactions`` nhánh ``SUMMARY`` trên CSDL dev, tenant riêng ``eeeeeeee-…-d026``.

Đo ba thứ cho cổng ra Ngày 12:

1. **4/4 phần trên 20 hội thoại** — đếm trên THÂN PATCH thật gửi sang java-core (thứ sẽ vào
   ``summary_data``), không trên đầu ra thô của mô hình.
2. **Tái lập ở ``temperature = 0``** — lượt 2 chạy lại đúng 20 hội thoại, đếm số bản GIỐNG HỆT
   lượt 1. Nhiệt độ 0 không bảo đảm tất định tuyệt đối với Gemini; báo đúng số đo được.
3. **Nhánh chia khối** (luồng phụ 2.1) — hai hội thoại dài nhất chạy lại với ngân sách 1.000 ký
   tự/khối để đi qua đường tóm tắt từng khối rồi gộp.

Kèm theo: số điện thoại/email gốc lọt vào bản tóm tắt (phải 0 — đã che trước khi gửi), và
``nextSteps`` của H08 (câu thử tiêm chỉ thị) để người đọc tự đánh giá.

Dữ liệu ``tests/eval/hoi_thoai_mau_uc026.jsonl``: 20 hội thoại HƯ CẤU do AI soạn (miền điện máy),
số điện thoại / email là giả. Khai trong báo cáo Ngày 12.
"""

import asyncio
import csv
import json
import re
import statistics
import time
from difflib import SequenceMatcher
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from src.ai import service
from src.ai.config import get_settings
from src.ai.integrations.java_core import MockJavaCoreClient, TinNhanHoiThoai
from src.ai.rag.generate.tom_tat import dong_hoi_thoai

TENANT = "eeeeeeee-0000-0000-0000-00000000d026"
DU_LIEU = Path(__file__).with_name("hoi_thoai_mau_uc026.jsonl")
BAO_CAO = Path(__file__).with_name("reports") / "uc026-minh-chung.csv"
BON_PHAN = ("main_need", "provided_info", "unresolved_issues", "next_steps")
CHO_GIUA_LUOT_S = 4.5  # < 15 lượt/phút
_PII_GOC = re.compile(r"0\d{2,3}[ .]?\d{3}[ .]?\d{3,4}|[\w.]+@[\w.]+")


def _doc() -> list[dict]:
    return [json.loads(d) for d in DU_LIEU.read_text().splitlines() if d.strip()]


async def _mot_luot(bo, hoi_thoai: list[dict], nhan: str) -> list[dict]:
    gia = MockJavaCoreClient()
    ket_qua = []
    for h in hoi_thoai:
        # Mỗi lượt một conversation_id riêng nhưng TẤT ĐỊNH — chạy lại script không sinh rác mới.
        conv = uuid5(NAMESPACE_URL, f"uc026:{nhan}:{h['id']}")
        cac_tin = [TinNhanHoiThoai(t["sender"], t["text"]) for t in h["tin_nhan"]]
        gia.nap_hoi_thoai(TENANT, conv, cac_tin)
        bat_dau = time.monotonic()
        try:
            kq = await service.summarize(TENANT, conv, trigger="CLOSING", java_core=gia,
                                         bo_tom_tat=bo)
            trang_thai, loi = kq.trang_thai, kq.loi
        except Exception as e:  # noqa: BLE001 — minh chứng ghi lại lỗi, không dừng cả lượt
            trang_thai, loi, kq = "LOI", f"{type(e).__name__}: {getattr(e, 'code', e)}", None
        ms = int((time.monotonic() - bat_dau) * 1000)
        ban_ghi = kq.ban_ghi if kq else None
        phan = {p: (getattr(ban_ghi, p) if ban_ghi else "") for p in BON_PHAN}
        ket_qua.append({
            "id": h["id"], "chu_de": h["chu_de"], "trang_thai": trang_thai, "loi": loi,
            "so_phan": sum(bool(v.strip()) for v in phan.values()),
            "model_version": ban_ghi.model_version if ban_ghi else "",
            "so_lan_goi_llm": kq.so_lan_goi_llm if kq else 0, "ms": ms,
            "pii_goc": sum(len(_PII_GOC.findall(v)) for v in phan.values()),
            # Bịa nhãn che: nói "(đã che)" khi đầu vào KHÔNG có nhãn [REDACTED_…] nào.
            "bia_nhan_che": int(
                not any("[REDACTED_" in d for d in dong_hoi_thoai(cac_tin))
                and any("đã che" in v for v in phan.values())
            ),
            **phan,
        })
        print(f"  {nhan} {h['id']} {trang_thai:10} {ket_qua[-1]['so_phan']}/4 {ms:6d} ms",
              loi or "")
        await asyncio.sleep(CHO_GIUA_LUOT_S * max(kq.so_lan_goi_llm if kq else 1, 1))
    return ket_qua


async def chay() -> None:
    s = get_settings()
    if s.llm_mode != "remote":
        raise SystemExit("Cần LLM_MODE=remote — minh chứng này đo mô hình thật.")
    hoi_thoai = _doc()
    bo = service.tao_bo_tom_tat(s)
    try:
        print(f"Lượt 1 — {len(hoi_thoai)} hội thoại, {s.llm_model}")
        lan1 = await _mot_luot(bo, hoi_thoai, "lan1")
        print("Lượt 2 — tái lập")
        lan2 = await _mot_luot(bo, hoi_thoai, "lan2")
    finally:
        await bo.llm.aclose()

    dai = sorted(hoi_thoai, key=lambda h: -sum(len(t["text"]) for t in h["tin_nhan"]))[:2]
    bo_khoi = service.tao_bo_tom_tat(s.model_copy(update={"tom_tat_ky_tu_moi_khoi": 1000}))
    try:
        print("Chia khối — 1.000 ký tự/khối")
        khoi = await _mot_luot(bo_khoi, dai, "khoi")
    finally:
        await bo_khoi.llm.aclose()

    BAO_CAO.parent.mkdir(exist_ok=True)
    with BAO_CAO.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["luot", *lan1[0].keys()])
        w.writeheader()
        for nhan, ds in (("lan1", lan1), ("lan2", lan2), ("khoi", khoi)):
            for d in ds:
                w.writerow({"luot": nhan, **d})

    du = sum(d["so_phan"] == 4 for d in lan1)
    giong = sum(
        all(a[p] == b[p] for p in BON_PHAN) for a, b in zip(lan1, lan2, strict=True)
        if a["trang_thai"] == b["trang_thai"] == "DA_GHI"
    )
    ms = [d["ms"] for d in lan1 if d["trang_thai"] == "DA_GHI"]
    print("\n── Kết quả ──")
    print(f"4/4 phần (lượt 1): {du}/{len(lan1)}  · lượt 2: "
          f"{sum(d['so_phan'] == 4 for d in lan2)}/{len(lan2)}")
    print(f"Giống hệt lượt 1 ↔ lượt 2: {giong}/{len(lan1)}")
    if ms:
        print(f"Độ trễ lượt 1: trung vị {statistics.median(ms):.0f} ms, tối đa {max(ms)} ms")
    print(f"Vòng sửa: {sum(d['so_lan_goi_llm'] > 1 for d in lan1)} hội thoại")
    print(f"PII gốc lọt vào bản tóm tắt: {sum(d['pii_goc'] for d in lan1 + lan2)}")
    print(f"Bịa nhãn che (nói 'đã che' khi đầu vào không có): "
          f"{sum(d['bia_nhan_che'] for d in lan1 + lan2)}/{len(lan1) + len(lan2)}")
    tuong_dong = [
        statistics.mean(SequenceMatcher(None, a[p], b[p]).ratio() for p in BON_PHAN)
        for a, b in zip(lan1, lan2, strict=True)
        if a["trang_thai"] == b["trang_thai"] == "DA_GHI"
    ]
    if tuong_dong:
        print(f"Tương đồng ký tự lượt 1 ↔ 2 (difflib): TB {statistics.mean(tuong_dong):.3f}, "
              f"thấp nhất {min(tuong_dong):.3f}; phần giống hệt "
              f"{sum(a[p] == b[p] for a, b in zip(lan1, lan2, strict=True) for p in BON_PHAN)}"
              f"/{4 * len(lan1)}")
    print(f"Chia khối: {[(d['id'], d['so_lan_goi_llm'], d['so_phan']) for d in khoi]}")
    print(f"Phiên bản: {sorted({d['model_version'] for d in lan1 if d['model_version']})}")
    h08 = next(d for d in lan1 if d["id"] == "H08")
    print(f"H08 nextSteps: {h08['next_steps']}")
    print(f"CSV: {BAO_CAO}")


if __name__ == "__main__":
    asyncio.run(chay())
