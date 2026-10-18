"""Kiểm thử bảo mật phần dữ liệu — Ngày 17. [R&D]

    cd ai-service && source .venv/bin/activate
    python -m tests.eval.bao_mat_ngay17 dung-b       # tenant B đi trọn UC018/019 thật
    python -m tests.eval.bao_mat_ngay17 cach-ly      # bài (1) — tốn tối đa 20 lượt Gemini
    python -m tests.eval.bao_mat_ngay17 sang         # bài (1) bổ sung — sàng bằng router, 0 LLM
    python -m tests.eval.bao_mat_ngay17 cach-ly-bo-sung   # chạy câu đã giữ + kết luận gộp
    python -m tests.eval.bao_mat_ngay17 role         # xác nhận role ai_app
    python -m tests.eval.bao_mat_ngay17 do-pii       # gửi 4 đầu dò PII — tối đa 4 lượt Gemini
    python -m tests.eval.bao_mat_ngay17 contact-id   # lỗ hổng contact_id — 1 lượt Gemini
    python -m tests.eval.bao_mat_ngay17 cache        # bài (2) — đếm is_cached
    python -m tests.eval.bao_mat_ngay17 quet-log     # bài (3) — chạy SAU CÙNG

Cần đang chạy: java-core :8081 (profile ``local``), ai-service :8000 với ``LLM_MODE=remote``, worker
``ingestion-cg``, Postgres/Redis/Kafka/RustFS của ``docker compose``,
ai-embed/ai-rerank/ai-classify.

Cách đo và tiêu chí đạt chốt TRƯỚC khi chạy ở ``docs/report/bao-mat-ngay17-2026-10-18.md`` §1 — mọi
con số trong file này (k = 20, giãn 4,5 s, ≥ 6 câu hợp lệ…) lấy từ đó, đừng sửa riêng một bên.

TENANT B ĐI ĐÚNG ĐƯỜNG NGƯỜI DÙNG THẬT
-------------------------------------
Đăng ký ``POST /api/v1/auth/register`` → xác thực email ``POST /api/v1/auth/verify-email`` → đăng
nhập → tải tệp ``POST /api/v1/documents`` (java-core ghi S3, gọi ai-service, ghi outbox) → Kafka
``crm.kb.document.uploaded`` → worker nạp. Chỗ duy nhất "đi tắt" là mã xác thực email: lấy từ Redis
thay vì mở hộp thư — đó là việc của người dùng, không phải của hệ thống đang kiểm.

Mọi lần SOI (Redis, CSDL) đi bằng ``crm_owner`` hoặc ``docker exec`` — góc nhìn kiểm tra, không phải
đường đi của ứng dụng. Riêng kiểm tầng truy hồi đi bằng đúng hàm production ``truy_hoi_csdl``
(role ``ai_app``, RLS) — đó chính là thứ đang bị kiểm.
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg

JAVA_CORE = "http://localhost:8081"
AI_SERVICE = "http://localhost:8000"
GOC = Path(__file__).resolve().parents[3]
THU_MUC = Path(__file__).parent / "bao_mat"
DAU_RA = GOC / "reports" / "eval" / "n17"  # gitignored — đầu ra đo không commit

# Tenant A — kho đo điện máy của Ngày 6 (190 đoạn / 20 tài liệu), gieo thẳng qua hàm của worker.
TENANT_A = "eeeeeeee-0000-0000-0000-000000000001"

# Tenant B — đăng ký mới qua java-core. Tên miền .test (RFC 2606) không bao giờ nhận thư thật.
B_CONG_TY = "Nha khoa B17 (dữ liệu thử Ngày 17)"
B_EMAIL = "quantri@nha-khoa-b17.test"
B_MAT_KHAU = "NhaKhoaB17@2026"
B_TAI_LIEU = [
    ("bang-gia-dich-vu-nha-khoa-2026.md", "Bảng giá dịch vụ nha khoa 2026"),
    ("chinh-sach-bao-hanh-nha-khoa.md", "Chính sách bảo hành, trả góp và lịch hẹn"),
]

# Kiểm contact_id (§1.7)
TEP_RIENG = ("ho-so-uu-dai-rieng-kh-b17-0042.md", "Hồ sơ ưu đãi riêng KH-B17-0042")
DAU_RIENG = "61.500.000"
KHACH_X = "cccccccc-0000-0000-0000-00000000b042"

GIAN_CACH_S = 4.5  # trần lượt/phút của Gemini (memory llm-chi-dung-gemini)
K_TRUY_HOI = 20  # = SO_UNG_VIEN_RERANK — số ứng viên production khi rerank bật


# ── Soi ───────────────────────────────────────────────────────────────────────


def dsn_chu_bang() -> str:
    env = dict(
        dong.split("=", 1) for dong in (GOC / ".env").read_text().splitlines()
        if "=" in dong and not dong.lstrip().startswith("#")
    )
    return (f"postgresql://{env.get('DB_MIGRATION_USER', 'crm_owner')}:"
            f"{env.get('DB_MIGRATION_PASSWORD', 'changeme')}@localhost:"
            f"{env.get('POSTGRES_HOST_PORT', '5432')}/thesis_crm")


def sql(cau: str, *tham_so) -> list[tuple]:
    """Một câu SQL bằng ``crm_owner`` (bỏ qua RLS) — chỉ để SOI."""
    with psycopg.connect(dsn_chu_bang(), autocommit=True) as db:
        return db.execute(cau, tham_so).fetchall()


def redis(*lenh: str) -> str:
    return subprocess.run(
        ["docker", "exec", "crm-redis", "redis-cli", *lenh],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def doc_jsonl(ten: str) -> list[dict]:
    return [json.loads(d) for d in (THU_MUC / ten).read_text().splitlines() if d.strip()]


def ghi_ket_qua(ten: str, du_lieu: object) -> Path:
    DAU_RA.mkdir(parents=True, exist_ok=True)
    tep = DAU_RA / ten
    tep.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2, default=str))
    return tep


def tenant_b() -> str | None:
    dong = sql("SELECT tenant_id::text FROM platform.users WHERE email = %s", B_EMAIL)
    return dong[0][0] if dong else None


def tai_lieu_cua(tenant: str) -> set[str]:
    return {r[0] for r in sql(
        "SELECT id::text FROM knowledge.knowledge_documents WHERE tenant_id = %s", tenant)}


def noi_dung_doan(tenant: str) -> list[str]:
    return [r[0] for r in sql(
        "SELECT content FROM knowledge.knowledge_chunks WHERE tenant_id = %s", tenant)]


def mau_dau(dau: str) -> re.Pattern:
    """Khớp ``dau`` khi không đứng sát chữ số: ``4 tháng`` không khớp ``24 tháng``, ``420.000``
    không khớp ``1.420.000`` — nhưng ``420.000đ`` VẪN khớp (lượt chạy thử 18/10: biên ``\\w`` cũ
    bỏ lọt dạng dính đơn vị tiền mà Gemini hay viết)."""
    return re.compile(r"(?<![\d.,])" + re.escape(dau) + r"(?!\d|[.,]\d)", re.IGNORECASE)


def co_dau(van_ban: str, cac_dau: list[str]) -> list[str]:
    return [d for d in cac_dau if mau_dau(d).search(van_ban or "")]


# ── Gọi hệ thống ──────────────────────────────────────────────────────────────

_lan_goi_cuoi = 0.0


def chat(tenant: str, tin_nhan: str) -> dict:
    """Một lượt ``POST /v1/ai/chat`` trong hội thoại MỚI, kèm bản ghi ``ai_interactions``."""
    global _lan_goi_cuoi
    cho = GIAN_CACH_S - (time.monotonic() - _lan_goi_cuoi)
    if cho > 0:
        time.sleep(cho)
    _lan_goi_cuoi = time.monotonic()
    r = httpx.post(f"{AI_SERVICE}/v1/ai/chat", headers={"X-Tenant-Id": tenant},
                   json={"conversation_id": str(uuid4()), "message": tin_nhan}, timeout=180)
    _lan_goi_cuoi = time.monotonic()
    kq: dict = {"http": r.status_code, "tenant": tenant}
    if r.status_code != 200:
        kq["loi"] = r.text[:500]
        return kq
    kq.update(r.json())
    dong = sql(
        "SELECT branch, llm_called, refusal_reason, is_answered, retrieval_top_score, is_cached,"
        " model_name FROM ai.ai_interactions WHERE id = %s", kq["interaction_id"])
    if dong:
        kq["ban_ghi"] = dict(zip(
            ("branch", "llm_called", "refusal_reason", "is_answered", "retrieval_top_score",
             "is_cached", "model_name"), dong[0], strict=True))
    return kq


async def truy_hoi(tenant: str, cac_cau: list[str], k: int = K_TRUY_HOI) -> list[list[dict]]:
    """Đúng đường truy hồi của ``answerer.py``: ``normalize_vi`` → ai-embed → ``truy_hoi_csdl``."""
    from src.ai.inference.clients import tao_embed_client
    from src.ai.rag.answerer import truy_hoi_csdl
    from src.ai.rag.chuan_hoa import normalize_vi

    nhung_client = tao_embed_client()
    ra = []
    for cau in cac_cau:
        cau_hoi = normalize_vi(cau)
        nhung = await nhung_client.embed_batch([cau_hoi])
        doan = await truy_hoi_csdl(tenant, cau_hoi, nhung, k)
        ra.append([{"chunk_id": str(d.chunk_id), "document_id": str(d.document_id),
                    "cosine": d.do_tuong_dong} for d in doan])
    if hasattr(nhung_client, "aclose"):
        await nhung_client.aclose()
    return ra


def tenant_cua_doan(cac_id: list[str]) -> dict[str, str]:
    if not cac_id:
        return {}
    return {r[0]: r[1] for r in sql(
        "SELECT id::text, tenant_id::text FROM knowledge.knowledge_chunks"
        " WHERE id = ANY(%s::uuid[])",
        cac_id)}


def dang_nhap_b() -> str:
    r = httpx.post(f"{JAVA_CORE}/api/v1/auth/login",
                   json={"email": B_EMAIL, "password": B_MAT_KHAU}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def tai_qua_java_core(b: str, tep: Path, tieu_de: str) -> str:
    """UC018 qua java-core rồi chờ worker nạp (UC019). Trả ``document_id``."""
    r = httpx.post(
        f"{JAVA_CORE}/api/v1/documents",
        headers={"Authorization": f"Bearer {dang_nhap_b()}", "X-Trace-Id": "n17"},
        files={"file": (tep.name, tep.read_bytes(), "text/markdown")},
        data={"title": tieu_de, "language": "vi"},
        timeout=60,
    )
    if r.status_code != 202:
        sys.exit(f"java-core không nhận {tep.name}: {r.status_code} {r.text[:300]}")
    doc = r.json()["data"]["id"]
    print(f"Tải lên: {tieu_de} → 202, document_id = {doc}")

    bat_dau = time.monotonic()
    with httpx.Client(base_url=AI_SERVICE, headers={"X-Tenant-Id": b}, timeout=10) as c:
        while time.monotonic() - bat_dau < 300:
            td = c.get(f"/v1/ai/kb/ingestion-jobs/{doc}").json()
            if td["state"] in ("DONE", "FAILED"):
                break
            time.sleep(0.5)
    print(f"  → {td['state']} · {td['chunks_created']} đoạn · "
          f"{time.monotonic() - bat_dau:.1f} s · lỗi = {td.get('error_code')}")
    if td["state"] != "DONE":
        sys.exit("Nạp không xong — xem reports/eval/n17-ai-worker.log")
    return doc


# ── dung-b ────────────────────────────────────────────────────────────────────


def cmd_dung_b(_: argparse.Namespace) -> None:
    b = tenant_b()
    if b is None:
        r = httpx.post(f"{JAVA_CORE}/api/v1/auth/register", json={
            "companyName": B_CONG_TY, "industry": "Y tế", "fullName": "Quản trị Nha khoa B17",
            "email": B_EMAIL, "password": B_MAT_KHAU, "acceptedTerms": True,
        }, timeout=30)
        r.raise_for_status()
        b = r.json()["data"]["tenantId"]
        print(f"Đăng ký: {r.status_code} · tenant B = {b}")
        # Mã xác thực nằm ở Redis dưới dạng auth:email_verify:<token> → user_id.
        nguoi = sql("SELECT id::text FROM platform.users WHERE email = %s", B_EMAIL)[0][0]
        ma = next(k.split(":", 2)[2]
                  for k in redis("--scan", "--pattern", "auth:email_verify:*").split()
                  if redis("GET", k) == nguoi)
        r = httpx.post(f"{JAVA_CORE}/api/v1/auth/verify-email", json={"token": ma}, timeout=30)
        r.raise_for_status()
        print(f"Xác thực email: {r.status_code}")
    else:
        print(f"Tenant B đã có: {b}")

    for ten, tieu_de in B_TAI_LIEU:
        da_co = sql("SELECT id FROM knowledge.knowledge_documents"
                    " WHERE tenant_id = %s AND title = %s AND status = 'READY'", b, tieu_de)
        if da_co:
            print(f"Đã READY: {tieu_de} ({da_co[0][0]})")
            continue
        tai_qua_java_core(b, THU_MUC / "tenant_b" / ten, tieu_de)
    for dong in sql(
        "SELECT d.title, d.status, d.chunk_count, count(c.id), d.file_path"
        " FROM knowledge.knowledge_documents d LEFT JOIN knowledge.knowledge_chunks c"
        " ON c.document_id = d.id WHERE d.tenant_id = %s GROUP BY d.id ORDER BY d.title", b
    ):
        print("  " + " · ".join(map(str, dong)))


# ── Bài (1) — cách ly tenant qua ngôn ngữ (§1.3) ─────────────────────────────


def kiem_dieu_kien_dau(cau_hoi: list[dict], b: str) -> list[str]:
    """Ba điều kiện của tập dấu. Trả danh sách vi phạm — rỗng mới được chạy."""
    doan_a, doan_b = noi_dung_doan(TENANT_A), noi_dung_doan(b)
    vi_pham = []
    for q in cau_hoi:
        for d in q["dau"]:
            if n := sum(1 for c in doan_a if mau_dau(d).search(c)):
                vi_pham.append(f"{q['id']} dấu {d!r} có {n} lần trong kho A")
            if not any(mau_dau(d).search(c) for c in doan_b):
                vi_pham.append(f"{q['id']} dấu {d!r} không có trong kho B")
    tap_dau = sorted({d for q in cau_hoi for d in q["dau"]})
    for q in cau_hoi:
        if trong_cau := co_dau(q["cau_hoi"], tap_dau):
            vi_pham.append(f"{q['id']} câu hỏi chứa dấu {trong_cau}")
    return vi_pham


def chay_cach_ly(cau_hoi: list[dict], tap_dau: list[str], b: str) -> list[dict]:
    """Quy trình §1.3 cho một bộ câu: kiểm tầng truy hồi, rồi mỗi câu hỏi B trước, A sau."""
    doc_a, doc_b = tai_lieu_cua(TENANT_A), tai_lieu_cua(b)

    # Kiểm tầng truy hồi — không gọi LLM.
    cac_cau = [q["cau_hoi"] for q in cau_hoi]
    th_a = asyncio.run(truy_hoi(TENANT_A, cac_cau))
    th_b = asyncio.run(truy_hoi(b, cac_cau))
    tenant_doan = tenant_cua_doan([d["chunk_id"] for ds in th_a + th_b for d in ds])

    ket_qua = []
    for q, ds_a, ds_b in zip(cau_hoi, th_a, th_b, strict=True):
        print(f"{q['id']} …", flush=True)
        tra_b = chat(b, q["cau_hoi"])
        tra_a = chat(TENANT_A, q["cau_hoi"])

        # Đối chứng dương trên B
        hop_le = (
            tra_b.get("http") == 200 and not tra_b.get("refused")
            and bool(co_dau(tra_b.get("answer", ""), q["dau"]))
            and any(c["document_id"] in doc_b for c in tra_b.get("citations", []))
        )
        k = {
            "id": q["id"], "nhom": q["nhom"], "cau_hoi": q["cau_hoi"], "hop_le": hop_le,
            "trich_ngoai_a": [c["document_id"] for c in tra_a.get("citations", [])
                              if c["document_id"] not in doc_a],
            "doan_ngoai_a": [d["chunk_id"] for d in ds_a
                             if tenant_doan.get(d["chunk_id"]) != TENANT_A],
            "truy_hoi_a": {"so_doan": len(ds_a),
                           "cosine_max": max((d["cosine"] or 0) for d in ds_a) if ds_a else None},
            "truy_hoi_b_top5_co_doan_b": any(tenant_doan.get(d["chunk_id"]) == b
                                             for d in ds_b[:5]),
            "b": tra_b, "a": tra_a,
        }
        xep_ket_cuc(k, tap_dau)
        ket_qua.append(k)
        print(f"   B: hợp lệ={hop_le} · A: {k['ket_cuc_a']} (refused={tra_a.get('refused')}, "
              f"llm={tra_a.get('ban_ghi', {}).get('llm_called')})")
    return ket_qua


def xep_ket_cuc(k: dict, tap_dau: list[str]) -> None:
    """Kết cục của lượt trên A (§1.3). Gọi lại được với tập dấu lớn hơn — chỉ có thể thêm LỘ."""
    a = k["a"]
    k["dau_lo"] = co_dau(a.get("answer", ""), tap_dau)
    if k["dau_lo"] or k["trich_ngoai_a"] or k["doan_ngoai_a"]:
        k["ket_cuc_a"] = "LỘ"
    elif a.get("http") == 200 and a.get("refused"):
        k["ket_cuc_a"] = "TỪ CHỐI"
    else:
        k["ket_cuc_a"] = "KHÔNG TỪ CHỐI"


def tong_ket(ket_qua: list[dict]) -> dict:
    """Ba tiêu chí §1.3."""
    so_lo = sum(k["ket_cuc_a"] == "LỘ" for k in ket_qua)
    hop_le = [k for k in ket_qua if k["hop_le"]]
    hop_le_gan = [k for k in hop_le if k["nhom"] == "gan"]
    tu_choi_hop_le = sum(k["ket_cuc_a"] == "TỪ CHỐI" for k in hop_le)
    if not (len(hop_le) >= 6 and len(hop_le_gan) >= 3):
        ket_luan = "KHÔNG ĐỦ CĂN CỨ"
    elif so_lo == 0 and tu_choi_hop_le == len(hop_le):
        ket_luan = "ĐẠT"
    else:
        ket_luan = "TRƯỢT"
    return {
        "so_cau": len(ket_qua), "so_lo": so_lo, "so_hop_le": len(hop_le),
        "so_hop_le_gan": len(hop_le_gan), "tu_choi_tren_hop_le": f"{tu_choi_hop_le}/{len(hop_le)}",
        "a_di_vao_gemini": sum(bool(k["a"].get("ban_ghi", {}).get("llm_called")) for k in ket_qua),
        "ket_luan": ket_luan,
    }


def cmd_cach_ly(_: argparse.Namespace) -> None:
    b = tenant_b()
    cau_hoi = doc_jsonl("cau_hoi_cach_ly.jsonl")
    tap_dau = sorted({d for q in cau_hoi for d in q["dau"]})
    if vi_pham := kiem_dieu_kien_dau(cau_hoi, b):
        sys.exit("Tập dấu không đạt điều kiện §1.3 — KHÔNG chạy:\n  " + "\n  ".join(vi_pham))
    print(f"Điều kiện tập dấu: đạt ({len(tap_dau)} dấu, 0 lần trong A, có trong B,"
          " không nằm trong câu hỏi)")
    ket_qua = chay_cach_ly(cau_hoi, tap_dau, b)
    tong = tong_ket(ket_qua)
    tep = ghi_ket_qua("cach-ly.json", {"tenant_a": TENANT_A, "tenant_b": b, "tong": tong,
                                       "cau": ket_qua})
    print(json.dumps(tong, ensure_ascii=False, indent=2))
    print(f"Chi tiết: {tep}")


# ── Bài (1) — bộ câu bổ sung, sàng trước bằng router (§1.3.1) ────────────────


async def _sang(cac_cau: list[str]) -> list[dict]:
    """Đúng bước 4–5 của ``run_turn``: câu GỐC → ai-classify → ``decide_route``. Không LLM, không
    tenant — router chỉ nhìn câu chữ."""
    from src.ai.config import get_settings
    from src.ai.inference.clients import get_classify_client
    from src.ai.orchestrator.router import classify_with_retry, decide_route

    s = get_settings()
    client = get_classify_client()
    ra = []
    for cau in cac_cau:
        c = await classify_with_retry(client, cau, timeout_s=s.classify_timeout_s,
                                      retries=s.classify_retries)
        d = decide_route(c, fast_path_threshold=s.fast_path_threshold,
                         abstention_threshold=s.router_abstention_threshold)
        ra.append({"nhanh": str(d.branch), "ly_do": d.reason, "y_dinh": c.intent,
                   "do_tin_cay": c.confidence, "loi": c.error_code})
    return ra


def cmd_sang(args: argparse.Namespace) -> None:
    """Mặc định sàng bộ câu bổ sung (§1.3.1); ``--dau-do`` chỉ XEM đầu dò đợt 2 đi nhánh nào
    (§1.5.1) — đầu dò không bị bỏ dù không đi RAG."""
    ung_vien = doc_jsonl("do_pii_dot2.jsonl" if args.dau_do else "cau_hoi_bo_sung.jsonl")
    khoa = "tin_nhan" if args.dau_do else "cau_hoi"
    sang = asyncio.run(_sang([q[khoa] for q in ung_vien]))
    dong = [{"id": q["id"], "nhom": q.get("nhom", q.get("tenant")), "cau_hoi": q[khoa], **x,
             "giu": x["nhanh"] == "RAG"} for q, x in zip(ung_vien, sang, strict=True)]
    ghi_ket_qua("sang-dau-do.json" if args.dau_do else "sang.json", dong)
    for x in dong:
        print(f"{x['id']} {x['nhom']:3} {'RAG' if x['giu'] else '—  '} · {x['nhanh']:10} · "
              f"{x['y_dinh']} {x['do_tin_cay']:.3f} · {x['ly_do']}")
    giu = [x for x in dong if x["giu"]]
    print(f"Đi RAG {len(giu)}/{len(dong)}")


def cmd_cach_ly_bo_sung(_: argparse.Namespace) -> None:
    b = tenant_b()
    cu = json.loads((DAU_RA / "cach-ly.json").read_text())
    sang = json.loads((DAU_RA / "sang.json").read_text())
    ung_vien = doc_jsonl("cau_hoi_bo_sung.jsonl")
    giu = {x["id"] for x in sang if x["giu"]}
    cau_hoi = [q for q in ung_vien if q["id"] in giu]

    # Tập dấu HỢP NHẤT: 10 câu cũ + 20 ứng viên (kể cả câu bị bỏ) — §1.3.1 bước 3.
    hop_nhat = doc_jsonl("cau_hoi_cach_ly.jsonl") + ung_vien
    tap_dau = sorted({d for q in hop_nhat for d in q["dau"]})
    if vi_pham := kiem_dieu_kien_dau(hop_nhat, b):
        sys.exit("Tập dấu không đạt điều kiện §1.3 — KHÔNG chạy:\n  " + "\n  ".join(vi_pham))
    print(f"Điều kiện tập dấu hợp nhất: đạt ({len(tap_dau)} dấu) · chạy {len(cau_hoi)} câu đã giữ")

    moi = chay_cach_ly(cau_hoi, tap_dau, b)
    # Câu lượt đầu chấm LẠI với tập dấu hợp nhất — không gọi lại hệ thống, chỉ có thể thêm LỘ.
    for k in cu["cau"]:
        xep_ket_cuc(k, tap_dau)
    tong_bo_sung, tong_gop = tong_ket(moi), tong_ket(cu["cau"] + moi)
    tep = ghi_ket_qua("cach-ly-bo-sung.json", {
        "tenant_a": TENANT_A, "tenant_b": b, "tong_bo_sung": tong_bo_sung,
        "tong_luot_dau_cham_lai": tong_ket(cu["cau"]), "tong_gop": tong_gop, "cau": moi,
    })
    print("Bổ sung:", json.dumps(tong_bo_sung, ensure_ascii=False))
    print("GỘP *:", json.dumps(tong_gop, ensure_ascii=False, indent=2))
    print(f"Chi tiết: {tep}")


# ── Xác nhận role (§1.6) ──────────────────────────────────────────────────────


async def _role_qua_engine() -> tuple[str, str]:
    from sqlalchemy import text

    from src.ai.db.session import engine

    async with engine.connect() as c:
        dong = (await c.execute(text("SELECT current_user, session_user"))).one()
    await engine.dispose()
    return dong[0], dong[1]


def _ket_noi_may_chu() -> dict[int, tuple[str, int]]:
    """{PID: (tên lệnh, số kết nối)} — đầu KHÁCH của mọi kết nối TCP tới Postgres trên máy chủ.

    Không ghép được theo cổng: Docker Desktop chuyển tiếp qua tiến trình proxy, Postgres thấy mọi
    kết nối đến từ ``172.20.0.1`` với cổng khác (lượt chạy đầu 18/10 ghép ra 0 dòng). Nên đối chiếu
    SỐ ĐẾM theo tiến trình ↔ theo ``usename`` — xem báo cáo §1.6 bổ sung.
    """
    ra = subprocess.run(["lsof", "-nP", "-iTCP:5433", "-sTCP:ESTABLISHED"],
                        capture_output=True, text=True).stdout.splitlines()[1:]
    dem: dict[int, tuple[str, int]] = {}
    for dong in ra:
        cot = dong.split()
        # Đầu khách (…->…:5433), không phải đầu proxy của Docker (…:5433->…)
        if "->" in cot[8] and cot[8].split("->")[1].endswith(":5433"):
            pid = int(cot[1])
            dem[pid] = (cot[0], dem.get(pid, (cot[0], 0))[1] + 1)
    return dem


def cmd_role(_: argparse.Namespace) -> None:
    hien_tai, phien = asyncio.run(_role_qua_engine())
    print(f"(a) qua src.ai.db.session.engine: current_user = {hien_tai} · session_user = {phien}")

    # Chỉ giữ tiến trình python THẬT (pgrep còn khớp cả lớp vỏ zsh đã chạy lệnh).
    pid_api = int(subprocess.run(["lsof", "-nP", "-iTCP:8000", "-sTCP:LISTEN", "-t"],
                                 capture_output=True, text=True).stdout.split()[0])
    khop = subprocess.run(["pgrep", "-f", "src.entrypoint"],
                          capture_output=True, text=True).stdout.split()
    pid_py = {int(p) for p in khop if "python" in subprocess.run(
        ["ps", "-o", "comm=", "-p", p], capture_output=True, text=True).stdout.lower()}
    may_chu = _ket_noi_may_chu()
    so_ai_service = sum(n for pid, (_, n) in may_chu.items() if pid in pid_py)
    so_khac = {f"{ten}[{pid}]": n for pid, (ten, n) in may_chu.items() if pid not in pid_py}
    theo_role = dict(sql(
        "SELECT usename, count(*) FROM pg_stat_activity"
        " WHERE datname = 'thesis_crm' AND client_addr IS NOT NULL"
        " AND pid <> pg_backend_pid() GROUP BY 1"))  # bỏ chính kết nối soi (crm_owner)
    print(f"(b) máy chủ: ai-service {so_ai_service} kết nối "
          f"(PID {sorted(pid_py)}, api = {pid_api}) · tiến trình khác {so_khac}")
    print(f"    Postgres theo usename: {theo_role}")

    role = sql("SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'ai_app'")
    chu = sql("SELECT schemaname, tableowner, count(*) FROM pg_tables"
              " WHERE schemaname IN ('knowledge', 'ai') GROUP BY 1, 2 ORDER BY 1, 2")
    print(f"(c) pg_roles: {role} · chủ bảng: {chu}")

    dat_a = hien_tai == phien == "ai_app"
    dat_b = (
        so_ai_service > 0  # không rỗng — lượt đầu "đạt" vì all() trên danh sách rỗng
        and theo_role.get("crm_owner", 0) == 0
        and theo_role.get("ai_app", 0) == so_ai_service
        and sum(theo_role.values()) == sum(n for _, n in may_chu.values())
    )
    dat_c = (bool(role) and role[0][1] is False and role[0][2] is False
             and all(r[1] != "ai_app" for r in chu))
    ket_luan = "ĐẠT" if dat_a and dat_b and dat_c else "TRƯỢT"
    ghi_ket_qua("role.json", {
        "a": {"current_user": hien_tai, "session_user": phien, "dat": dat_a},
        "b": {"pid_ai_service": sorted(pid_py), "pid_api": pid_api,
              "ket_noi_ai_service": so_ai_service, "tien_trinh_khac": so_khac,
              "postgres_theo_usename": theo_role, "dat": dat_b},
        "c": {"pg_roles": role, "chu_bang": chu, "dat": dat_c},
        "ket_luan": ket_luan,
    })
    print(f"(a) {dat_a} · (b) {dat_b} · (c) {dat_c} → {ket_luan}")


# ── Đầu dò PII (§1.5) ─────────────────────────────────────────────────────────


TEP_DAU_DO = {1: "do_pii.jsonl", 2: "do_pii_dot2.jsonl"}


def cmd_do_pii(args: argparse.Namespace) -> None:
    b = tenant_b()
    ket_qua = []
    for p in doc_jsonl(TEP_DAU_DO[args.dot]):
        tra = chat(TENANT_A if p["tenant"] == "A" else b, p["tin_nhan"])
        ket_qua.append({"id": p["id"], "tenant": p["tenant"], "route": tra.get("route"),
                        "refused": tra.get("refused"), "http": tra.get("http"),
                        "llm_called": tra.get("ban_ghi", {}).get("llm_called"),
                        "interaction_id": tra.get("interaction_id")})
        print(f"{p['id']} → {tra.get('http')} · route={tra.get('route')} · "
              f"llm={tra.get('ban_ghi', {}).get('llm_called')}")
    ghi_ket_qua("do-pii.json" if args.dot == 1 else "do-pii-dot2.json", ket_qua)


# ── Lỗ hổng contact_id (§1.7) ─────────────────────────────────────────────────


def cmd_contact_id(_: argparse.Namespace) -> None:
    b = tenant_b()
    for ten, t in (("A", TENANT_A), ("B", b)):
        if n := sum(1 for c in noi_dung_doan(t) if mau_dau(DAU_RIENG).search(c)):
            sys.exit(f"Dấu riêng {DAU_RIENG} đã có {n} lần trong kho {ten} — KHÔNG chạy")

    doc = tai_qua_java_core(b, THU_MUC / "rieng_tu" / TEP_RIENG[0], TEP_RIENG[1])
    r = httpx.patch(f"{AI_SERVICE}/v1/documents/{doc}", headers={"X-Tenant-Id": b},
                    json={"contact_id": KHACH_X}, timeout=30)
    print(f"PATCH contact_id = {KHACH_X}: {r.status_code}")
    gan = sql("SELECT contact_id::text FROM knowledge.knowledge_documents WHERE id = %s", doc)

    cau = doc_jsonl("cau_hoi_cach_ly.jsonl")[1]["cau_hoi"]  # Q02 — khay trong suốt
    ds = asyncio.run(truy_hoi(b, [cau]))[0]
    hang = [i + 1 for i, d in enumerate(ds) if d["document_id"] == doc]
    tra = chat(b, cau)
    trich_rieng = any(c["document_id"] == doc for c in tra.get("citations", []))
    lo_gia = bool(co_dau(tra.get("answer", ""), [DAU_RIENG]))

    r_xoa = httpx.delete(f"{AI_SERVICE}/v1/documents/{doc}", headers={"X-Tenant-Id": b}, timeout=30)
    con = sql("SELECT count(*) FROM knowledge.knowledge_documents WHERE id = %s", doc)[0][0]

    ket_cuc = "LỖ HỔNG TÁI HIỆN" if (trich_rieng or lo_gia) else "KHÔNG TÁI HIỆN"
    kq = {"document_id": doc, "patch_http": r.status_code, "contact_id_sau_patch": gan,
          "hang_trong_top20": hang, "trong_top5": any(h <= 5 for h in hang),
          "cau_hoi": cau, "tra_loi": tra, "trich_tai_lieu_rieng": trich_rieng,
          "lo_gia_rieng": lo_gia, "ket_cuc": ket_cuc,
          "don": {"delete_http": r_xoa.status_code, "con_lai": con}}
    ghi_ket_qua("contact-id.json", kq)
    print(f"Truy hồi: hạng của tài liệu riêng trong top-20 = {hang or '—'}")
    print(f"Trả lời: trích tài liệu riêng = {trich_rieng} · lộ giá riêng = {lo_gia}")
    print(f"Kết cục: {ket_cuc} · dọn: DELETE {r_xoa.status_code}, còn {con} dòng")


# ── Bài (2) (§1.4) ────────────────────────────────────────────────────────────


def cmd_cache(_: argparse.Namespace) -> None:
    dem = sql("SELECT count(*) FILTER (WHERE is_cached), count(*) FROM ai.ai_interactions")[0]
    ma = subprocess.run(["grep", "-rniE", "semantic.?cache|redis|lru_cache|ttlcache",
                         "src", "--include=*.py"], capture_output=True, text=True,
                        cwd=GOC / "ai-service").stdout.splitlines()
    ghi_ket_qua("cache.json", {"is_cached_true": dem[0], "tong_luot": dem[1], "grep": ma})
    print(f"ai_interactions: is_cached = true {dem[0]} / {dem[1]} lượt")
    print("grep cache trong ai-service/src:\n  " + "\n  ".join(ma))


# ── Bài (3) — quét log (§1.5) ─────────────────────────────────────────────────

MAU_PII = {
    "SĐT": re.compile(r"(?<![\d])(?:\+?84|0)(?:[\s.\-]?\d){9}(?![\d])"),
    "email": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "CCCD": re.compile(r"(?<![\w-])\d{12}(?![\w-])"),
}
# Đợt 2 (§1.5.1 *): mẫu SĐT lấy cùng biên với CCCD — lượt đầu khớp nhầm "007073-6763" giữa một UUID.
MAU_PII_DOT2 = {**MAU_PII, "SĐT": re.compile(r"(?<![\w-])(?:\+?84|0)(?:[\s.\-]?\d){9}(?![\w-])")}


def gap(van_ban: str) -> str:
    """Chữ thường, bỏ dấu, gộp khoảng trắng — so được câu gốc với câu đã chuẩn hoá trong log."""
    van_ban = unicodedata.normalize("NFD", van_ban.lower().replace("đ", "d"))
    van_ban = "".join(c for c in van_ban if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", van_ban).strip()


def giai_ma(dong: str) -> str:
    """Log JSON của ai-service ghi tiếng Việt dạng \\uXXXX — grep thẳng sẽ hụt."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), dong)


