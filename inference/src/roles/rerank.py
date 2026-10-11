"""``MODEL_ROLE=rerank`` — cross-encoder bge-reranker-v2-m3 chạy ONNX trên CPU. UC023.

[PRODUCTION]

Endpoint: ``POST /v1/rerank`` · ``GET /v1/model``
Ngân sách độ trễ §5.3: p95 300 ms — ngưỡng KẾ HOẠCH, chưa áp dụng (người dùng chốt 11/10/2026: độ
trễ chưa là cổng). Số đo thật ghi ở ADR-0006.

Ngày 15 thay bản giả của Dev B (Jaccard trên tập từ) bằng model thật. Bản giả khai
``model_id="BAAI/bge-reranker-base"`` — một model chỉ huấn luyện cho tiếng Anh và tiếng Trung —
trong khi điểm là phép đếm từ chung: đo chất lượng rerank trên nó là đo một phép đếm.

ARTIFACT — sinh ở ``notebooks/07_export_reranker.py``, mount lúc chạy, KHÔNG COPY vào image
------------------------------------------------------------------------------------------
    RERANK_MODEL_PATH      mặc định artifacts/models/bge-reranker-v2-m3-int8.onnx (+ .onnx.data)
    RERANK_TOKENIZER_PATH  mặc định artifacts/models/bge-reranker-v2-m3-tokenizer.json
                           (HF BAAI/bge-reranker-v2-m3 @ 953dc6f6 — KHÔNG phải tokenizer của bge-m3)
    RERANK_VARIANT         int8 | fp32 — ship fp32 khi cổng parity trượt (ADR-0021), cùng code
    RERANK_MAX_LENGTH      512 — cùng max_length lúc export và đo parity; 256 là đòn bẩy độ trễ

Thiếu file thì ``/ready`` = 503, **không** lùi về Jaccard: điểm giả mang nhãn model thật là đúng
thứ bất biến 1 sinh ra để chặn. Phía ai-service đã có đường suy giảm riêng — ai-rerank lỗi thì bỏ
bước xếp lại, giữ thứ hạng RRF (§3.8.1, ``ai-service/src/ai/rag/answerer.py``).

``model_version`` = ``"<variant>-<8 ký tự đầu sha256 của .onnx>"``, cùng cách ``embed.py``: tính
từ file lúc nạp, không đọc từ biến môi trường. Harness Ngày 15 so chuỗi này với cấu hình đo.

CẶP MÃ HOÁ CHUNG MỘT CHUỖI, ĐẦU RA MỘT LOGIT
---------------------------------------------
``tokenizer.encode(câu_hỏi, đoạn)`` → ``<s> câu hỏi </s></s> đoạn </s>``; cắt ``longest_first`` nên
đoạn dài bị cắt trước, câu hỏi giữ nguyên (notebook 07 §2 kiểm khớp HF từng token). Graph trả
``logit`` hình dạng ``(batch,)``. ``score`` trả về là ``sigmoid(logit)`` ∈ (0, 1) — đơn điệu nên thứ
tự không đổi, cùng thang với hợp đồng cũ (và với ``normalize=True`` của FlagReranker). Sắp xếp
dùng logit, không dùng score: sigmoid bão hoà về 1,0 khi logit rất lớn và làm hoà hai cặp khác nhau.

MỖI CẶP MỘT LƯỢT — KHÔNG GHÉP LÔ
---------------------------------
Cùng lý do ``embed.py``: ``quantize_dynamic`` sinh ``DynamicQuantizeLinear`` — thang lượng tử hoá
activation tính trên CẢ tensor, ghép lô thì điểm của một cặp phụ thuộc cặp nào tình cờ đi cùng nó.
Cổng parity ở notebook 07 cũng đo theo lô 1 — chạy khác cách đã đo là ship một thứ chưa đo.
Suy luận tuần tự sau một khoá: session đã ghim ``intra_op = OMP_NUM_THREADS``.
"""

from __future__ import annotations

import hashlib
import logging
import math
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

logger = logging.getLogger("inference.rerank")

