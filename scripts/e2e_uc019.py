"""UC019 đầu-cuối trên hạ tầng của scripts/e2e-uc018.sh — minh chứng cổng ra Ngày 5.

Gọi từ ``scripts/e2e-uc018.sh nap`` (SAU ``up`` và ``run``): lúc đó java-core đã nhận ~65 tệp và phát
~65 sự kiện ``DocumentUploaded`` thật lên Kafka, còn ai-worker vừa được bật.

  1. Chờ worker nạp xong mọi tài liệu ``run`` đã tải — sự kiện THẬT do java-core phát qua outbox.
  2. Tài liệu PDF 100 trang và tài liệu MD ≥ 3.000 đoạn: sinh tệp, tải qua java-core như người dùng,
     lấy mẫu 6 bước tiến độ từ ai-service mỗi 50 ms, đo thời gian nạp, số đoạn/giây, RSS đỉnh của
     worker. Bài 3.000 đoạn dùng MD: PDF cỡ đó cần ~730 trang, phân tích vượt trần 120 s (find_tables
     ~0,3 s/trang) — mà thứ cần đo ở bài này là bộ nhớ vector, không phụ thuộc định dạng.
  3. Bảng trạng thái cuối theo định dạng + model nhúng trên từng đoạn.
  4. Bản tin hỏng lược đồ phát vào topic nguồn → phải xuất hiện trong ``ai.dlq``.

``AI_MODE=mock``: vector giả seed cố định — số đoạn/giây ở đây là của đường ống (tải S3, phân tích,
chia đoạn, ghi CSDL), KHÔNG gồm thời gian nhúng thật. Đo lại với ai-embed thật ở Ngày 7.

In markdown để dán vào báo cáo. Thoát khác 0 nếu có ca sai.
"""

import asyncio
import io
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psycopg
import pymupdf
from aiokafka import AIOKafkaProducer
from markdown_it import MarkdownIt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "data" / "kb_samples"))
sys.path.insert(0, str(REPO / "ai-service"))

from _tao_tep_mau import CSS_PDF, DOCX, NGUON, PDF, TRANG_A4, VUNG_VIET
from e2e_uc018 import TENANT_A, tai_len, token
from src.ai.rag.ingest.duong_ong import chia_doan_tu_khoi
from src.ai.rag.ingest.phan_tich import phan_tich_tep

AI_URL = os.environ["E2E_AI_URL"]
DSN = os.environ["E2E_DB_DSN"]
KAFKA = os.environ["E2E_KAFKA"]
WORKER_PID = int(os.environ["E2E_WORKER_PID"])
TOPIC = "crm.kb.document.uploaded"

loi = 0


def kiem(ten: str, dat: bool, chi_tiet: str = "") -> None:
    global loi
    loi += 0 if dat else 1
    print(f"| {'✅' if dat else '❌'} | {ten} | {chi_tiet} |")


def sql(cau: str, *tham_so) -> list[tuple]:
    with psycopg.connect(DSN) as conn:
        return conn.execute(cau, tham_so).fetchall()


def rss_kb(pid: int) -> int:
    """RSS (KB) của một tiến trình; 0 nếu nó không còn."""
    kq = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, check=False)
    return int(kq.stdout.strip() or 0)


def rss_con_kb(pid: int) -> int:
    """RSS lớn nhất trong các tiến trình con (bộ phân tích tệp chạy ở tiến trình con spawn)."""
    kq = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False)
    return max((rss_kb(int(c)) for c in kq.stdout.split()), default=0)


# ── Sinh PDF N trang ─────────────────────────────────────────────────────────


def tao_pdf_nhieu_trang(so_trang: int) -> bytes:
    """Nối nguồn Markdown của 9 tài liệu mẫu, lặp lại dưới heading "Phần k", dừng ĐÚNG ở trang N.

    Dựng bằng cùng ``pymupdf.Story`` + CSS với bộ tệp mẫu, nên PDF ra có heading thật, bảng thật —
    đường ống đi đúng nhánh như với tệp khách hàng, không phải một khối chữ trơn.
    """
    md = MarkdownIt("commonmark").enable("table")
    nguon = [(NGUON / f"{t}.md").read_text(encoding="utf-8") for t in PDF + DOCX]
    phan = []
    for k in range(1, 400):
        phan.append(f"<h1>Phần {k}</h1>" + "".join(md.render(n) for n in nguon))
        if len(phan) * 9 * 1.5 > so_trang * 1.2:  # dư chữ; phần thừa bị cắt ở trang N
            break
    story = pymupdf.Story(html="".join(phan), user_css=CSS_PDF)
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    for _ in range(so_trang):
        thiet_bi = writer.begin_page(TRANG_A4)
        con, _ = story.place(VUNG_VIET)
        story.draw(thiet_bi)
        writer.end_page()
        if not con:
            break
    writer.close()
    # Nén như bộ tệp mẫu (_luu_pdf_tat_dinh): bản thô của DocumentWriter ~45 KB/trang.
    return pymupdf.open("pdf", buf.getvalue()).tobytes(garbage=4, deflate=True)


