#!/usr/bin/env python3
"""[R&D] Xuất tham số embedder của router nhánh C ra JSON cho image ai-inference.

VÌ SAO CÓ SCRIPT NÀY
--------------------
``artifacts/router_branch_c.joblib`` là pickle chứa object ``SemanticDenseEmbedder`` —
class nằm ở ``ai-service/src/ai/inference/embedder.py``. Image ``ai-inference`` không có
``joblib`` lẫn code của ai-service, nên ``ai-classify`` chạy trong container không nạp được
embedder và âm thầm rơi về luật từ khoá (phát hiện 05/10).

Embedder thực chất chỉ là bảng IDF + băm MD5/SHA-1 — xuất bảng IDF ra JSON là đủ để
``inference/src/roles/router_embedder.py`` tái tạo đúng vector bằng numpy, không cần pickle.

    python scripts/export_router_embedder.py

Ghi ``artifacts/router_embedder.json`` và THÊM một dòng hash vào ``artifacts/DATA_HASHES.txt``
(không sửa dòng nào đã có).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("ai-service/src").resolve()))

import joblib  # noqa: E402

SRC = Path("artifacts/router_branch_c.joblib")
OUT = Path("artifacts/router_embedder.json")
HASHES = Path("artifacts/DATA_HASHES.txt")


def main() -> int:
    artifact = joblib.load(SRC)
    emb = artifact["embedder"]
    clf = artifact["classifier_lr"]
    payload = {
        "format": "router-embedder/v1",
        "algorithm": "word + char 3/4-gram, md5/sha1 hashing, idf weight, L2 — SemanticDenseEmbedder",
        "source_artifact": str(SRC).replace("\\", "/"),
        "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "dim": int(emb.dim),
        "n_docs": int(emb.n_docs),
        # Thứ tự lớp của LogisticRegression = thứ tự xác suất trong đồ thị ONNX
        "classes": [str(c) for c in clf.classes_],
        "idf": {k: float(v) for k, v in sorted(emb.idf.items())},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"Đã ghi {OUT} ({OUT.stat().st_size / 1024:.1f} KB, {len(payload['idf'])} token IDF)")
    print(f"SHA-256: {digest}")

    lines = HASHES.read_text(encoding="utf-8").splitlines()
    entry = f"{digest}  {OUT.as_posix()}"
    if entry not in lines:
        lines = [ln for ln in lines if not ln.endswith(f"  {OUT.as_posix()}")]
        lines.append(entry)
        HASHES.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Đã thêm hash vào {HASHES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
