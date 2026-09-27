"""UC018 đầu-cuối: java-core thật → kho S3 thật → ai-service thật → Kafka. Gọi từ scripts/e2e-uc018.sh.

Đóng vai người dùng gọi ``POST /api/v1/documents`` như dashboard sẽ gọi, rồi SOI lại dữ liệu ở mọi
chỗ nó được lưu:

  1.  Tenant A (gói STARTER): 25 tệp của data/kb_samples/manifest.csv — so mã HTTP với cột ma_http.
  1b. Tenant A: tệp tên tiếng Việt (dấu cách, gạch dài, tên dạng NFD như khi chép từ macOS), có mô
      tả, có tệp tiếng Anh — những thứ bộ 25 tệp mẫu (tên ASCII, không mô tả) không phủ.
  2.  Tenant B (gói TRIAL, 20 tài liệu): 21 lượt tải — mốc 80% ở lượt 16, 100% ở lượt 20, 409 ở 21.
  3.  Soi dữ liệu: từng trường của knowledge_documents, từng byte trên kho S3, hạn mức, outbox,
      Kafka — và dữ liệu đã đủ cho UC019 (Ngày 4) đọc chưa.

Phần 3 nối CSDL bằng crm_owner (bỏ qua RLS) — đây là góc nhìn KIỂM TRA, không phải đường đi của
ứng dụng. In bảng markdown để dán vào báo cáo. Thoát khác 0 nếu có ca sai.
"""

import asyncio
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
import psycopg
from aiokafka import AIOKafkaConsumer
from minio import Minio

REPO = Path(__file__).resolve().parents[1]
MAU = REPO / "data" / "kb_samples"
URL = os.environ["E2E_JAVA_CORE_URL"] + "/api/v1/documents"
TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"
NGUOI_TAI = "00000000-0000-0000-0000-00000000a001"  # sub mặc định của scripts/dev-jwt.sh
BUCKET = os.environ.get("E2E_BUCKET", "kb-tai-lieu")
GIOI_HAN = 20 * 1024 * 1024

# Gương của mime.py — kỳ vọng độc lập với code đang bị kiểm.
DINH_DANG = {".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT", ".md": "MD", ".markdown": "MD",
             ".html": "HTML", ".htm": "HTML"}