def tao_md_it_nhat(so_doan: int, tam: Path) -> tuple[bytes, int]:
    """Nối nguồn Markdown dưới heading "Phần k" tới khi chia ra được ≥ ``so_doan`` đoạn.

    Đếm bằng CHÍNH hàm của đường ống (phan_tich_tep + chia_doan_tu_khoi), không ước lượng.
    """
    nguon = "\n\n".join((NGUON / f"{t}.md").read_text(encoding="utf-8") for t in PDF + DOCX)
    phan: list[str] = []
    while True:
        phan.append(f"# Phần {len(phan) + 1}\n\n{nguon}")
        if len(phan) % 10:
            continue
        du_lieu = "\n\n".join(phan).encode("utf-8")
        tam.write_bytes(du_lieu)
        dem = len(chia_doan_tu_khoi(phan_tich_tep(tam, "MD"), "MD", 500))
        if dem >= so_doan:
            return du_lieu, dem


# ── Phần 1: chờ tài liệu của `run` ───────────────────────────────────────────


def cho_het_hang_doi(han_s: float = 300) -> None:
    het = time.monotonic() + han_s
    while time.monotonic() < het:
        (con,) = sql("SELECT count(*) FROM knowledge.knowledge_documents"
                     " WHERE status IN ('PENDING', 'PROCESSING')")[0]
        if con == 0:
            return
        time.sleep(1)
    raise SystemExit(f"Quá {han_s}s mà còn tài liệu chưa nạp xong — xem ai-worker.log")


# ── Phần 2: đo một tài liệu lớn ──────────────────────────────────────────────


def do_mot_tai_lieu(ten: str, du_lieu: bytes, duoi: str, trang: int | None) -> dict | None:
    ma, body = tai_len(token(TENANT_A), TENANT_A, f"{ten}.{duoi}", du_lieu, f"Ngày 5 — {ten}")
    if ma != 202:
        kiem(f"java-core nhận {ten}", False, f"{ma} {body.get('code')}")
        return None
    doc = body["data"]["id"]

    rss_truoc = rss_kb(WORKER_PID)
    rss_dinh, rss_con_dinh = rss_truoc, 0
    lan_dau: dict[str, float] = {}
    mau: list[dict] = []
    t0 = time.monotonic()
    with httpx.Client(base_url=AI_URL, headers={"X-Tenant-Id": TENANT_A}, timeout=5) as c:
        while time.monotonic() - t0 < 600:
            td = c.get(f"/v1/ai/kb/ingestion-jobs/{doc}").json()
            t = time.monotonic() - t0
            lan_dau.setdefault(td["state"], t)
            mau.append({"t": t, "state": td["state"], "chunks": td["chunks_created"],
                        "total": td["chunks_total"]})
            rss_dinh = max(rss_dinh, rss_kb(WORKER_PID))
            rss_con_dinh = max(rss_con_dinh, rss_con_kb(WORKER_PID))
            if td["state"] in ("DONE", "FAILED"):
                break
            time.sleep(0.05)

    (so_doan, giay_nap, giay_cho, trang_thai) = sql(
        "SELECT chunk_count, extract(epoch FROM indexed_at - ingest_started_at),"
        " extract(epoch FROM ingest_started_at - created_at), status"
        " FROM knowledge.knowledge_documents WHERE id = %s", doc)[0]
    return {"ten": ten, "doc": doc, "trang": trang, "byte": len(du_lieu),
            "trang_thai": trang_thai, "so_doan": so_doan, "giay_nap": float(giay_nap or 0),
            "giay_cho": float(giay_cho or 0), "lan_dau": lan_dau, "mau": mau,
            "rss_truoc": rss_truoc, "rss_dinh": rss_dinh, "rss_con_dinh": rss_con_dinh}


