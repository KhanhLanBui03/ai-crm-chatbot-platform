# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 07 — Export cross-encoder `BAAI/bge-reranker-v2-m3` sang ONNX rồi lượng tử hoá INT8 per-channel
#
# **[R&D]** — chạy trên Kaggle, **KHÔNG bật GPU** (cùng lý do notebook 06: export và quantize là
# tác vụ CPU). **Bật Internet** trong Settings — notebook tải model từ Hugging Face.
#
# Đầu ra: artifact cho `inference/ai-rerank`, phục vụ UC023 — Ngày 15 Khối A thay bản giả Jaccard.
#
# **Vì sao model này:** đa ngôn ngữ, dựng trên cùng xương sống với bge-m3 (XLM-RoBERTa-large,
# ~568 triệu tham số), kho và câu hỏi là tiếng Việt, có cả câu không dấu. `bge-reranker-base`
# mà `rerank.py` khai trước đây chỉ được huấn luyện cho tiếng Anh và tiếng Trung.
#
# **Khác notebook 06 ở ba chỗ — đều là chỗ dễ sai âm thầm:**
#
# 1. **Đầu vào là CẶP** (câu hỏi, đoạn) mã hoá chung MỘT chuỗi `<s> câu hỏi </s></s> đoạn </s>`,
#    không phải hai chuỗi nhúng riêng. Cross-encoder nhìn câu hỏi và đoạn cùng lúc — đó là lý do
#    nó chính xác hơn bi-encoder, và cũng là lý do nó không dùng được ở bước tìm.
# 2. **Đầu ra là MỘT logit mỗi cặp**, không phải vector. Rerank chỉ dùng điểm để SẮP XẾP.
# 3. **Cổng parity đo THỨ HẠNG, không đo cosine.** Lệch thang điểm không sao, đảo thứ tự mới hỏng.
#    Cổng (`artifacts/MODEL_REGISTRY.md`): nDCG@5 sau rerank của INT8 chênh fp32 **< 1 điểm**.
#    Báo kèm Spearman trung bình theo câu và độ trùng top-5.
#
# Bốn điều kiện tái lập (§5.8, `notebooks/README.md`): ghim seed · ghim phiên bản (cả revision của
# model) · ghi `sha256` của dữ liệu vào lẫn artifact ra · ghép cặp `.ipynb` ↔ `.py` bằng jupytext.

# %%
# --- 0. Phụ thuộc.
#
# Notebook 06 đo trên Kaggle (26/09/2026, ENVIRONMENT = "Pin to original environment"):
# torch · transformers · numpy · onnx · tokenizers ĐÃ CÓ SẴN;  onnxruntime  THIẾU.
#
# Chạy ô `import` ngay dưới TRƯỚC. Chỉ bỏ comment dòng này khi nó báo ModuleNotFoundError,
# và sửa cho khớp đúng gói mà nó kêu thiếu.
# !pip install -q "onnxruntime>=1.20"

# %%
import hashlib
import json
import random
import shutil
import time
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import tokenizers
import torch
import transformers
from huggingface_hub import hf_hub_download
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Điều kiện tái lập 1: ghim seed cho mọi nguồn ngẫu nhiên.
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# Điều kiện tái lập 2: ghim phiên bản, chép nguyên khối này vào Model Card.
PHIEN_BAN = {
    "torch": torch.__version__,
    "transformers": transformers.__version__,
    "tokenizers": tokenizers.__version__,
    "onnx": onnx.__version__,
    "onnxruntime": ort.__version__,
}
print(json.dumps(PHIEN_BAN, indent=2, ensure_ascii=False))

# %%
MODEL_ID = "BAAI/bge-reranker-v2-m3"
# Ghim commit, không ghim nhánh `main`: tác giả đẩy bản mới lên `main` là notebook ra model khác
# mà không báo gì. Lấy từ https://huggingface.co/api/models/BAAI/bge-reranker-v2-m3 ngày 11/10/2026
# (lastModified 24/06/2024).
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
OPSET = 17
# Cùng giá trị ở ba chỗ: lúc export, lúc đo parity dưới đây, và DO_DAI_TOI_DA của
# inference/src/roles/rerank.py. Mặc định của FlagReranker cũng là 512.
DO_DAI_TOI_DA = 512