MIME = {"PDF": "application/pdf", "TXT": "text/plain", "MD": "text/markdown", "HTML": "text/html",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@dataclass
class DaNhan:
    """Một lượt được java-core trả 202 — cùng những gì người dùng đã gửi."""

    id: str
    tenant: str
    ten_tep: str
    kich_thuoc: int
    sha256: str
    title: str
    description: str | None
    language: str
    version: int
    ten_key_mong_doi: str | None = None


da_nhan: list[DaNhan] = []


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def token(tenant: str) -> str:
    """JWT RS256 từ scripts/dev-jwt.sh — cùng cặp khoá java-core đang tin (DEV_JWT_DIR)."""
    kq = subprocess.run([str(REPO / "scripts" / "dev-jwt.sh"), tenant],
                        capture_output=True, text=True, check=True, env=os.environ.copy())
    return kq.stdout.strip()


def tai_len(tok: str, tenant: str, ten: str, du_lieu: bytes, title: str, language: str = "vi",
            description: str | None = None, ten_key: str | None = None) -> tuple[int, dict]:
    form = {"title": title, "language": language}
    if description is not None:
        form["description"] = description
    r = httpx.post(URL, headers={"Authorization": f"Bearer {tok}", "X-Trace-Id": "e2e-uc018"},
                   files={"file": (ten, du_lieu, "application/octet-stream")}, data=form, timeout=60)
    body = r.json()
    if r.status_code == 202:
        d = body["data"]
        mo_ta = nfc(description) if description else None
        da_nhan.append(DaNhan(d["id"], tenant, nfc(ten), len(du_lieu), hashlib.sha256(du_lieu).hexdigest(),
                              nfc(title), mo_ta or None,
                              language, d["version"], ten_key))
    return r.status_code, body


# ── Phần 1, 1b, 2: đóng vai người dùng ────────────────────────────────────────


def phan_1_manifest() -> int:
    tok = token(TENANT_A)
    dong = list(csv.DictReader(open(MAU / "manifest.csv", encoding="utf-8")))
    print("### 1. 25 tệp mẫu qua java-core (tenant A, gói STARTER)\n")
    print("| # | Tệp | Mong đợi | Thực tế | `code` | version | |")
    print("|---|---|---|---|---|---|---|")
    sai = 0
    for i, r in enumerate(dong, 1):
        if r["file"] == "tep-qua-lon.pdf":  # không commit tệp 20 MiB — sinh tại chỗ, vượt 1 byte
            du_lieu = b"%PDF-1.7\n" + b"0" * GIOI_HAN
        else:
            du_lieu = (MAU / r["file"]).read_bytes()
        ma, body = tai_len(tok, TENANT_A, r["file"], du_lieu, r["title"], r["language"])
        code = body.get("code") or ""
        dung = str(ma) == r["ma_http"] and (not r["ma_loi"] or code == r["ma_loi"])
        ver = body.get("data", {}).get("version", "") if ma == 202 else ""
        sai += not dung
        print(f"| {i} | `{r['file']}` | {r['ma_http']} {r['ma_loi']} | {ma} | {code} | {ver} | "
              f"{'✅' if dung else '❌'} |")
    print(f"\n**{len(dong) - sai}/{len(dong)}** tệp đúng mã HTTP.\n")
    return sai


def phan_1b_nguoi_dung_that() -> int:
    """Tên tệp như người dùng thật đặt. Cột cuối là tên phân đoạn cuối của key mong đợi."""
    tok = token(TENANT_A)
    ca = [
        ("Bảng giá sản phẩm 2026.pdf", "bang-gia-2026.pdf", "Bảng giá sản phẩm 2026 (bản gửi đại lý)",
         "vi", "Giá niêm yết áp dụng từ 01/10/2026 cho đại lý cấp 1", "Bảng-giá-sản-phẩm-2026.pdf"),
        ("Warranty Policy – EN.html", "warranty-policy-en.html", "Warranty Policy (EN)",
         "en", "Bản rút gọn cho khách nước ngoài", "Warranty-Policy-EN.html"),
        # Tên và tiêu đề dạng NFD (dán từ macOS); mô tả toàn khoảng trắng phải thành NULL.
        (unicodedata.normalize("NFD", "Hỏi đáp thanh toán.txt"), "faq-thanh-toan.txt",
         unicodedata.normalize("NFD", "Hỏi đáp về thanh toán"), "vi", "   ", "Hỏi-đáp-thanh-toán.txt"),
    ]
    print("### 1b. Tên tệp tiếng Việt, mô tả, tiếng Anh (tenant A)\n")
    print("| Tên tệp người dùng đặt | Ngôn ngữ | HTTP | |")
    print("|---|---|---|---|")
    sai = 0
    for ten, nguon, title, lang, mo_ta, ten_key in ca:
        ma, _ = tai_len(tok, TENANT_A, ten, (MAU / nguon).read_bytes(), title, lang, mo_ta, ten_key)
        sai += ma != 202
        print(f"| `{nfc(ten)}` | {lang} | {ma} | {'✅' if ma == 202 else '❌'} |")
    print()
    return sai


def phan_2_han_muc() -> int:
    tok = token(TENANT_B)
    print("### 2. Hạn mức (tenant B, gói TRIAL = 20 tài liệu)\n")
    print("| Lượt | HTTP | `code` | used / quota | % | `warnedAt` | `blockedAt` |")
    print("|---|---|---|---|---|---|---|")
    ket_qua = {}
    for i in range(1, 22):
        ma, body = tai_len(tok, TENANT_B, f"tai-lieu-{i:02d}.txt", f"Nội dung {i}".encode(),
                           f"Tài liệu {i:02d}")
        q = (body.get("data") or {}).get("documentQuota") if ma == 202 else body.get("data") or {}
        ket_qua[i] = (ma, body.get("code"), q)
        if i in (1, 15, 16, 19, 20, 21):
            print(f"| {i} | {ma} | {body.get('code') or ''} | {q.get('used')} / {q.get('quota')} | "
                  f"{q.get('percent')} | {'có' if q.get('warnedAt') else '—'} | "
                  f"{'có' if q.get('blockedAt') else '—'} |")
    mong = [
        ket_qua[15][0] == 202 and not ket_qua[15][2].get("warnedAt"),
        ket_qua[16][0] == 202 and ket_qua[16][2].get("warnedAt") and not ket_qua[16][2].get("blockedAt"),
        ket_qua[20][0] == 202 and ket_qua[20][2].get("blockedAt"),
        ket_qua[21][0] == 409 and ket_qua[21][1] == "DOCUMENT_QUOTA_EXCEEDED",
    ]
    print(f"\nMốc 80% ở lượt 16, 100% ở lượt 20, 409 ở lượt 21: **{'đúng' if all(mong) else 'SAI'}**.\n")
    return 0 if all(mong) else 1


# ── Phần 3: soi dữ liệu đã lưu ────────────────────────────────────────────────


class BangKiem:
    def __init__(self) -> None:
        self.dong: list[tuple[str, bool, str]] = []

    def kiem(self, ten: str, dat: bool, chi_tiet: str = "") -> None:
        self.dong.append((ten, dat, chi_tiet))

    def in_ra(self) -> int:
        print("| # | Kiểm | | Chi tiết |")
        print("|---|---|---|---|")
        for i, (ten, dat, ct) in enumerate(self.dong, 1):
            print(f"| {i} | {ten} | {'✅' if dat else '❌'} | {ct} |")
        sai = sum(not d for _, d, _ in self.dong)
        print(f"\n**{len(self.dong) - sai}/{len(self.dong)}** mục kiểm đạt.\n")
        return sai


def _lech(cap: list[tuple[str, object, object]]) -> tuple[bool, str]:
    """(đạt?, chi tiết) cho một trường so trên mọi tài liệu. cap = [(tên tệp, mong đợi, thực tế)]."""
    sai = [(t, m, th) for t, m, th in cap if m != th]
    if not sai:
        return True, f"{len(cap)}/{len(cap)} tài liệu khớp"
    t, m, th = sai[0]
    return False, f"{len(sai)} lệch — `{t}`: mong `{m}`, thấy `{th}`"


def _doc_kafka(bootstrap: str, can: int) -> list:
    async def doc():
        # Không group: chỉ đọc để kiểm, không lưu offset — và khỏi chờ Kafka dựng topic
        # __consumer_offsets trên broker mới (log GroupCoordinatorNotAvailable lặp lại).
        c = AIOKafkaConsumer("crm.document.v1", bootstrap_servers=bootstrap, group_id=None,
                             auto_offset_reset="earliest", enable_auto_commit=False)
        await c.start()
        ds, han = [], time.monotonic() + 20
        try:
            while len(ds) < can and time.monotonic() < han:
                for ban_tin in (await c.getmany(timeout_ms=500)).values():
                    ds.extend(ban_tin)
        finally:
            await c.stop()
        return ds
    return asyncio.run(doc())


def phan_3_soi_du_lieu() -> int:
    bk = BangKiem()
    theo_id = {d.id: d for d in da_nhan}
    tenant_co = {TENANT_A, TENANT_B}

    with psycopg.connect(os.environ["E2E_DB_DSN"], autocommit=True) as db:
        # Chờ job phát outbox (500 ms/lượt) xả hết trước khi soi.
        han = time.monotonic() + 30
        while db.execute("SELECT count(*) FROM platform.outbox_events WHERE published_at IS NULL").fetchone()[0] \
                and time.monotonic() < han:
            time.sleep(0.5)

        dong = {r[0]: r for r in db.execute("""
            SELECT id::text, tenant_id::text, title, description, language, source_type, mime_type,
                   file_name, file_path, file_size_bytes, status, error_message, version,
                   uploaded_by::text, chunk_count
              FROM knowledge.knowledge_documents""").fetchall()}
        so_doan = db.execute("SELECT count(*) FROM knowledge.knowledge_chunks").fetchone()[0]
        han_muc = {(r[0], r[1]): r[2] for r in db.execute("""
            SELECT u.tenant_id::text, u.metric, u.used_value
              FROM platform.usage_records u
              JOIN platform.tenant_subscriptions s ON s.id = u.subscription_id
             WHERE s.period_end > now()""").fetchall()}
        outbox = db.execute("""
            SELECT aggregate_id::text, tenant_id::text, payload, published_at, event_type, topic
              FROM platform.outbox_events""").fetchall()

    print("### 3. Soi dữ liệu đã lưu\n")

    # 3.1 — Bản ghi tài liệu: có đủ, không thừa, từng trường đúng.
    thieu = [d.ten_tep for d in da_nhan if d.id not in dong]
    bk.kiem("Mọi lượt 202 đều có bản ghi `knowledge_documents`", not thieu,
            f"{len(da_nhan) - len(thieu)}/{len(da_nhan)}" + (f" — thiếu `{thieu[0]}`" if thieu else ""))
    thua = [r for i, r in dong.items() if i not in theo_id]
    bk.kiem("Lượt bị từ chối (413, 415, 409) không để lại bản ghi", not thua, f"{len(thua)} bản ghi thừa")

    co = [(d, dong[d.id]) for d in da_nhan if d.id in dong]
    for ten, lay_mong, lay_that in [
        ("`tenant_id` = tenant trong JWT", lambda d: d.tenant, lambda r: r[1]),
        ("`title` đã chuẩn hoá NFC + strip", lambda d: d.title, lambda r: r[2]),
        ("`description` (toàn khoảng trắng ⇒ NULL)", lambda d: d.description, lambda r: r[3]),
        ("`language`", lambda d: d.language, lambda r: r[4]),
        ("`source_type` theo định dạng thật", lambda d: DINH_DANG[Path(d.ten_tep).suffix.lower()], lambda r: r[5]),
        ("`mime_type`", lambda d: MIME[DINH_DANG[Path(d.ten_tep).suffix.lower()]], lambda r: r[6]),
        ("`file_name` = tên người dùng đặt (NFC)", lambda d: d.ten_tep, lambda r: r[7]),
        ("`file_size_bytes` = dung lượng thật", lambda d: d.kich_thuoc, lambda r: r[9]),
        ("`version` khớp phản hồi 202", lambda d: d.version, lambda r: r[12]),
        ("`uploaded_by` = `sub` của JWT", lambda d: NGUOI_TAI, lambda r: r[13]),
    ]:
        bk.kiem(ten, *_lech([(d.ten_tep, lay_mong(d), lay_that(r)) for d, r in co]))

    # 3.2 — Kho S3: key đúng vùng tenant, trùng từng byte, không object mồ côi.
    kho = Minio(os.environ["E2E_S3_ENDPOINT"], access_key=os.environ["E2E_S3_ACCESS"],
                secret_key=os.environ["E2E_S3_SECRET"], secure=False)
    khuon = re.compile(rf"^s3://{BUCKET}/([0-9a-f-]{{36}})/[0-9a-f-]{{36}}/([^/\\]+)$")
    sai_dang, sai_byte, sai_ten = [], [], []
    for d, r in co:
        m = khuon.match(r[8] or "")
        if not m or m.group(1) != d.tenant:
            sai_dang.append(r[8])
            continue
        if d.ten_key_mong_doi and m.group(2) != d.ten_key_mong_doi:
            sai_ten.append(f"{m.group(2)} ≠ {d.ten_key_mong_doi}")
        key = r[8][len(f"s3://{BUCKET}/"):]
        obj = kho.get_object(BUCKET, key)
        try:
            if hashlib.sha256(obj.read()).hexdigest() != d.sha256:
                sai_byte.append(d.ten_tep)
        finally:
            obj.close()
            obj.release_conn()
    bk.kiem("`file_path` = `s3://kb-tai-lieu/{tenant_id}/{uuid}/{tên}`, tenant đúng", not sai_dang,
            f"{len(co) - len(sai_dang)}/{len(co)}" + (f" — `{sai_dang[0]}`" if sai_dang else ""))
    bk.kiem("Tên tiếng Việt được làm sạch đúng trong key", not sai_ten,
            "; ".join(sai_ten) or "3/3 (dấu cách, gạch dài, NFD)")
    bk.kiem("Object trên S3 trùng TỪNG BYTE với tệp gốc (SHA-256)", not sai_byte,
            f"{len(co) - len(sai_byte)}/{len(co)}" + (f" — lệch `{sai_byte[0]}`" if sai_byte else ""))
    keys = {o.object_name for o in kho.list_objects(BUCKET, recursive=True)}
    duong_dan = {r[8][len(f"s3://{BUCKET}/"):] for _, r in co}
    bk.kiem("Không object mồ côi — tệp bị ai-service từ chối đã bị xoá", keys == duong_dan,
            f"{len(keys)} object / {len(duong_dan)} bản ghi")

    # 3.3 — Hạn mức: đúng lượng đang có.
    for tenant, ten_tenant in ((TENANT_A, "A"), (TENANT_B, "B")):
        cua = [d for d in da_nhan if d.tenant == tenant]
        so, byte = han_muc.get((tenant, "DOCUMENT")), han_muc.get((tenant, "STORAGE_MB"))
        bk.kiem(f"Hạn mức tenant {ten_tenant}: số tài liệu và dung lượng = lượng đang có",
                so == len(cua) and byte == sum(d.kich_thuoc for d in cua),
                f"DOCUMENT {so}/{len(cua)} · STORAGE {byte}/{sum(d.kich_thuoc for d in cua)} byte")

    # 3.4 — Outbox: mỗi tài liệu đúng một sự kiện, đã phát, payload khớp.
    ob = {}
    for agg, tenant, payload, phat, loai, topic in outbox:
        ob.setdefault(agg, []).append((tenant, payload, phat, loai, topic))
    sai_ob = [d.ten_tep for d in da_nhan if len(ob.get(d.id, [])) != 1
              or ob[d.id][0][0] != d.tenant or ob[d.id][0][2] is None
              or ob[d.id][0][3:] != ("DocumentUploaded", "crm.document.v1")
              or ob[d.id][0][1].get("size_bytes") != d.kich_thuoc]
    bk.kiem("Outbox: mỗi tài liệu đúng 1 sự kiện `DocumentUploaded`, đã phát, payload khớp",
            not sai_ob and len(outbox) == len(da_nhan),
            f"{len(outbox)} sự kiện / {len(da_nhan)} tài liệu" + (f" — lệch `{sai_ob[0]}`" if sai_ob else ""))

    # 3.5 — Kafka: consumer UC019 sẽ nhận đúng những gì?
    ban_tin = _doc_kafka(os.environ["E2E_KAFKA"], len(da_nhan))
    theo_khoa: dict[str, set] = {}
    id_tren_kafka = set()
    for b in ban_tin:
        v = json.loads(b.value)
        theo_khoa.setdefault(b.key.decode(), set()).add(b.partition)
        if b.key.decode() == v["tenant_id"]:
            id_tren_kafka.add(v["payload"]["document_id"])
    bk.kiem("Kafka: đủ sự kiện, khoá bản tin = `tenant_id`, `document_id` khớp CSDL",
            id_tren_kafka == set(theo_id) and set(theo_khoa) <= tenant_co,
            f"{len(ban_tin)} bản tin, {len(id_tren_kafka)} tài liệu khớp")
    bk.kiem("Kafka: mỗi tenant nằm trọn MỘT phân vùng (giữ thứ tự)",
            all(len(p) == 1 for p in theo_khoa.values()),
            " · ".join(f"{k[:8]}… → {sorted(p)}" for k, p in sorted(theo_khoa.items())))

    # 3.6 — Đủ cho UC019 (Ngày 4) bắt đầu chưa.
    cho_nap = [r for _, r in co if r[10] != "PENDING" or r[11] is not None or r[14] != 0]
    bk.kiem("Sẵn sàng cho UC019: mọi tài liệu `PENDING`, chưa lỗi, `chunk_count` = 0, chưa có đoạn",
            not cho_nap and so_doan == 0, f"{len(co) - len(cho_nap)}/{len(co)} · knowledge_chunks = {so_doan}")
    return bk.in_ra()


if __name__ == "__main__":
    # Danh sách lượt đã nhận lưu ra tệp để `e2e-uc018.sh soi` chạy LẠI riêng phần 3 — dùng để kiểm
    # ngược: phá dữ liệu sau khi tải (sửa object, xoá bản ghi) rồi soi, bảng kiểm phải đỏ.
    so_do = Path(os.environ["E2E_STATE"]) / "da_nhan.json"
    if "--chi-soi" in sys.argv:
        da_nhan.extend(DaNhan(**d) for d in json.loads(so_do.read_text(encoding="utf-8")))
        sys.exit(1 if phan_3_soi_du_lieu() else 0)
    sai = phan_1_manifest() + phan_1b_nguoi_dung_that() + phan_2_han_muc()
    so_do.write_text(json.dumps([asdict(d) for d in da_nhan], ensure_ascii=False), encoding="utf-8")
    sai += phan_3_soi_du_lieu()
    sys.exit(1 if sai else 0)