router = APIRouter(tags=["rerank"])

DEFAULT_MODEL_ID = "BAAI/bge-reranker-v2-m3"
DO_DAI_MAC_DINH = 512

MODEL_MAC_DINH = "artifacts/models/bge-reranker-v2-m3-int8.onnx"
TOKENIZER_MAC_DINH = "artifacts/models/bge-reranker-v2-m3-tokenizer.json"


class Candidate(BaseModel):
    chunk_id: str
    text: str


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    candidates: list[Candidate] = Field(..., max_length=20, description="Tối đa 12-20 đoạn ứng viên cần xếp hạng")


class RankedItem(BaseModel):
    chunk_id: str
    score: float
    rank: int


class RerankResponse(BaseModel):
    results: list[RankedItem]
    model_id: str
    model_version: str


class ModelInfoResponse(BaseModel):
    model_id: str
    model_version: str | None
    role: str
    max_length: int
    device: str
    status: str


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


def _tim_tep(duong_dan: str) -> Path:
    """Đường dẫn tuyệt đối giữ nguyên; tương đối thì thử CWD rồi lần lên các thư mục cha.

    Cùng cách ``embed._tim_tep``: chạy từ ``inference/`` trên máy thì artifact ở ``../artifacts``,
    trong container thì ở ``/app/artifacts``. Chép lại thay vì import để pod rerank không nạp mã
    của vai trò khác.
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


def _sigmoid(x: float) -> float:
    """Ổn định số học ở cả hai phía — ``math.exp(-x)`` tràn khi x rất âm."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


class BoXepHang:
    """Một ONNX session + tokenizer, nạp một lần cho cả vòng đời tiến trình."""

    def __init__(
        self, duong_model: Path, duong_tokenizer: Path, bien_the: str, do_dai: int
    ) -> None:
        from tokenizers import Tokenizer

        from src.session import make_session

        if not duong_tokenizer.is_file():
            raise FileNotFoundError(f"Không tìm thấy tokenizer tại: {duong_tokenizer}")
        self.session: ort.InferenceSession = make_session(duong_model)
        dau_vao = sorted(i.name for i in self.session.get_inputs())
        if dau_vao != ["attention_mask", "input_ids"]:
            raise ValueError(f"Graph nhận {dau_vao}, kỳ vọng input_ids + attention_mask")
        dau_ra = [o.name for o in self.session.get_outputs()]
        if dau_ra != ["logit"]:
            raise ValueError(f"Graph trả {dau_ra}, kỳ vọng đúng một đầu ra 'logit' (notebook 07)")

        tok = Tokenizer.from_file(str(duong_tokenizer))
        tok.enable_truncation(max_length=do_dai)  # longest_first: cắt đoạn trước, giữ câu hỏi
        tok.no_padding()  # lô 1 thì không có gì để pad
        self.tokenizer: Tokenizer = tok
        self.do_dai = do_dai
        self.model_version = f"{bien_the}-{_sha256(duong_model)[:8]}"
        self._khoa = threading.Lock()

    def cham(self, cau_hoi: str, cac_doan: list[str]) -> list[float]:
        """Logit của từng cặp (câu hỏi, đoạn), đúng thứ tự đầu vào. Mỗi cặp một lượt (lô 1)."""
        logit = []
        for ma in self.tokenizer.encode_batch([(cau_hoi, d) for d in cac_doan]):
            ids = np.asarray([ma.ids], dtype=np.int64)
            with self._khoa:
                (ra,) = self.session.run(
                    ["logit"], {"input_ids": ids, "attention_mask": np.ones_like(ids)}
                )
            if ra.shape != (1,):
                raise ValueError(f"Model trả hình dạng {ra.shape}, kỳ vọng một logit mỗi cặp")
            logit.append(float(ra[0]))
        return logit


_BO_XEP_HANG: dict[tuple[str, str, str, int], BoXepHang] = {}
_KHOA_NAP = threading.Lock()