TEN = "bge-reranker-v2-m3"
THU_MUC = Path("/kaggle/working")
DUONG_FP32 = THU_MUC / f"{TEN}-fp32.onnx"
DUONG_INT8 = THU_MUC / f"{TEN}-int8.onnx"
# Tên riêng, KHÔNG phải "tokenizer.json": artifacts/models/tokenizer.json đã là tokenizer của
# bge-m3 (ai-embed). Hai tokenizer trùng tên là chờ ngày một service nạp nhầm của service kia.
DUONG_TOKENIZER = THU_MUC / f"{TEN}-tokenizer.json"

# sha256 của ai-service/tests/eval/rerank_cap_100x20.jsonl đã commit — xuất bằng
# `python -m tests.eval.danh_gia_truy_hoi xuat-cap tests/eval/configs/e3_hybrid.yaml --ung-vien 20`.
SHA_TAP_CAP = "1f6c77adfcdf33b6390b3b42367411ef15b2120cb77f5f2a6989a20424163593"

# %% [markdown]
# ## 1. Nạp model, xác nhận **một** nhãn đầu ra bằng máy

# %%
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)

# attn_implementation="eager": cùng lý do notebook 06 — SDPA phải bị phân rã lúc export và graph
# ra khác nhau tuỳ phiên bản torch/transformers. Eager giống hệt về số học.
# Nếu transformers báo lỗi tham số lạ thì bỏ dòng đó, chạy lại, và GHI LẠI là đã bỏ.
mo_hinh = AutoModelForSequenceClassification.from_pretrained(
    MODEL_ID, revision=REVISION, attn_implementation="eager"
).eval()

print("kiến trúc:", mo_hinh.config.architectures, "· num_labels:", mo_hinh.config.num_labels)
assert mo_hinh.config.num_labels == 1, "Cross-encoder phải cho đúng MỘT logit mỗi cặp"

# %% [markdown]
# ## 2. Tokenizer cho production — lấy từ repo CỦA RERANKER, kiểm khớp từng token
#
# `inference/` không có `transformers` (cổng chặn image chỉ cho `onnxruntime · tokenizers · numpy`),
# nên lúc chạy nó mã hoá cặp bằng thư viện `tokenizers` trên tệp `tokenizer.json`. Ô này chép đúng
# tệp đó từ repo của reranker — **không** dùng lại `tokenizer.json` của bge-m3, dù cùng họ XLM-R:
# trùng hôm nay không có nghĩa là trùng ở revision sau.
#
# Hai thứ phải khớp HF từng token, nếu không thì điểm production khác điểm đo ở đây:
#
# - **Mẫu cặp:** `post_processor` của tệp phải tự chèn `<s> A </s></s> B </s>` khi gọi
#   `encode(câu_hỏi, đoạn)`.
# - **Cắt độ dài:** HF `truncation=True` với cặp dùng chiến lược `longest_first` (cắt bên dài hơn
#   trước). `enable_truncation` của `tokenizers` mặc định cũng vậy — nhưng mặc định là thứ đổi
#   được, nên kiểm bằng một đoạn dài hơn 512 token.

# %%
shutil.copyfile(hf_hub_download(MODEL_ID, "tokenizer.json", revision=REVISION), DUONG_TOKENIZER)

tok_prod = tokenizers.Tokenizer.from_file(str(DUONG_TOKENIZER))
tok_prod.enable_truncation(max_length=DO_DAI_TOI_DA)  # y hệt rerank.py
tok_prod.no_padding()  # lô 1 thì không có gì để pad


def ma_hoa_cap(cau_hoi: str, doan: str) -> np.ndarray:
    """Đúng cách ``rerank.py`` mã hoá: một cặp, lô 1, không pad."""
    return np.asarray([tok_prod.encode(cau_hoi, doan).ids], dtype=np.int64)