def in_do(kq: dict) -> None:
    trang = f"{kq['trang']} trang, " if kq["trang"] else ""
    print(f"\n**{kq['ten']}** — {trang}{kq['byte'] / 1024:.0f} KB, "
          f"{kq['so_doan']} đoạn, `{kq['trang_thai']}`\n")
    print("| Chỉ số | Giá trị |\n|---|---|")
    print(f"| Chờ hàng đợi (`created_at` → `ingest_started_at`) | {kq['giay_cho']:.2f} s |")
    print(f"| Thời gian nạp (`ingest_started_at` → `indexed_at`) | {kq['giay_nap']:.2f} s |")
    if kq["giay_nap"]:
        print(f"| Thông lượng | {kq['so_doan'] / kq['giay_nap']:.0f} đoạn/giây |")
    print(f"| RSS worker trước → đỉnh | {kq['rss_truoc'] / 1024:.0f} → "
          f"{kq['rss_dinh'] / 1024:.0f} MB |")
    print(f"| RSS đỉnh tiến trình con phân tích | {kq['rss_con_dinh'] / 1024:.0f} MB |")
    print("\nSáu bước — lần đầu thấy qua `GET /v1/ai/kb/ingestion-jobs/{id}` (lấy mẫu 50 ms):\n")
    print("| Bước | Thấy lần đầu ở giây |\n|---|---|")
    for b in ("QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE"):
        t = kq["lan_dau"].get(b)
        print(f"| {b} | {f'{t:.2f}' if t is not None else '— (ngắn hơn chu kỳ lấy mẫu)'} |")


def luu_mau_csv(kq: dict) -> Path:
    """Chuỗi mẫu tiến độ → CSV cho biểu đồ 6 bước của báo cáo."""
    dich = Path(os.environ.get("E2E_STATE", "/tmp")) / f"tien-do-{kq['ten']}.csv"
    dich.write_text(
        "giay,buoc,doan_da_ghi,tong_doan\n"
        + "".join(f"{m['t']:.3f},{m['state']},{m['chunks']},{m['total'] or ''}\n"
                  for m in kq["mau"]),
        encoding="utf-8",
    )
    return dich


# ── Phần 4: DLQ ──────────────────────────────────────────────────────────────


async def phat_ban_tin_hong() -> None:
    p = AIOKafkaProducer(bootstrap_servers=KAFKA)
    await p.start()
    try:
        await p.send_and_wait(TOPIC, b'{"event_id": "khong-phai-so", "tenant_id": "x"}',
                              key=TENANT_A.encode(), headers=[("X-Trace-Id", b"ngay5-dlq")])
    finally:
        await p.stop()


