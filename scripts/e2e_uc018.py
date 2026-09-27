"""UC018 đầu-cuối: java-core thật → kho S3 thật → ai-service thật. Gọi từ scripts/e2e-uc018.sh.

Hai phần, mỗi phần một tenant:
  1. Tenant A (gói STARTER, 100 tài liệu): 25 tệp của data/kb_samples/manifest.csv qua java-core,
     so mã HTTP và mã lỗi với cột ma_http / ma_loi — cổng ra Ngày 3.
  2. Tenant B (gói TRIAL, 20 tài liệu): 21 lượt tải — mốc 80% ở lượt 16, 100% ở lượt 20, 409 ở 21.

In bảng markdown để dán thẳng vào báo cáo. Thoát khác 0 nếu có ca sai.
"""

import csv
import os
import subprocess
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
MAU = REPO / "data" / "kb_samples"
URL = os.environ["E2E_JAVA_CORE_URL"] + "/api/v1/documents"
TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"
GIOI_HAN = 20 * 1024 * 1024


def token(tenant: str) -> str:
    """JWT RS256 từ scripts/dev-jwt.sh — cùng cặp khoá java-core đang tin (DEV_JWT_DIR)."""
    kq = subprocess.run(
        [str(REPO / "scripts" / "dev-jwt.sh"), tenant],
        capture_output=True, text=True, check=True, env=os.environ.copy(),
    )
    return kq.stdout.strip()


def tai_len(tok: str, ten: str, du_lieu: bytes, title: str, language: str = "vi") -> tuple[int, dict]:
    r = httpx.post(
        URL,
        headers={"Authorization": f"Bearer {tok}", "X-Trace-Id": "e2e-uc018"},
        files={"file": (ten, du_lieu, "application/octet-stream")},
        data={"title": title, "language": language},
        timeout=60,
    )
    return r.status_code, r.json()


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
        ma, body = tai_len(tok, r["file"], du_lieu, r["title"], r["language"])
        code = body.get("code") or ""
        dung = str(ma) == r["ma_http"] and (not r["ma_loi"] or code == r["ma_loi"])
        ver = body.get("data", {}).get("version", "") if ma == 202 else ""
        sai += not dung
        print(f"| {i} | `{r['file']}` | {r['ma_http']} {r['ma_loi']} | {ma} | {code} | {ver} | "
              f"{'✅' if dung else '❌'} |")
    print(f"\n**{len(dong) - sai}/{len(dong)}** tệp đúng mã HTTP.\n")
    return sai


def phan_2_han_muc() -> int:
    tok = token(TENANT_B)
    print("### 2. Hạn mức (tenant B, gói TRIAL = 20 tài liệu)\n")
    print("| Lượt | HTTP | `code` | used / quota | % | `warnedAt` | `blockedAt` |")
    print("|---|---|---|---|---|---|---|")
    ket_qua = {}
    for i in range(1, 22):
        ma, body = tai_len(tok, f"tai-lieu-{i:02d}.txt", f"Nội dung {i}".encode(), f"Tài liệu {i:02d}")
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


if __name__ == "__main__":
    sys.exit(1 if phan_1_manifest() + phan_2_han_muc() else 0)