DOAN_DAI = "Chính sách bảo hành áp dụng cho sản phẩm còn tem nhãn và hoá đơn mua hàng. " * 60
cap_kiem = [
    ("ship bao lau v", "Giao hàng nội thành trong 24 giờ, ngoại thành 2–3 ngày."),
    ("Chính sách đổi trả hàng trong 7 ngày", "Khách được đổi trả trong vòng 7 ngày."),
    ("bảo hành máy lọc nước bao lâu", DOAN_DAI),
]
for q, p in cap_kiem:
    ids_hf = tokenizer(q, p, truncation=True, max_length=DO_DAI_TOI_DA)["input_ids"]
    ids_prod = tok_prod.encode(q, p).ids
    assert ids_hf == ids_prod, (
        f"Tokenizer production lệch HF ở cặp {q!r}: {len(ids_hf)} vs {len(ids_prod)} token"
    )
    print(f"khớp HF · {len(ids_prod):3d} token · {q!r}")

assert len(tok_prod.encode(*cap_kiem[2]).ids) == DO_DAI_TOI_DA, "Đoạn dài phải bị cắt đúng 512"
print("\nmẫu cặp:", tok_prod.encode(*cap_kiem[0]).tokens)

# %% [markdown]
# ## 3. Bọc lại: đầu ra là `logits[:, 0]` — một số thực mỗi cặp
#
# Kiểm ngữ nghĩa trước khi export, bằng một phép so mà ai cũng chấm tay được: với cùng câu hỏi,
# đoạn đúng phải được điểm cao hơn đoạn lạc đề. Export một model trả điểm ngược thì mọi bước sau
# vẫn chạy trơn tru.

# %%
class CrossEncoderLogit(torch.nn.Module):
    """Chỉ lấy logit duy nhất của đầu phân loại — hình dạng ``(batch,)``."""

    def __init__(self, mo_hinh: torch.nn.Module) -> None:
        super().__init__()
        self.mo_hinh = mo_hinh

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        return self.mo_hinh(input_ids=input_ids, attention_mask=attention_mask).logits[:, 0]


bo_cham = CrossEncoderLogit(mo_hinh).eval()

CAU_HOI = "máy lọc nước bao lâu thì phải thay lõi"
mau = tokenizer(
    [CAU_HOI, CAU_HOI],
    [
        "Lõi PP 5 micron cần thay sau 3 tháng sử dụng để nước đạt chất lượng.",
        "Cửa hàng mở cửa từ 8 giờ sáng đến 21 giờ tối, kể cả cuối tuần.",
    ],
    return_tensors="pt",
    padding=True,
    truncation=True,
    max_length=DO_DAI_TOI_DA,
)
with torch.no_grad():
    logit_thu = bo_cham(mau["input_ids"], mau["attention_mask"])

print("shape:", tuple(logit_thu.shape), "· logit (đúng, lạc đề):", logit_thu.tolist())
assert logit_thu.shape == (2,), "Phải là MỘT logit mỗi cặp"
assert logit_thu[0] > logit_thu[1], "Đoạn đúng phải có điểm cao hơn đoạn lạc đề"

# %% [markdown]
# ## 4. Export ONNX fp32 rồi gom trọng số về một file
#
# Cùng cỡ bge-m3 (~568M tham số ⇒ fp32 ~2,2 GB, vượt giới hạn 2 GB của protobuf) nên bộ export tự
# rải trọng số ra hàng trăm file đặt tên theo tensor. Gom về đúng hai: `.onnx` + `.data`.
# Thứ tự cố ý: **gom → kiểm chạy được → mới xoá**, và chỉ xoá file DO EXPORT sinh ra.

# %%
co_san_truoc_export = {f.name for f in THU_MUC.iterdir()}

torch.onnx.export(
    bo_cham,
    (mau["input_ids"], mau["attention_mask"]),
    str(DUONG_FP32),
    input_names=["input_ids", "attention_mask"],
    output_names=["logit"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "logit": {0: "batch"},
    },
    opset_version=OPSET,
    do_constant_folding=True,
    # Ghi RÕ dynamo=False — mặc định đổi giữa các bản torch, và bộ dynamo cần onnxscript mà môi
    # trường ghim của Kaggle không có (đo thật ở notebook 06, torch 2.10).
    dynamo=False,
)