def main() -> int:
    print("## UC019 đầu-cuối — Ngày 5\n")

    print("### 1. Tài liệu do `run` tải lên (sự kiện thật từ java-core)\n")
    t0 = time.monotonic()
    cho_het_hang_doi()
    print(f"Hàng đợi rỗng sau {time.monotonic() - t0:.1f} s kể từ lúc bật worker.\n")

    # Phát bản tin hỏng TRƯỚC phần đo: phần sau có hỏng thì bash vẫn đọc được DLQ.
    asyncio.run(phat_ban_tin_hong())

    print("### 2. Tài liệu lớn\n")
    pdf = tao_pdf_nhieu_trang(100)
    kq_100 = do_mot_tai_lieu("tai-lieu-100-trang", pdf, "pdf", pymupdf.open("pdf", pdf).page_count)
    tam = Path(os.environ.get("E2E_STATE", "/tmp")) / "tai-lieu-3000-doan.md"
    md, du_kien = tao_md_it_nhat(3000, tam)
    kq_3000 = do_mot_tai_lieu("tai-lieu-3000-doan", md, "md", None)
    for kq in (kq_100, kq_3000):
        if kq:
            in_do(kq)
            print(f"\nCSV tiến độ: `{luu_mau_csv(kq)}`")
    print(f"\n(Đường ống chia tệp MD ra {du_kien} đoạn khi đếm trước ở máy chủ.)")

    print("\n### 3. Trạng thái cuối\n")
    print("| source_type | status | số tài liệu | tổng đoạn | mã lỗi |\n|---|---|---|---|---|")
    for dong in sql(
        "SELECT source_type, status, count(*), sum(chunk_count),"
        " string_agg(DISTINCT split_part(error_message, ':', 1), ', ')"
        " FROM knowledge.knowledge_documents GROUP BY 1, 2 ORDER BY 1, 2"
    ):
        print("| " + " | ".join("" if v is None else str(v) for v in dong) + " |")
    print()
    print("| Kiểm | Việc | Chi tiết |\n|---|---|---|")
    (khop,) = sql(
        "SELECT count(*) FROM knowledge.knowledge_documents d WHERE d.status = 'READY'"
        " AND d.chunk_count <> (SELECT count(embedding) FROM knowledge.knowledge_chunks c"
        " WHERE c.document_id = d.id)")[0]
    kiem("Mọi tài liệu READY: chunk_count = số đoạn có vector", khop == 0, f"{khop} lệch")
    (con,) = sql("SELECT count(*) FROM knowledge.knowledge_documents"
                 " WHERE status IN ('PENDING', 'PROCESSING')")[0]
    kiem("Không còn tài liệu PENDING/PROCESSING", con == 0, f"{con} còn lại")
    (mo_coi,) = sql("SELECT count(*) FROM knowledge.knowledge_chunks c JOIN"
                    " knowledge.knowledge_documents d ON d.id = c.document_id"
                    " WHERE d.status <> 'READY'")[0]
    kiem("Không có đoạn nào thuộc tài liệu không READY", mo_coi == 0, f"{mo_coi} đoạn")
    (scan,) = sql("SELECT count(*) FROM knowledge.knowledge_documents WHERE status = 'FAILED'"
                  " AND error_message LIKE 'PARSE_NO_TEXT_EXTRACTED%%'")[0]
    kiem("PDF scan → FAILED PARSE_NO_TEXT_EXTRACTED (không vào DLQ)", scan >= 1, f"{scan} tài liệu")
    if kq_100:
        kiem("Tài liệu 100 trang READY",
             kq_100["trang_thai"] == "READY" and kq_100["trang"] == 100,
             f"{kq_100['trang']} trang, {kq_100['so_doan']} đoạn")
    if kq_3000:
        kiem("Tài liệu ≥ 3.000 đoạn READY",
             kq_3000["trang_thai"] == "READY" and kq_3000["so_doan"] >= 3000,
             f"{kq_3000['so_doan']} đoạn")
    if kq_100 and kq_3000:
        # So ĐỈNH với ĐỈNH của hai tài liệu nạp liền nhau trên cùng worker đã ấm — không so với mốc
        # "trước": RSS của macOS không tính trang bị nén khi tiến trình nhàn rỗi, mốc đó thấp giả.
        # Gom hết vector thì mỗi đoạn thêm ~32 KB (1024 float Python); nạp theo lô thì chênh lệch
        # chỉ còn phần văn bản của các đoạn thêm vào.
        them = kq_3000["so_doan"] - kq_100["so_doan"]
        chenh = (kq_3000["rss_dinh"] - kq_100["rss_dinh"]) / 1024
        gom = them * 32 / 1024
        kiem("RSS đỉnh không tăng theo số vector (chênh < ½ phần gom hết vector)",
             chenh < gom / 2,
             f"đỉnh {kq_100['rss_dinh'] / 1024:.0f} → {kq_3000['rss_dinh'] / 1024:.0f} MB: "
             f"+{chenh:.0f} MB cho +{them} đoạn; gom hết vector sẽ thêm ≈ {gom:.0f} MB")
    print("\nModel nhúng trên từng đoạn:\n")
    for model, so in sql("SELECT embedding_model, count(*) FROM knowledge.knowledge_chunks"
                         " GROUP BY 1 ORDER BY 2 DESC"):
        print(f"- `{model}`: {so} đoạn")
    (xu_ly,) = sql("SELECT count(*) FROM ai.processed_events")[0]
    print(f"\n`ai.processed_events`: {xu_ly} sự kiện đã ghi nhận (bảng có RLS — đếm bằng crm_owner).")

    print("\n### 4. Bản tin hỏng lược đồ → DLQ\n")
    print("Đã phát `{\"event_id\": \"khong-phai-so\", …}` với `X-Trace-Id: ngay5-dlq` — "
          "xem bản tin trong `ai.dlq` ở phần bash ngay sau.")
    return loi


if __name__ == "__main__":
    sys.exit(main())