def lay_bo_xep_hang() -> BoXepHang:
    """Nạp lười theo bộ (model, tokenizer, biến thể, độ dài) đang cấu hình.

    Như ``embed.lay_bo_nhung``: lần ``/ready`` đầu tiên kích hoạt việc nạp; nạp hỏng thì ném lỗi và
    KHÔNG ghi nhớ — artifact mount muộn vẫn lên được mà không phải khởi động lại pod.
    """
    khoa = (
        str(_tim_tep(os.getenv("RERANK_MODEL_PATH", MODEL_MAC_DINH))),
        str(_tim_tep(os.getenv("RERANK_TOKENIZER_PATH", TOKENIZER_MAC_DINH))),
        os.getenv("RERANK_VARIANT", "int8"),
        int(os.getenv("RERANK_MAX_LENGTH", str(DO_DAI_MAC_DINH))),
    )
    with _KHOA_NAP:
        if khoa not in _BO_XEP_HANG:
            _BO_XEP_HANG[khoa] = BoXepHang(Path(khoa[0]), Path(khoa[1]), khoa[2], khoa[3])
            logger.info("Đã nạp cross-encoder %s (%s)", khoa[0], _BO_XEP_HANG[khoa].model_version)
        return _BO_XEP_HANG[khoa]


def check_invariants() -> tuple[bool, str]:
    """Bất biến 1 (model_id khớp EXPECTED_MODEL_ID) + model và tokenizer nạp được."""
    expected_id = os.getenv("EXPECTED_MODEL_ID")
    current_id = get_model_id()
    if expected_id and current_id != expected_id:
        return False, (
            f"BẤT BIẾN VI PHẠM: rerank model_id ({current_id!r}) khác EXPECTED_MODEL_ID ({expected_id!r})"
        )
    try:
        bo = lay_bo_xep_hang()
    except Exception as e:  # noqa: BLE001 — mọi lỗi nạp phải ra 503, không để /ready trả 500
        return False, f"CHƯA NẠP ĐƯỢC CROSS-ENCODER: {type(e).__name__}: {e}"
    return True, f"Rerank hợp lệ: {current_id} {bo.model_version}"


def _bo_xep_hang_hoac_503() -> BoXepHang:
    try:
        return lay_bo_xep_hang()
    except Exception as e:
        logger.error("Không nạp được cross-encoder: %s", e)
        raise HTTPException(status_code=503, detail="Cross-encoder chưa sẵn sàng") from e


# Hàm đồng bộ: FastAPI chạy trong threadpool nên suy luận không chặn vòng sự kiện.
@router.post("/v1/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest) -> dict[str, Any]:
    """Chấm điểm liên quan (câu hỏi, đoạn) bằng cross-encoder, trả về theo thứ tự giảm dần."""
    bo = _bo_xep_hang_hoac_503()
    logit = bo.cham(req.query, [c.text for c in req.candidates])
    # Hoà logit thì giữ thứ tự đầu vào (thứ hạng RRF) — cùng luật với ``xep_lai`` ở ai-service.
    thu_tu = sorted(range(len(logit)), key=lambda i: (-logit[i], i))
    return {
        "results": [
            {"chunk_id": req.candidates[i].chunk_id, "score": _sigmoid(logit[i]), "rank": hang}
            for hang, i in enumerate(thu_tu, 1)
        ],
        "model_id": get_model_id(),
        "model_version": bo.model_version,
    }


@router.get("/v1/model", response_model=ModelInfoResponse)
def model_info() -> dict[str, Any]:
    """Thông tin cross-encoder đang phục vụ — harness Ngày 15 kiểm danh tính ở đây."""
    try:
        bo = lay_bo_xep_hang()
        version, do_dai, trang_thai = bo.model_version, bo.do_dai, "READY"
    except Exception:  # noqa: BLE001 — chỉ là thông tin, lỗi thật đã báo ở /ready
        version, do_dai, trang_thai = None, DO_DAI_MAC_DINH, "NOT_READY"
    return {
        "model_id": get_model_id(),
        "model_version": version,
        "role": "rerank",
        "max_length": do_dai,
        "device": "CPU",
        "status": trang_thai,
    }