m = onnx.load(str(DUONG_FP32), load_external_data=True)
onnx.save_model(
    m,
    str(DUONG_FP32),
    save_as_external_data=True,
    all_tensors_to_one_file=True,
    location=f"{TEN}-fp32.data",
    size_threshold=1024,
)
del m

sess_fp32 = ort.InferenceSession(str(DUONG_FP32), providers=["CPUExecutionProvider"])
thu = sess_fp32.run(
    ["logit"],
    {"input_ids": mau["input_ids"].numpy(), "attention_mask": mau["attention_mask"].numpy()},
)[0]
assert thu.shape == (2,), f"File gom lại hỏng: shape {thu.shape}"
print("file gom lại chạy được, shape", thu.shape)

GIU = {DUONG_FP32.name, f"{TEN}-fp32.data", DUONG_TOKENIZER.name}
xoa = [
    f for f in THU_MUC.iterdir()
    if f.is_file() and f.name not in GIU and f.name not in co_san_truoc_export
]
for f in xoa:
    f.unlink()
print("đã xoá", len(xoa), "file rời rạc")

# %% [markdown]
# ### Graph có tổng quát hoá được sang kích thước khác không?
#
# Lúc export sẽ có `TracerWarning` ở `masking_utils.py` như notebook 06: một nhánh `if` mức Python
# bị đóng băng theo kích thước lúc trace. Không suy luận được từ code — **phải đo**: chạy PyTorch và
# ONNX fp32 trên lô có batch lẫn độ dài khác hẳn lúc export, và trên **lô 1 không pad** — đúng
# cách production chạy.
#
# Dung sai 1e-3 trên logit (không phải 1e-4 như vector đã chuẩn hoá của notebook 06): logit không
# bị chặn trong [−1, 1], cỡ vài đơn vị, sai số float32 cộng dồn qua 24 tầng tỉ lệ theo độ lớn đó.
# So ở đây là fp32 vs fp32 — lệch thì lỗi nằm ở export, không phải ở INT8.

# %%
def mo_session(duong_dan: Path) -> ort.InferenceSession:
    """Nạp MỘT LẦN rồi dùng lại — mỗi lần tạo session là đọc lại toàn bộ trọng số."""
    return ort.InferenceSession(str(duong_dan), providers=["CPUExecutionProvider"])


def cham_mot_cap(sess: ort.InferenceSession, ids: np.ndarray) -> float:
    """Logit của một cặp đã mã hoá bằng ``ma_hoa_cap`` — lô 1, mask toàn 1."""
    (ra,) = sess.run(["logit"], {"input_ids": ids, "attention_mask": np.ones_like(ids)})
    return float(ra[0])


q_kiem = ["Ngan", "Cong ty co ho tro xuat hoa don VAT khong", "ship bao lau v",
          "bảo hành máy lọc nước bao lâu",
          "trả góp qua thẻ tín dụng khác công ty tài chính chỗ nào"]
p_kiem = ["Ngắn.", "Công ty xuất hoá đơn GTGT theo yêu cầu trong vòng 24 giờ.",
          "Giao hàng nội thành trong 24 giờ.", DOAN_DAI,
          "Tiêu chí | Qua thẻ tín dụng | Qua công ty tài chính"]
enc_kiem = tokenizer(q_kiem, p_kiem, return_tensors="pt", padding=True, truncation=True,
                     max_length=DO_DAI_TOI_DA)
print("batch×seq lúc export:", tuple(mau["input_ids"].shape))
print("batch×seq lúc kiểm :", tuple(enc_kiem["input_ids"].shape), "← phải KHÁC dòng trên")

with torch.no_grad():
    l_torch = bo_cham(enc_kiem["input_ids"], enc_kiem["attention_mask"]).numpy()
l_onnx = sess_fp32.run(["logit"], {"input_ids": enc_kiem["input_ids"].numpy(),
                                   "attention_mask": enc_kiem["attention_mask"].numpy()})[0]
