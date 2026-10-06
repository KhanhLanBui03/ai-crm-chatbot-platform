"""Minh chứng Ngày 4 cho báo cáo — UC019 (1/2). [R&D]

Chạy lại được y hệt, in ra các bảng markdown để dán vào ``docs/report/``::

    cd ai-service && source .venv/bin/activate
    python -m tests.eval.ngay4_minh_chung                       # phần 1–3, không cần CSDL
    python -m tests.eval.ngay4_minh_chung --dsn postgresql://ai_app:…@localhost:5432/thesis_crm

Bốn phần:
    1. Tỉ lệ trích xuất thành công theo từng định dạng trên ``data/kb_samples/``
    2. Phân bố số token (ƯỚC LƯỢNG) mỗi đoạn
    3. Một đoạn mẫu có đủ đường dẫn heading
    4. (cần ``--dsn``, CSDL đã có V210) tỉ lệ khớp truy vấn KHÔNG DẤU trước/sau ``unaccent``

Phần 4 ghi vào một tenant ngẫu nhiên trong MỘT transaction rồi ROLLBACK — CSDL không giữ lại
dòng nào. Chạy bằng ``ai_app`` (role chịu RLS), đúng role của runtime. Chạy hai lần phải ra
cùng con số (``.claude/rules/rag-eval.md``) — mọi thứ ảnh hưởng thứ hạng đều tất định.

CÁCH DỰNG TRUY VẤN Ở PHẦN 4 — phải ghi kèm con số trong báo cáo
----------------------------------------------------------------
Chưa có bộ vàng (Ngày 6), nên truy vấn được SINH TỰ ĐỘNG: với mỗi đoạn có heading, lấy heading
lá, bỏ số thứ tự mục ("3.1. "), rồi BỎ DẤU — mô phỏng khách gõ không dấu. Đoạn đó được coi là
"đúng" cho truy vấn của chính nó. Hai cấu hình so trên CÙNG bộ truy vấn:

    trước   to_tsvector('simple', content)          @@ to_tsquery('simple', q)
    sau     content_segmented  (V210, đã bỏ dấu)    @@ to_tsquery('simple', knowledge.f_unaccent(q))

Đây là phép đo khả năng KHỚP của làn từ khoá, không phải recall@5 của cả hệ truy hồi — con số
đó đo trên bộ vàng ở Ngày 13.
"""

import argparse
import csv
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from src.ai.exceptions import AiServiceError
from src.ai.rag.ingest.chia_doan import Doan, chia_doan
from src.ai.rag.ingest.duong_ong import chuan_hoa_khoi
from src.ai.rag.ingest.phan_tich import phan_tich_tep
from src.ai.rag.tsquery import build_tsquery

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"
_SO_MUC = re.compile(r"^\s*(?:[IVXLC]+|\d+(?:\.\d+)*)[.)]\s*")


def _bo_dau(chu: str) -> str:
    """Mô phỏng khách gõ không dấu. CHỈ để sinh truy vấn thử — đường truy hồi thật bỏ dấu
    bằng ``knowledge.f_unaccent`` trong SQL."""
    chu = chu.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", chu) if unicodedata.category(c) != "Mn")


