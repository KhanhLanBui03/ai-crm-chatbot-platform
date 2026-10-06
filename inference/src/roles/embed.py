"""``MODEL_ROLE=embed`` — encoder bge-m3 chạy ONNX trên CPU. UC019 (lập chỉ mục) và UC023 (truy hồi).

[PRODUCTION]

Endpoint: ``POST /v1/embed`` · ``POST /v1/embed/batch`` · ``GET /v1/model``
Ngân sách độ trễ: p95 120 ms (§5.3).

Ngày 06/10 thay bản vector giả (numpy gieo theo hash) bằng model thật. Bản giả khai
``model_id="BAAI/bge-m3"`` trong khi vector là nhiễu: nạp kho bằng nó là ghi vào CSDL một
không gian vector mang nhãn của không gian khác — đúng thứ bất biến 1 sinh ra để chặn.

ARTIFACT — sinh ở ``notebooks/06_export_onnx.py``, mount lúc chạy, KHÔNG COPY vào image
----------------------------------------------------------------------------------------
    EMBED_MODEL_PATH      mặc định artifacts/models/bge-m3-int8.onnx  (+ .onnx.data cạnh nó)
    EMBED_TOKENIZER_PATH  mặc định artifacts/models/tokenizer.json    (HF BAAI/bge-m3 @ 5617a9f6)
    EMBED_VARIANT         int8 | fp32 — Ngày 7 đổi sang fp32 bằng biến môi trường, cùng code

Graph đã gồm bước lấy token CLS + chuẩn hoá L2 (notebook 06 §2), nên ở đây KHÔNG chuẩn hoá lại:
chuẩn hoá hai lần không sai, nhưng che mất lỗi export quên chuẩn hoá. Test khoá ``‖v‖ ≈ 1``.

``model_version`` = ``"<variant>-<8 ký tự đầu sha256 của .onnx>"`` — ví dụ ``int8-71e2aa91``,
khớp ADR-0021 và ``tests/eval/configs/e3_*.yaml``. Tính từ file lúc nạp chứ không đọc từ biến
môi trường: biến môi trường khai sai được, hash thì không. Giới hạn đã biết: hash chỉ phủ graph
``.onnx``, không phủ ``.onnx.data`` (541 MB, băm mất vài giây mỗi lần khởi động) — sha256 của
``.data`` nằm trong ADR-0021.

MỖI VĂN BẢN MỘT LƯỢT CHẠY — KHÔNG GHÉP LÔ
------------------------------------------
API nhận danh sách, nhưng graph chạy từng văn bản một (lô 1, không pad). Lý do là số đo, đo
06/10 trên 190 đoạn của ``data/kb_samples`` (16–512 token, trung vị 94), 4 luồng, M-series:

    cách chạy             cos với lô 1 (mean / min)    thông lượng
    lô 1                  1 / 1                        9,8 đoạn/s
    lô 32, xếp độ dài     0,98508 / 0,97439            3,1 đoạn/s
    lô 32, không xếp      0,98466 / 0,97570            —

1. **Vector phải là hàm của RIÊNG văn bản đó.** ``quantize_dynamic`` sinh ``DynamicQuantizeLinear``
   — thang lượng tử hoá activation tính trên CẢ tensor, tức trên mọi câu cùng lô và cả vị trí pad.
   Ghép lô thì vector của một đoạn phụ thuộc đoạn nào tình cờ đi cùng nó; câu hỏi lúc chat luôn
   nhúng một mình. Lệch ~0,985 — đúng cỡ ``parity.mean = 0,98476`` của ADR-0021, vốn đo theo lô.
2. **Lô 1 còn nhanh hơn** trên CPU: không tốn phép tính cho vị trí pad, attention O(n²) chạy trên
   độ dài thật của từng câu.

Suy luận chạy tuần tự sau một khoá: session đã ghim ``intra_op = OMP_NUM_THREADS``, hai lượt chạy
song song là hai lần số luồng tranh cùng số vCPU — đúng cái bẫy ``session.py`` mô tả.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import onnxruntime as ort
    from tokenizers import Tokenizer

logger = logging.getLogger("inference.embed")

router = APIRouter(tags=["embed"])

DEFAULT_MODEL_ID = "BAAI/bge-m3"
VECTOR_DIM = 1024  # Chốt 1024 theo ADR-0015
DO_DAI_TOI_DA = 512  # cùng max_length lúc export và đo parity (notebook 06)

MODEL_MAC_DINH = "artifacts/models/bge-m3-int8.onnx"
TOKENIZER_MAC_DINH = "artifacts/models/tokenizer.json"


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Văn bản cần nhúng vector")


class BatchEmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=64, description="Danh sách văn bản nhúng batch")


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int
    model_id: str
    model_version: str


class BatchEmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int
    count: int
    model_id: str
    model_version: str


class ModelInfoResponse(BaseModel):
    model_id: str
    model_version: str | None
    role: str
    dim: int
    device: str
    status: str


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


def _tim_tep(duong_dan: str) -> Path:
    """Đường dẫn tuyệt đối giữ nguyên; tương đối thì thử CWD rồi lần lên các thư mục cha.

    Cùng cách ``classify._find_path``: chạy từ ``inference/`` trên máy thì artifact ở
    ``../artifacts``, trong container thì ở ``/app/artifacts``.
    """
    p = Path(duong_dan)
    if p.is_absolute() or p.is_file():
        return p
    for cha in Path(__file__).resolve().parents:
        if (cha / duong_dan).is_file():
            return cha / duong_dan
    return p


def _sha256(duong_dan: Path) -> str:
    h = hashlib.sha256()
    with duong_dan.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


class BoNhung:
    """Một ONNX session + tokenizer, nạp một lần cho cả vòng đời tiến trình."""

    def __init__(self, duong_model: Path, duong_tokenizer: Path, bien_the: str) -> None:
        from tokenizers import Tokenizer

        from src.session import make_session

        if not duong_tokenizer.is_file():
            raise FileNotFoundError(f"Không tìm thấy tokenizer tại: {duong_tokenizer}")
        self.session: ort.InferenceSession = make_session(duong_model)
        dau_vao = sorted(i.name for i in self.session.get_inputs())
        if dau_vao != ["attention_mask", "input_ids"]:
            raise ValueError(f"Graph nhận {dau_vao}, kỳ vọng input_ids + attention_mask")

        tok = Tokenizer.from_file(str(duong_tokenizer))
        tok.enable_truncation(max_length=DO_DAI_TOI_DA)
        tok.no_padding()  # lô 1 thì không có gì để pad
        self.tokenizer: Tokenizer = tok
        self.model_version = f"{bien_the}-{_sha256(duong_model)[:8]}"
        self._khoa = threading.Lock()

    def nhung(self, texts: list[str]) -> np.ndarray:
        """Trả ma trận ``len(texts) × 1024``, đúng thứ tự đầu vào. Mỗi văn bản một lượt (lô 1)."""
        ket_qua = np.empty((len(texts), VECTOR_DIM), dtype=np.float32)
        for i, ma in enumerate(self.tokenizer.encode_batch(texts)):
            ids = np.asarray([ma.ids], dtype=np.int64)
            with self._khoa:
                (ra,) = self.session.run(
                    ["embedding"], {"input_ids": ids, "attention_mask": np.ones_like(ids)}
                )
            if ra.shape != (1, VECTOR_DIM):
                raise ValueError(f"Model trả hình dạng {ra.shape}, cột CSDL là {VECTOR_DIM} chiều")
            ket_qua[i] = ra[0]
        return ket_qua


_BO_NHUNG: dict[tuple[str, str, str], BoNhung] = {}
_KHOA_NAP = threading.Lock()


def lay_bo_nhung() -> BoNhung:
    """Nạp lười theo bộ (model, tokenizer, biến thể) đang cấu hình.

    Lần ``/ready`` đầu tiên kích hoạt việc nạp (healthcheck của compose và readinessProbe của k8s
    gọi nó trước khi có traffic). Nạp hỏng thì ném lỗi và KHÔNG ghi nhớ — lần sau thử lại, để
    artifact mount muộn vẫn lên được mà không phải khởi động lại pod.
    """
    khoa = (
        str(_tim_tep(os.getenv("EMBED_MODEL_PATH", MODEL_MAC_DINH))),
        str(_tim_tep(os.getenv("EMBED_TOKENIZER_PATH", TOKENIZER_MAC_DINH))),
        os.getenv("EMBED_VARIANT", "int8"),
    )
    with _KHOA_NAP:
        if khoa not in _BO_NHUNG:
            _BO_NHUNG[khoa] = BoNhung(Path(khoa[0]), Path(khoa[1]), khoa[2])
            logger.info("Đã nạp model nhúng %s (%s)", khoa[0], _BO_NHUNG[khoa].model_version)
        return _BO_NHUNG[khoa]


def check_invariants() -> tuple[bool, str]:
    """Bất biến 1 (model_id khớp EXPECTED_MODEL_ID) + model và tokenizer nạp được."""
    expected_id = os.getenv("EXPECTED_MODEL_ID")
    current_id = get_model_id()
    if expected_id and current_id != expected_id:
        return False, (
            f"BẤT BIẾN 1 VI PHẠM: model_id đang nạp ({current_id!r}) khác EXPECTED_MODEL_ID ({expected_id!r}). "
            "Lệch không gian vector dẫn tới truy hồi vô nghĩa (EMBEDDING_MODEL_MISMATCH)."
        )
    try:
        bo = lay_bo_nhung()
    except Exception as e:  # noqa: BLE001 — mọi lỗi nạp phải ra 503, không để /ready trả 500
        return False, f"CHƯA NẠP ĐƯỢC MODEL NHÚNG: {type(e).__name__}: {e}"
    return True, f"Embedding hợp lệ: {current_id} {bo.model_version}"


def _bo_nhung_hoac_503() -> BoNhung:
    try:
        return lay_bo_nhung()
    except Exception as e:
        logger.error("Không nạp được model nhúng: %s", e)
        raise HTTPException(status_code=503, detail="Model nhúng chưa sẵn sàng") from e


# Hàm đồng bộ: FastAPI chạy chúng trong threadpool nên suy luận không chặn vòng sự kiện
# (/health vẫn trả lời trong lúc một lô đang chạy).
@router.post("/v1/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> dict[str, Any]:
    """Tạo vector nhúng 1024 chiều cho một đoạn văn bản."""
    bo = _bo_nhung_hoac_503()
    return {
        "embedding": bo.nhung([req.text])[0].tolist(),
        "dim": VECTOR_DIM,
        "model_id": get_model_id(),
        "model_version": bo.model_version,
    }


@router.post("/v1/embed/batch", response_model=BatchEmbedResponse)
def embed_batch(req: BatchEmbedRequest) -> dict[str, Any]:
    """Tạo vector nhúng cho một danh sách văn bản (tối đa 64 đoạn), cùng thứ tự đầu vào."""
    bo = _bo_nhung_hoac_503()
    embeddings = bo.nhung(req.texts).tolist()
    return {
        "embeddings": embeddings,
        "dim": VECTOR_DIM,
        "count": len(embeddings),
        "model_id": get_model_id(),
        "model_version": bo.model_version,
    }


@router.get("/v1/model", response_model=ModelInfoResponse)
def model_info() -> dict[str, Any]:
    """Thông tin model embedding đang phục vụ."""
    try:
        version, trang_thai = lay_bo_nhung().model_version, "READY"
    except Exception:  # noqa: BLE001 — chỉ là thông tin, lỗi thật đã báo ở /ready
        version, trang_thai = None, "NOT_READY"
    return {
        "model_id": get_model_id(),
        "model_version": version,
        "role": "embed",
        "dim": VECTOR_DIM,
        "device": "CPU",
        "status": trang_thai,
    }