l_lo1 = np.array(
    [cham_mot_cap(sess_fp32, ma_hoa_cap(q, p)) for q, p in zip(q_kiem, p_kiem, strict=True)]
)

lech_lo = float(np.abs(l_torch - l_onnx).max())
lech_lo1 = float(np.abs(l_torch - l_lo1).max())
print("logit PyTorch:", np.round(l_torch, 4).tolist())
print(f"lệch lớn nhất PyTorch vs ONNX fp32 — cùng lô: {lech_lo:.2e} · "
      f"lô 1 không pad: {lech_lo1:.2e}")
assert lech_lo < 1e-3 and lech_lo1 < 1e-3, (
    "Graph KHÔNG tổng quát hoá được — nhánh if bị đóng băng lúc trace. Đừng đi tiếp."
)
print("→ graph tổng quát hoá được, đi tiếp được")

# %% [markdown]
# ## 5. Lượng tử hoá INT8 động, per-channel — y hệt notebook 06
#
# Động (không cần tập hiệu chuẩn) · per-channel (một cột có outlier không kéo giãn thang của cả ma
# trận) · QInt8. Bảng nhúng từ vựng là phép `Gather` nên giữ fp32 ⇒ thu gọn cỡ 1,5–2 lần chứ không
# phải 4 lần — báo cáo trung thực con số đó.

# %%
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402


def file_du_lieu(duong_dan: Path) -> list[Path]:
    """File external data đi kèm một .onnx — hai kiểu tên (xem notebook 06):
    ``onnx.save_model(location=...)`` → ``x-fp32.data``;
    ``quantize_dynamic`` → ``x-int8.onnx.data``.
    """
    ung_vien = [duong_dan.with_suffix(".data"), Path(str(duong_dan) + ".data")]
    return [p for p in ung_vien if p.exists()]


def kich_thuoc_that(duong_dan: Path) -> int:
    """Cỡ THẬT của model, tính cả external data — ``.onnx`` một mình chỉ là graph."""
    return duong_dan.stat().st_size + sum(p.stat().st_size for p in file_du_lieu(duong_dan))


quantize_dynamic(
    model_input=str(DUONG_FP32),
    model_output=str(DUONG_INT8),
    weight_type=QuantType.QInt8,
    per_channel=True,
    use_external_data_format=True,
)

kich_thuoc = {
    "fp32_GB": round(kich_thuoc_that(DUONG_FP32) / 1024**3, 3),
    "int8_GB": round(kich_thuoc_that(DUONG_INT8) / 1024**3, 3),
}
kich_thuoc["ti_le_thu_gon"] = round(kich_thuoc["fp32_GB"] / kich_thuoc["int8_GB"], 2)
print(json.dumps(kich_thuoc, indent=2, ensure_ascii=False))

sess_int8 = mo_session(DUONG_INT8)
print("kiểm khói INT8 (đúng, lạc đề):",
      [round(cham_mot_cap(sess_int8, ma_hoa_cap(CAU_HOI, p)), 4)
       for p in ["Lõi PP 5 micron cần thay sau 3 tháng sử dụng để nước đạt chất lượng.",
                 "Cửa hàng mở cửa từ 8 giờ sáng đến 21 giờ tối, kể cả cuối tuần."]])

for f in sorted(THU_MUC.iterdir()):
    if f.is_file():
        print(f"{f.stat().st_size / 1024**2:10.2f} MB  {f.name}")

# %% [markdown]
# ## 6. `sha256` của artifact — điều kiện tái lập 3
#
# Hash **cả `.data`**, không chỉ `.onnx` (graph chỉ vài MB, trọng số nằm ở `.data`), và hash cả
# tokenizer: nó quyết định chuỗi token, tức quyết định điểm.

# %%
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def sha256_model(duong_dan: Path) -> dict[str, str]:
    kq = {duong_dan.name: sha256_file(duong_dan)}
    for p in file_du_lieu(duong_dan):
        kq[p.name] = sha256_file(p)
    return kq