def _phan_vi(xs: list[int], p: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def trich_tat_ca() -> tuple[dict, dict[str, list[Doan]]]:
    """Phân tích mọi tệp nhận 202 trong manifest (gồm cả PDF scan — ca thất bại có chủ đích)."""
    theo_dinh_dang: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    doan_theo_tep: dict[str, list[Doan]] = {}
    for r in csv.DictReader(open(MAU / "manifest.csv", encoding="utf-8")):
        if r["ma_http"] != "202":
            continue
        try:
            khoi = phan_tich_tep(MAU / r["file"], r["dinh_dang"])
            doan_theo_tep[r["file"]] = chia_doan(chuan_hoa_khoi(khoi))
            theo_dinh_dang[r["dinh_dang"]].append((r["file"], None))
        except AiServiceError as e:
            theo_dinh_dang[r["dinh_dang"]].append((r["file"], e.code))
    return theo_dinh_dang, doan_theo_tep


def in_phan_1(theo_dinh_dang: dict) -> None:
    print("## 1. Tỉ lệ trích xuất thành công theo định dạng\n")
    print("| Định dạng | Thành công | Tổng | Tỉ lệ | Thất bại (mã) |")
    print("|---|---:|---:|---:|---|")
    for dd in ("PDF", "DOCX", "TXT", "MD", "HTML"):
        ds = theo_dinh_dang.get(dd, [])
        ok = sum(1 for _, loi in ds if loi is None)
        hong = ", ".join(f"`{t}` → `{loi}`" for t, loi in ds if loi)
        print(f"| {dd} | {ok} | {len(ds)} | {ok / len(ds):.0%} | {hong or '—'} |")
    print(
        "\n`ban-scan-bao-hanh.pdf` là PDF chỉ có ảnh, đưa vào CÓ CHỦ ĐÍCH: thất bại đúng mã "
        "`PARSE_NO_TEXT_EXTRACTED` là kết quả mong đợi.\n"
    )


def in_phan_2(doan_theo_tep: dict[str, list[Doan]]) -> None:
    tat_ca = [d.token_count for ds in doan_theo_tep.values() for d in ds]
    print("## 2. Phân bố số token mỗi đoạn (ước lượng: từ + dấu câu, trần 500)\n")
    print("| Số đoạn | Nhỏ nhất | p10 | Trung vị | p90 | Lớn nhất | Có heading |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    co_heading = sum(1 for ds in doan_theo_tep.values() for d in ds if d.heading)
    print(
        f"| {len(tat_ca)} | {min(tat_ca)} | {_phan_vi(tat_ca, 0.1)} | "
        f"{statistics.median(tat_ca):g} | {_phan_vi(tat_ca, 0.9)} | {max(tat_ca)} | "
        f"{co_heading}/{len(tat_ca)} |"
    )
    print(
        "\nTrung vị thấp hơn trần 500 vì luật \"ranh giới heading là ranh giới đoạn\": các mục "
        "của tài liệu nghiệp vụ ngắn, và gộp hai mục vào một đoạn thì đoạn đó mất heading đúng "
        "để trích dẫn.\n"
    )


def in_phan_3(doan_theo_tep: dict[str, list[Doan]]) -> None:
    d = next(
        d for d in doan_theo_tep["bang-gia-2026.pdf"] if d.heading and "Máy lạnh" in d.heading
    )
    print("## 3. Một đoạn mẫu\n")
    print(f"- **heading:** `{d.heading}`")
    print(f"- **page_number:** {d.page_number} · **chunk_index:** {d.chunk_index} · "
          f"**token_count:** {d.token_count}\n")
    print("```text")
    print(d.content)
    print("```\n")


def in_phan_4(doan_theo_tep: dict[str, list[Doan]], dsn: str) -> None:
    import psycopg

    truy_van: list[tuple[str, int, str]] = []  # (tệp, chunk_index, câu không dấu)
    for tep, ds in doan_theo_tep.items():
        for d in ds:
            if not d.heading:
                continue
            la = _SO_MUC.sub("", d.heading.split(" > ")[-1]).strip()
            if len(la.split()) >= 2:
                truy_van.append((tep, d.chunk_index, _bo_dau(la).lower()))

    tenant = str(uuid4())
    ket_qua = {"truoc": [0, 0], "sau": [0, 0]}  # [khớp, top-5]
    with psycopg.connect(dsn) as conn, conn.transaction(force_rollback=True):
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        doc_id = {}
        for tep, ds in doan_theo_tep.items():
            # id TẤT ĐỊNH theo tên tệp: các đoạn hoà điểm ts_rank được xếp tiếp theo document_id,
            # id ngẫu nhiên làm cột top-5 đổi giữa hai lần chạy (đã gặp: 40,1% rồi 39,6%).
            doc_id[tep] = uuid5(NAMESPACE_URL, f"ngay4-minh-chung/{tep}")
            conn.execute(
                "INSERT INTO knowledge.knowledge_documents"
                " (id, tenant_id, title, source_type, file_path, status)"
                " VALUES (%s, ai.current_tenant(), %s, 'TXT', %s, 'PROCESSING')",
                (doc_id[tep], f"{tep} {tenant}", f"/eval/{tep}"),
            )
            for d in ds:
                conn.execute(
                    "INSERT INTO knowledge.knowledge_chunks (tenant_id, document_id, chunk_index,"
                    " content, heading, page_number, token_count, embedding_model,"
                    " embedding_version) VALUES (ai.current_tenant(), %s, %s, %s, %s, %s, %s,"
                    " 'chua-nhung', 'v0')",
                    (doc_id[tep], d.chunk_index, d.content, d.heading, d.page_number,
                     d.token_count),
                )

        cau_sql = {
            "truoc": "to_tsvector('simple', content) @@ to_tsquery('simple', %(q)s)",
            "sau": "content_segmented @@ to_tsquery('simple', knowledge.f_unaccent(%(q)s))",
        }
        hang_sql = {
            "truoc": "ts_rank(to_tsvector('simple', content), to_tsquery('simple', %(q)s))",
            "sau": "ts_rank(content_segmented,"
            " to_tsquery('simple', knowledge.f_unaccent(%(q)s)))",
        }
        for tep, idx, cau in truy_van:
            q = build_tsquery(cau)
            dung = (doc_id[tep], idx)
            for cau_hinh in ("truoc", "sau"):
                dong = conn.execute(
                    f"SELECT document_id, chunk_index FROM knowledge.knowledge_chunks"
                    f" WHERE {cau_sql[cau_hinh]} ORDER BY {hang_sql[cau_hinh]} DESC,"
                    f" document_id, chunk_index",
                    {"q": q},
                ).fetchall()
                khop = [tuple(r) for r in dong]
                ket_qua[cau_hinh][0] += dung in khop
                ket_qua[cau_hinh][1] += dung in khop[:5]

    n = len(truy_van)
    print("## 4. Truy vấn KHÔNG DẤU trên làn từ khoá — trước/sau `unaccent`\n")
    print(f"{n} truy vấn sinh từ heading lá (bỏ số mục, bỏ dấu), "
          f"{sum(len(ds) for ds in doan_theo_tep.values())} đoạn, 20 tài liệu.\n")
    print("| Cấu hình | Đoạn đúng nằm trong tập khớp | Đoạn đúng trong top-5 `ts_rank` |")
    print("|---|---:|---:|")
    for cau_hinh, ten in (("truoc", "Trước — không bỏ dấu"), ("sau", "Sau — V210 `f_unaccent`")):
        k, t5 = ket_qua[cau_hinh]
        print(f"| {ten} | {k}/{n} = {k / n:.1%} | {t5}/{n} = {t5 / n:.1%} |")
    print("\nVí dụ truy vấn: " + " · ".join(f"`{c}`" for _, _, c in truy_van[:4]) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", help="DSN psycopg của ai_app tới CSDL đã chạy V210 (cho phần 4)")
    args = ap.parse_args()

    theo_dinh_dang, doan_theo_tep = trich_tat_ca()
    print("# Minh chứng Ngày 4 — UC019 (1/2)\n")
    in_phan_1(theo_dinh_dang)
    in_phan_2(doan_theo_tep)
    in_phan_3(doan_theo_tep)
    if args.dsn:
        in_phan_4(doan_theo_tep, args.dsn)
    else:
        print("## 4. (bỏ qua — chạy lại với `--dsn` để đo khớp không dấu)\n")


if __name__ == "__main__":
    main()