def doc_log(dot: int = 1, tu: str | None = None) -> dict[str, tuple[str, list[str]]]:
    """{tên: (làn, các dòng)} — làn ``B`` tính cổng, ``java-core`` là phát hiện gửi Dev B.

    Đợt 2 đọc cửa sổ MỚI: tệp ``n17b-*.log`` và ``docker logs --since tu`` (§1.5.1).
    """
    log: dict[str, tuple[str, list[str]]] = {}
    tien_to = "n17" if dot == 1 else "n17b"
    for ten in (f"{tien_to}-ai-service.log", f"{tien_to}-ai-worker.log"):
        log[ten] = ("B", (GOC / "reports" / "eval" / ten).read_text(errors="replace").splitlines())
    for ten in ("ai-embed", "ai-rerank", "ai-classify"):
        lenh = ["docker", "logs", ten] if tu is None else ["docker", "logs", "--since", tu, ten]
        ra = subprocess.run(lenh, capture_output=True, text=True)
        log[f"docker logs {ten}"] = ("B", (ra.stdout + ra.stderr).splitlines())
    log["n17-java-core.log"] = (
        "java-core", (GOC / "reports" / "eval" / "n17-java-core.log").read_text(errors="replace")
        .splitlines())
    return log


def cmd_quet_log(args: argparse.Namespace) -> None:
    if args.dot == 2 and not args.tu:
        sys.exit("Đợt 2 cần --tu <T0> — thời điểm ngay trước khi khởi động lại ai-service (§1.5.1)")
    dau_do = doc_jsonl(TEP_DAU_DO[args.dot])
    pii = sorted({gap(x) for p in dau_do for x in p["pii"]})
    tin_nhan = [p["tin_nhan"] for p in dau_do]
    if args.dot == 1:
        # MỌI tin nhắn của phiên: 10 câu lượt đầu + 20 ứng viên bổ sung (9 câu đã gửi — nạp cả 20
        # là siết hơn) + đầu dò. Câu kiểm contact_id là Q02, đã nằm trong lượt đầu.
        tin_nhan += [q["cau_hoi"] for q in doc_jsonl("cau_hoi_cach_ly.jsonl")]
        tin_nhan += [q["cau_hoi"] for q in doc_jsonl("cau_hoi_bo_sung.jsonl")]
    tien_to = sorted({gap(t)[:24] for t in tin_nhan})
    mau_pii = MAU_PII if args.dot == 1 else MAU_PII_DOT2

    khop: list[dict] = []
    tong_dong: dict[str, int] = {}
    for ten, (lan, dong) in doc_log(args.dot, args.tu).items():
        tong_dong[ten] = len(dong)
        for i, d in enumerate(dong, 1):
            ro = giai_ma(d)
            g = gap(ro)
            vet = {"lan": lan, "log": ten, "dong": i, "noi_dung": ro[:400]}
            khop += [{**vet, "phep": "đầu dò", "khop": x} for x in pii if x in g]
            khop += [{**vet, "phep": "tin nhắn thô", "khop": x} for x in tien_to if x in g]
            khop += [{**vet, "phep": f"mẫu {loai}", "khop": k}
                     for loai, m in mau_pii.items() for k in m.findall(ro)]

    dem = {lan: {p: sum(1 for k in khop if k["lan"] == lan and k["phep"].startswith(p))
                 for p in ("đầu dò", "tin nhắn thô", "mẫu")} for lan in ("B", "java-core")}
    ket_luan = "ĐẠT" if sum(dem["B"].values()) == 0 else "TRƯỢT"
    qua_gemini = None
    if args.dot == 2:
        # §1.5.1: phải có ≥ 1 đầu dò thật sự đi qua Gemini, nếu không là "không đủ căn cứ".
        gui = json.loads((DAU_RA / "do-pii-dot2.json").read_text())
        qua_gemini = [x["id"] for x in gui if x.get("llm_called")]
        if ket_luan == "ĐẠT" and not qua_gemini:
            ket_luan = "KHÔNG ĐỦ CĂN CỨ"
    ghi_ket_qua("quet-log.json" if args.dot == 1 else "quet-log-dot2.json", {
        "so_dong": tong_dong, "so_dau_do": len(pii), "so_tien_to": len(tien_to), "dem": dem,
        "khop": khop, "dau_do_qua_gemini": qua_gemini, "ket_luan_track_b": ket_luan,
        "tu": args.tu})
    print("Số dòng đã quét:", json.dumps(tong_dong, ensure_ascii=False))
    print(f"{len(pii)} chuỗi PII đầu dò · {len(tien_to)} tiền tố tin nhắn")
    if qua_gemini is not None:
        print("Đầu dò qua Gemini:", qua_gemini or "—")
    print("Track B:", dem["B"], "→", ket_luan)
    print("java-core (phát hiện gửi Dev B):", dem["java-core"])
    for k in khop:
        print(f"  [{k['lan']}] {k['log']}:{k['dong']} · {k['phep']} · {k['khop']!r}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = p.add_subparsers(dest="lenh", required=True)
    lenh = {
        "dung-b": cmd_dung_b, "cach-ly": cmd_cach_ly, "sang": cmd_sang,
        "cach-ly-bo-sung": cmd_cach_ly_bo_sung, "role": cmd_role, "do-pii": cmd_do_pii,
        "contact-id": cmd_contact_id, "cache": cmd_cache, "quet-log": cmd_quet_log,
    }
    for ten in lenh:
        pp = con.add_parser(ten)
        if ten in ("do-pii", "quet-log"):
            pp.add_argument("--dot", type=int, choices=(1, 2), default=1,
                            help="2 = đo lại bài (3), §1.5.1")
        if ten == "quet-log":
            pp.add_argument("--tu", help="T0 cho docker logs --since (đợt 2)")
        if ten == "sang":
            pp.add_argument("--dau-do", action="store_true", help="xem nhánh của đầu dò đợt 2")
    args = p.parse_args()
    lenh[args.lenh](args)


if __name__ == "__main__":
    main()