so_dang_ky = {
    "model_id": MODEL_ID,
    "revision": REVISION,
    "dau_ra": "logit (batch,) — logits[:, 0] cua XLMRobertaForSequenceClassification",
    "max_length": DO_DAI_TOI_DA,
    "opset": OPSET,
    "exporter": "TorchScript (dynamo=False)",
    "attention": "eager",
    "luong_tu_hoa": "dynamic INT8, per-channel, QInt8",
    "sha256_fp32": sha256_model(DUONG_FP32),
    "sha256_int8": sha256_model(DUONG_INT8),
    "sha256_tokenizer": {DUONG_TOKENIZER.name: sha256_file(DUONG_TOKENIZER)},
    **kich_thuoc,
    "phien_ban": PHIEN_BAN,
}
print(json.dumps(so_dang_ky, indent=2, ensure_ascii=False))

# %% [markdown]
# ---
# ## 7. CỔNG PARITY — đo THỨ HẠNG trên cặp thật
#
# **Tập đo:** `rerank_cap_100x20.jsonl` — 100 câu có đáp án của bộ vàng × 20 ứng viên đầu của
# hybrid RRF (đúng thứ tự cấu hình ship `e3-hybrid`), mỗi ứng viên kèm nhãn `dung`. Chữ của đoạn
# là `content` trong kho đo — chỉ có chữ của `data/kb_samples`, không có PII.
# Đưa tệp lên bằng `+ Add Input → Upload`; ô dưới tự tìm, không ghi cứng đường dẫn có tên tài khoản.
#
# **Cách chấm — y hệt production:** mỗi cặp một lượt (lô 1, không pad), mã hoá bằng `tok_prod`.
# Lô 1 không phải tuỳ chọn: `DynamicQuantizeLinear` tính thang trên CẢ tensor, ghép lô thì điểm
# của một cặp phụ thuộc cặp đi cùng — đo theo lô là đo một thứ production không chạy.
#
# **Ba con số, cổng nằm ở con số thứ ba:**
#
# 1. **Spearman** giữa điểm fp32 và INT8 trên 20 ứng viên, trung bình theo câu (kèm `min`) — thứ
#    hạng toàn cục giữ được bao nhiêu.
# 2. **Độ trùng top-5** — năm đoạn sẽ vào lời nhắc có giữ nguyên không.
# 3. **nDCG@5 sau rerank, INT8 so với fp32, chênh < 1 điểm** — cổng của `MODEL_REGISTRY.md`. Định
#    nghĩa giống hệt harness (`danh_gia_truy_hoi.py`): `1/log2(1 + hạng đoạn đúng đầu tiên)`,
#    IDCG = 1, câu không có đoạn đúng trong top-5 tính 0. Đo cho cả N = 12 và N = 20 ứng viên;
#    phải đạt cả hai.
#
# Không `assert` ở cổng — cùng lý do notebook 06: lượt `Save & Run All (Commit)` là bản DUY NHẤT
# lưu được bằng chứng, kể cả khi trượt. Trượt thì **không hạ ngưỡng**: người dùng quyết ship fp32
# hay loại model (ADR-0021).

# %%
_tim = sorted(Path("/kaggle/input").rglob("rerank_cap_100x20.jsonl"))
assert _tim, "Chưa gắn dataset chứa rerank_cap_100x20.jsonl — bấm '+ Add Input'"
DUONG_CAP = _tim[0]
sha_cap = sha256_file(DUONG_CAP)
print("dùng file:", DUONG_CAP, "\nsha256:", sha_cap)
assert sha_cap == SHA_TAP_CAP, (
    "Tệp cặp khác bản đã commit — con số parity sẽ không gắn được vào tệp nào"
)

cac_cau = [json.loads(d) for d in DUONG_CAP.read_text(encoding="utf-8").splitlines() if d.strip()]
so_cap = sum(len(c["ung_vien"]) for c in cac_cau)
print(f"{len(cac_cau)} câu · {so_cap} cặp · "
      f"có đoạn đúng trong 20 ứng viên: {sum(1 for c in cac_cau if c['hang_dung_rrf'])} câu · "
      f"mơ hồ theo cổng production: {sum(1 for c in cac_cau if c['mo_ho'])} câu")

# Biết trước bao nhiêu cặp bị cắt ở 512 — đừng để im lặng.
_do_dai = [
    len(tok_prod.encode(c["question"], u["text"]).ids) for c in cac_cau for u in c["ung_vien"]
]
_khong_cat = tokenizers.Tokenizer.from_file(str(DUONG_TOKENIZER))
_khong_cat.no_truncation()
_bi_cat = sum(
    1 for c in cac_cau for u in c["ung_vien"]
    if len(_khong_cat.encode(c["question"], u["text"]).ids) > DO_DAI_TOI_DA
)
print(f"độ dài cặp (token): min {min(_do_dai)} · p50 {int(np.median(_do_dai))} · "
      f"max {max(_do_dai)} "
      f"· bị cắt ở {DO_DAI_TOI_DA}: {_bi_cat}/{so_cap}")

# %%
# Chấm 2000 cặp × 2 model, lô 1. Ước lượng trên Kaggle CPU: 15–30 phút — in tiến độ mỗi 10 câu.
diem = {"fp32": [], "int8": []}
giay = {"fp32": 0.0, "int8": 0.0}
for i, c in enumerate(cac_cau):
    cac_ids = [ma_hoa_cap(c["question"], u["text"]) for u in c["ung_vien"]]
    for ten, sess in (("fp32", sess_fp32), ("int8", sess_int8)):
        t = time.perf_counter()
        diem[ten].append(np.array([cham_mot_cap(sess, ids) for ids in cac_ids]))
        giay[ten] += time.perf_counter() - t
    if (i + 1) % 10 == 0:
        print(f"[{i + 1}/{len(cac_cau)}] fp32 {giay['fp32']:.0f}s · int8 {giay['int8']:.0f}s")

# %%
def hang_cua(x: np.ndarray) -> np.ndarray:
    r = np.empty(len(x))
    r[np.argsort(x, kind="stable")] = np.arange(len(x))
    return r


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(hang_cua(a), hang_cua(b))[0, 1])


def thu_tu_sau_rerank(d: np.ndarray, n: int) -> np.ndarray:
    """Chỉ số ứng viên theo thứ tự sau khi xếp lại ``n`` đoạn đầu; phần sau ``n`` giữ thứ tự RRF.
    Sắp ổn định theo điểm giảm dần — cùng luật hoà điểm với ``xep_lai`` của ai-service."""
    dau = np.argsort(-d[:n], kind="stable")
    return np.concatenate([dau, np.arange(n, len(d))])


def ndcg5(thu_tu: np.ndarray, nhan: list[bool]) -> float:
    for hang, j in enumerate(thu_tu[:5], 1):
        if nhan[j]:
            return 1 / np.log2(1 + hang)
    return 0.0


nhan = [[u["dung"] for u in c["ung_vien"]] for c in cac_cau]
mo_ho = [c["mo_ho"] for c in cac_cau]
rrf = np.arange(20)

sp = np.array([spearman(a, b) for a, b in zip(diem["fp32"], diem["int8"], strict=True)])
trung5 = np.array([
    len(set(np.argsort(-a)[:5]) & set(np.argsort(-b)[:5])) / 5
    for a, b in zip(diem["fp32"], diem["int8"], strict=True)
])

bang = {"khong_rerank": {"ndcg5": float(np.mean([ndcg5(rrf, y) for y in nhan])),
                         "recall5": float(np.mean([ndcg5(rrf, y) > 0 for y in nhan]))}}
for n in (12, 20):
    for ten in ("fp32", "int8"):
        tt = [thu_tu_sau_rerank(d, n) for d in diem[ten]]
        bang[f"{ten}_N{n}"] = {
            "ndcg5": float(np.mean([ndcg5(t, y) for t, y in zip(tt, nhan, strict=True)])),
            "recall5": float(np.mean([ndcg5(t, y) > 0 for t, y in zip(tt, nhan, strict=True)])),
        }
    # Bản xem trước của cấu hình "chỉ khi mơ hồ" — harness Ngày 15 đo lại trên ai-rerank thật.
    tt = [thu_tu_sau_rerank(d, n) if m else rrf for d, m in zip(diem["int8"], mo_ho, strict=True)]
    bang[f"int8_N{n}_mo_ho"] = {
        "ndcg5": float(np.mean([ndcg5(t, y) for t, y in zip(tt, nhan, strict=True)])),
        "recall5": float(np.mean([ndcg5(t, y) > 0 for t, y in zip(tt, nhan, strict=True)])),
    }

print(f"Spearman fp32↔INT8 theo câu: mean {sp.mean():.5f} · min {sp.min():.5f}")
print(f"Độ trùng top-5 fp32↔INT8   : mean {trung5.mean():.3f} · min {trung5.min():.2f} · "
      f"câu trùng đủ 5/5: {int((trung5 == 1).sum())}/{len(trung5)}\n")
print(f"{'cấu hình':22s} {'nDCG@5':>8s} {'recall@5':>9s}")
for k, v in bang.items():
    print(f"{k:22s} {v['ndcg5']:8.4f} {v['recall5']:9.3f}")

chenh = {n: (bang[f"int8_N{n}"]["ndcg5"] - bang[f"fp32_N{n}"]["ndcg5"]) * 100 for n in (12, 20)}
CONG_PARITY_DAT = all(abs(x) < 1.0 for x in chenh.values())
print("\nchênh nDCG@5 INT8 − fp32 (điểm %):", {f"N={n}": round(x, 2) for n, x in chenh.items()})
if CONG_PARITY_DAT:
    print("CỔNG PARITY XANH — ship INT8.")
else:
    print("[TRƯỢT] Cổng parity: chênh ≥ 1 điểm. KHÔNG hạ ngưỡng — người dùng quyết ship fp32 hay "
          "loại model (ADR-0021).")

# %% [markdown]
# ### Tổng kết vào sổ đăng ký

# %%
# Độ trễ TUYỆT ĐỐI trên Kaggle KHÔNG tái lập (notebook 06: chênh 1,6 lần giữa hai lượt). Chỉ tỉ lệ
# fp32/INT8 dùng được. p95 nghiệm thu đo bằng harness trên ai-rerank ở máy dev.
ms_moi_cap = {ten: round(giay[ten] / so_cap * 1000, 1) for ten in giay}
print("ms trung bình mỗi cặp (lô 1):", ms_moi_cap)

so_dang_ky["parity"] = {
    "cong": "nDCG@5 sau rerank INT8 vs fp32 chenh < 1 diem, ca N=12 va N=20",
    "dat": CONG_PARITY_DAT,
    "chenh_ndcg5_diem": {f"N{n}": round(x, 3) for n, x in chenh.items()},
    "spearman_theo_cau": {"mean": round(float(sp.mean()), 5), "min": round(float(sp.min()), 5)},
    "trung_top5": {"mean": round(float(trung5.mean()), 4), "min": round(float(trung5.min()), 2)},
    "bang": {k: {m: round(x, 4) for m, x in v.items()} for k, v in bang.items()},
    "tap_do": {"so_cau": len(cac_cau), "so_cap": so_cap, "sha256": sha_cap,
               "bi_cat_512": _bi_cat},
}
so_dang_ky["ms_moi_cap_kaggle"] = {**ms_moi_cap, "may": "Kaggle CPU — KHONG tai lap duoc"}
print(json.dumps(so_dang_ky, indent=2, ensure_ascii=False))

# %% [markdown]
# ## 8. Sau khi chạy xong
#
# 1. Tải về `artifacts/models/` (Kaggle: Output → Download) đúng **ba** file:
#    `bge-reranker-v2-m3-int8.onnx` · `bge-reranker-v2-m3-int8.onnx.data` ·
#    `bge-reranker-v2-m3-tokenizer.json`. Bản fp32 chỉ tải nếu cổng parity trượt.
# 2. Chép khối `so_dang_ky` in ở ô trên vào phiên làm việc — dòng `MODEL_REGISTRY.md` và Model Card
#    lấy số từ đó.
# 3. Ghép cặp lại: `jupytext --set-formats ipynb,py:percent 07_export_reranker.ipynb`,
#    commit cả hai.
