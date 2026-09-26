# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 06 — Export encoder `BAAI/bge-m3` sang ONNX rồi lượng tử hoá INT8 per-channel
#
# **[R&D]** — chạy trên Kaggle, **KHÔNG bật GPU**. Export và quantize là tác vụ CPU;
# bật GPU chỉ làm chậm hàng đợi (`notebooks/README.md`).
#
# Đầu ra: hai artifact `.onnx` cho `inference/ai-embed`, phục vụ UC019 và UC023.
#
# **Ràng buộc cứng — số chiều phải đúng 1024.** Cột `knowledge.knowledge_chunks.embedding`
# khai `vector(1024)` ở V203 dòng 17. Đổi model ra số chiều khác là đổi DDL, tức đổi
# migration đã chạy — không phải việc sửa một dòng config.
#
# Bốn điều kiện tái lập (§5.8, `notebooks/README.md`): ghim seed · ghim phiên bản ·
# ghi `sha256` artifact · ghép cặp `.ipynb` ↔ `.py` bằng jupytext.
#
# 🚫 **Cổng chặn ở cuối notebook:** `cosine(fp32, int8) ≥ 0,995` trên 500 mẫu. Không đạt
# thì **đổi model**, không đi tiếp. Lượng tử hoá hỏng thì hỏng *âm thầm* — vector vẫn đủ
# 1024 chiều, vẫn trông hợp lệ, chỉ là sai.

# %%
# --- 0. Phụ thuộc.
#
# Đo thật trên Kaggle (26/09/2026, ENVIRONMENT = "Pin to original environment"):
# torch · transformers · numpy · onnx  ĐÃ CÓ SẴN;  onnxruntime  THIẾU.
#
# Nên chỉ cài đúng gói thiếu. Cài đè cả "onnx" lên bản đang có là tự chuốc rủi ro lệch
# phiên bản trong một môi trường cố tình ghim — mà ghim chính là điều kiện tái lập 2.
#
# Chạy ô `import` ngay dưới TRƯỚC. Chỉ bỏ comment dòng này khi nó báo ModuleNotFoundError,
# và sửa cho khớp đúng gói mà nó kêu thiếu.
# !pip install -q "onnxruntime>=1.20"

# %%
import collections
import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import transformers
from transformers import AutoModel, AutoTokenizer

# Điều kiện tái lập 1: ghim seed cho mọi nguồn ngẫu nhiên.
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# Điều kiện tái lập 2: ghim phiên bản, chép nguyên khối này vào Model Card.
PHIEN_BAN = {
    "torch": torch.__version__,
    "transformers": transformers.__version__,
    "onnx": onnx.__version__,
    "onnxruntime": ort.__version__,
}
print(json.dumps(PHIEN_BAN, indent=2, ensure_ascii=False))

# %%
MODEL_ID = "BAAI/bge-m3"
SO_CHIEU_BAT_BUOC = 1024  # V203:17 — vector(1024). Không thương lượng.
OPSET = 17

THU_MUC = Path("/kaggle/working")
DUONG_FP32 = THU_MUC / "bge-m3-fp32.onnx"
DUONG_INT8 = THU_MUC / "bge-m3-int8.onnx"

# %% [markdown]
# ## 1. Nạp model và xác nhận số chiều **bằng máy**
#
# `config.py:61-62` đang khai `BAAI/bge-m3` + `embedding_dim = 1024`. Đọc bằng mắt thấy
# khớp là chưa đủ — dưới đây kiểm bằng một lượt forward thật.

# %%
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# attn_implementation="eager": ép attention thuần thay vì SDPA.
#
# transformers mặc định dùng SDPA — nhanh hơn khi chạy PyTorch, nhưng lúc export ONNX nó
# phải bị phân rã, và graph ra khác nhau tuỳ phiên bản torch/transformers. Đây là nguồn lỗi
# export phổ biến nhất của họ BERT/RoBERTa. Bản eager cho kết quả GIỐNG HỆT về số học,
# chỉ chậm hơn ở đúng notebook này — mà đây là việc chạy một lần, không phải đường request.
#
# Nếu transformers báo lỗi tham số lạ thì bỏ dòng attn_implementation đi và chạy lại;
# ghi lại là đã bỏ, vì nó đổi graph được export.
backbone = AutoModel.from_pretrained(MODEL_ID, attn_implementation="eager").eval()

print("hidden_size khai trong config:", backbone.config.hidden_size)
assert backbone.config.hidden_size == SO_CHIEU_BAT_BUOC, (
    f"Model cho {backbone.config.hidden_size} chiều, cột CSDL là {SO_CHIEU_BAT_BUOC}. "
    "Đổi model hoặc đổi DDL — không có đường thứ ba."
)


# %% [markdown]
# ## 2. Bọc lại: vector dense của bge-m3 = token CLS, chuẩn hoá L2
#
# ⚠️ **`inference/ai-embed` phải làm ĐÚNG phép này.** Lệch một bước — ví dụ mean pooling
# thay vì CLS, hoặc quên chuẩn hoá — thì vector vẫn đủ 1024 chiều, vẫn ghi vào CSDL được,
# vẫn tính được cosine. Chỉ là Recall@5 tụt mà **không có exception nào** báo.
#
# Chuẩn hoá L2 ngay trong graph, không để tầng ứng dụng tự làm: một phép toán nằm ở một
# chỗ thì không có cơ hội lệch giữa lúc nạp tài liệu và lúc truy vấn.

# %%
class BgeM3Dense(torch.nn.Module):
    """Chỉ lấy nhánh dense của bge-m3. Bỏ nhánh sparse và ColBERT — RAG này không dùng."""

    def __init__(self, backbone: torch.nn.Module) -> None:
        super().__init__()
        self.backbone = backbone

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0]  # token đầu tiên, KHÔNG phải mean pooling
        return torch.nn.functional.normalize(cls, p=2, dim=-1)


encoder = BgeM3Dense(backbone).eval()

# Kiểm bằng một lượt chạy thật, có dấu tiếng Việt.
mau = tokenizer(
    ["Chinh sach doi tra hang trong 7 ngay", "Chính sách đổi trả hàng trong 7 ngày"],
    return_tensors="pt",
    padding=True,
    truncation=True,
    max_length=512,
)
with torch.no_grad():
    v_thu = encoder(mau["input_ids"], mau["attention_mask"])

print("shape thật:", tuple(v_thu.shape))
print("chuẩn L2 (phải ≈ 1):", v_thu.norm(dim=-1).tolist())
assert v_thu.shape[-1] == SO_CHIEU_BAT_BUOC, "Forward thật cho sai số chiều"

# %% [markdown]
# ## 3. Export ONNX fp32
#
# `dynamic_axes` cho cả `batch` lẫn `seq`: kích thước lô và độ dài câu thay đổi theo từng
# request thật. Cố định chúng lúc export là ép tầng suy luận phải pad về đúng một độ dài,
# vừa chậm vừa sai ngữ nghĩa.
#
# ⚠️ **bge-m3 ~568M tham số ⇒ fp32 khoảng 2,2 GB, vượt giới hạn 2 GB của protobuf.** torch
# 2.x tự chuyển sang external data khi vượt; nếu bản torch trên Kaggle báo lỗi
# *"exceed maximum protobuf size"* thì chạy ô dự phòng ngay dưới.

# %%
torch.onnx.export(
    encoder,
    (mau["input_ids"], mau["attention_mask"]),
    str(DUONG_FP32),
    input_names=["input_ids", "attention_mask"],
    output_names=["embedding"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "embedding": {0: "batch"},
    },
    opset_version=OPSET,
    do_constant_folding=True,
    # Ghi RÕ dynamo=False, đừng dựa vào mặc định — mặc định đổi giữa các bản torch.
    # Đo thật: torch 2.10.0 mặc định dynamo=True, và bộ export dynamo cần gói onnxscript
    # mà môi trường ghim của Kaggle không có ⇒ ModuleNotFoundError ngay tại đây.
    #
    # Chọn bộ TorchScript vì `dynamic_axes` là tham số CỦA NÓ; bộ dynamo dùng
    # `dynamic_shapes`, truyền dynamic_axes vào đó thì phải qua một lớp quy đổi nữa.
    # Bộ cũ cũng là thứ quantize_dynamic của onnxruntime được kiểm nhiều nhất.
    # Đánh đổi: bộ TorchScript đã deprecated, sẽ in DeprecationWarning — chấp nhận.
    #
    # Nếu một bản torch sau này bỏ hẳn bộ cũ: `!pip install -q onnxscript`, bỏ dòng này,
    # rồi đổi dynamic_axes sang dynamic_shapes và ĐO LẠI PARITY từ đầu.
    dynamo=False,
)
print("fp32:", DUONG_FP32, f"{DUONG_FP32.stat().st_size / 1024**3:.2f} GB")

# %% [markdown]
# ### Gom trọng số về một file
#
# ĐO THẬT (torch 2.10, bge-m3): sau export, `/kaggle/working` có **172 file, tổng 2,11 GB**.
# `bge-m3-fp32.onnx` chỉ 1,33 MB vì nó **chỉ chứa graph** — 2,11 GB trọng số bị rải ra 171
# file đặt tên theo tensor (`backbone.embeddings.word_embeddings.weight`, `onnx__MatMul_2872`…).
# Đó là hành vi bình thường: model 2,27 GB vượt giới hạn 2 GB của protobuf nên bộ export tự
# chuyển sang external data.
#
# Export **không hỏng** — kiểm bằng số: `word_embeddings` 976,57 MB = 250 002 × 1024 × 4 byte,
# `position_embeddings` 32,01 MB = 8194 × 1024 × 4, và có đủ `layer.0` → `layer.23`.
#
# Nhưng 172 file thì không tải từ Kaggle về nổi, mà thiếu một file là `.onnx` thành cái vỏ.
# Gom về đúng hai: `.onnx` (graph) + `.data` (toàn bộ trọng số).
#
# Thứ tự dưới đây là cố ý: **gom → kiểm chạy được → mới xoá**. Xoá trước rồi mới phát hiện
# file gom hỏng thì phải export lại từ đầu, mà đó là bước tốn thời gian nhất notebook này.

# %%
GIU = {"bge-m3-fp32.onnx", "bge-m3-fp32.data"}

m = onnx.load(str(DUONG_FP32), load_external_data=True)  # nạp ~2,1 GB vào RAM
onnx.save_model(
    m,
    str(DUONG_FP32),
    save_as_external_data=True,
    all_tensors_to_one_file=True,
    location="bge-m3-fp32.data",
    size_threshold=1024,  # tensor nhỏ hơn 1 KB thì để luôn trong .onnx
)
del m

sess_fp32 = ort.InferenceSession(str(DUONG_FP32), providers=["CPUExecutionProvider"])
thu = sess_fp32.run(
    ["embedding"],
    {"input_ids": mau["input_ids"].numpy(), "attention_mask": mau["attention_mask"].numpy()},
)[0]
assert thu.shape == (2, SO_CHIEU_BAT_BUOC), f"File gom lại hỏng: shape {thu.shape}"
print("file gom lại chạy được, shape", thu.shape)

xoa = sum(1 for f in THU_MUC.iterdir() if f.is_file() and f.name not in GIU)
for f in THU_MUC.iterdir():
    if f.is_file() and f.name not in GIU:
        f.unlink()
print("đã xoá", xoa, "file rời rạc")

# %%
# Bố cục file sau export.
#
# ĐO THẬT (torch 2.10, bge-m3): .onnx in ra 0.00 GB — KHÔNG phải export hỏng. Model 2,27 GB
# vượt giới hạn 2 GB của protobuf nên bộ export tự tách trọng số ra external data, và nó
# đặt tên các file đó theo TÊN TENSOR (backbone.embeddings...weight), không theo tên model.
# Vì vậy phải liệt kê cả thư mục chứ không glob theo tiền tố.
#
# Thiếu mấy file trọng số này thì .onnx chỉ là cái vỏ — tải về sẽ không chạy được.
tong = 0
for f in sorted(THU_MUC.iterdir()):
    if f.is_file():
        tong += f.stat().st_size
        print(f"{f.stat().st_size / 1024**2:10.2f} MB  {f.name}")
print(f"\nTổng: {tong / 1024**3:.2f} GB · {sum(1 for f in THU_MUC.iterdir() if f.is_file())} file")

# %%
# Cố ý KHÔNG gọi onnx.checker.check_model ở đây.
#
# Ô gom trọng số phía trên đã mở được InferenceSession và chạy ra đúng (2, 1024) — đó là
# bằng chứng MẠNH HƠN checker: checker chỉ nói graph đúng cú pháp, còn ORT nạp được và
# chạy ra kết quả thì đã bao hàm điều đó. Chạy thêm checker trên model 2,16 GB external
# data tốn vài phút và 2 GB RAM cho một câu trả lời yếu hơn.
def mo_session(duong_dan: Path) -> ort.InferenceSession:
    """Nạp model MỘT LẦN rồi dùng lại.

    ⚠️ Tách khỏi ``chay_onnx`` có chủ đích: mỗi lần tạo InferenceSession là đọc lại toàn bộ
    trọng số (2,27 GB với bản fp32). Gọi nó trong vòng lặp 500 câu ở bước 7 thì notebook
    chạy hàng chục phút cho một việc đáng ra mất vài phút.
    """
    return ort.InferenceSession(str(duong_dan), providers=["CPUExecutionProvider"])


def chay_onnx(sess: ort.InferenceSession, enc: dict) -> np.ndarray:
    """Chạy một lô đã tokenize. ``enc`` là output của tokenizer, còn ở dạng torch tensor."""
    return sess.run(
        ["embedding"],
        {
            "input_ids": enc["input_ids"].numpy(),
            "attention_mask": enc["attention_mask"].numpy(),
        },
    )[0]


# %% [markdown]
# ### Graph có tổng quát hoá được sang kích thước khác không?
#
# 🔴 Ô này bắt buộc, vì lúc export có cảnh báo:
#
# > `TracerWarning: Converting a tensor to a Python boolean` — `masking_utils.py:171`
#
# Dòng bị cảnh báo là một nhánh `if` ở **mức Python** bên trong `transformers`. Trace chỉ
# chạy model đúng một lần với mẫu 2 câu, nên nhánh đó được tính một lần rồi **đóng băng
# thành hằng số** trong graph. Graph vì thế có thể đúng với độ dài lúc export và **sai âm
# thầm** với độ dài khác — mà ô parity sắp tới chạy 500 câu đủ mọi độ dài.
#
# Không suy luận được từ code, **phải đo**: chạy PyTorch và ONNX trên một lô có batch lẫn
# độ dài khác hẳn lúc export, rồi so từng phần tử. So ở đây là **fp32 vs fp32**, chưa dính
# lượng tử hoá — lệch ở đây thì lỗi nằm ở export, không phải ở INT8.

# %%
cau_kiem = [
    "Ngan",
    "Cong ty co ho tro xuat hoa don VAT khong",
    "Chính sách đổi trả hàng trong 7 ngày kể từ ngày nhận hàng",
    "Chính sách đổi trả áp dụng cho sản phẩm còn nguyên tem nhãn, chưa qua sử dụng, kèm hoá "
    "đơn mua hàng và được gửi về kho trong vòng bảy ngày làm việc kể từ ngày khách nhận hàng",
    "ship bao lau v",
]
enc_kiem = tokenizer(cau_kiem, return_tensors="pt", padding=True, truncation=True, max_length=512)

print("batch×seq lúc export:", tuple(mau["input_ids"].shape))
print("batch×seq lúc kiểm :", tuple(enc_kiem["input_ids"].shape), "← phải KHÁC dòng trên")

# sess_fp32 đã mở ở ô gom trọng số — không mở lại, mỗi lần là đọc 2,1 GB từ đĩa.
with torch.no_grad():
    v_torch = encoder(enc_kiem["input_ids"], enc_kiem["attention_mask"]).numpy()
v_onnx = chay_onnx(sess_fp32, enc_kiem)

lech = float(np.abs(v_torch - v_onnx).max())
print("lệch lớn nhất PyTorch vs ONNX fp32:", lech)
assert lech < 1e-4, (
    f"Graph KHÔNG tổng quát hoá được: lệch {lech:.3e} ở kích thước khác lúc export. "
    "Nhánh if bị đóng băng lúc trace. Đừng đi tiếp — số parity sau đó vô nghĩa."
)
print("→ graph tổng quát hoá được, đi tiếp được")

# %% [markdown]
# ## 4. Lượng tử hoá INT8 **động, per-channel**
#
# Ba lựa chọn ở đây đều có lý do, đừng đổi khi chưa đo lại parity:
#
# - **Động (dynamic)** chứ không tĩnh: không cần tập hiệu chuẩn, và thang đo của
#   activation tính ngay lúc chạy. Tĩnh nhanh hơn chút nhưng cần calibration set đại diện —
#   thứ hiện chưa có, và dùng tập sai còn tệ hơn không lượng tử hoá.
# - **Per-channel** chứ không per-tensor: mỗi cột trọng số có thang riêng. Một cột có
#   outlier thì per-tensor kéo giãn thang cho **toàn bộ** ma trận, mọi cột khác mất độ
#   phân giải. Đây thường là khác biệt giữa parity 0,99 và 0,999.
# - **QInt8** (có dấu) cho trọng số — mặc định và tương thích rộng nhất trên CPU x86.
#
# ⚠️ **Đừng kỳ vọng thu gọn 4 lần.** `quantize_dynamic` chỉ lượng tử hoá trọng số của
# `MatMul`. Bảng nhúng từ vựng (`word_embeddings`, 976 MB) là phép `Gather` nên thường
# **giữ nguyên fp32** ⇒ tỉ lệ thực tế cỡ 1,5–2 lần. Đó là con số phải **báo cáo trung
# thực**, không phải thứ cần chữa. Muốn nhỏ hơn thì phải lượng tử hoá cả embedding — đó
# là một đánh đổi chất lượng khác, chỉ bàn sau khi đã có số parity của bản này.


# %%
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402


def file_du_lieu(duong_dan: Path) -> list[Path]:
    """File external data đi kèm một .onnx. HAI kiểu tên, tuỳ ai sinh ra nó.

    ⚠️ Đo thật:
        onnx.save_model(location="bge-m3-fp32.data")  ->  bge-m3-fp32.data
        quantize_dynamic(use_external_data_format)    ->  bge-m3-int8.onnx.data

    Kiểu thứ hai GIỮ NGUYÊN đuôi .onnx. Chỉ dùng ``with_suffix(".data")`` là bỏ sót
    541 MB trọng số của bản INT8 mà không báo lỗi gì.
    """
    ung_vien = [duong_dan.with_suffix(".data"), Path(str(duong_dan) + ".data")]
    return [p for p in ung_vien if p.exists()]


def kich_thuoc_that(duong_dan: Path) -> int:
    """Cỡ THẬT của model, tính cả external data.

    ⚠️ ``duong_dan.stat().st_size`` một mình là SAI sau khi trọng số ra ngoài:
    bge-m3-fp32.onnx khi đó chỉ còn 0,55 MB vì nó chỉ chứa graph, trong khi model thật
    là 2,16 GB. Lấy nhầm con số đó thì mọi nhánh rẽ theo "có quá 2 GB không" đều sai.
    """
    return duong_dan.stat().st_size + sum(p.stat().st_size for p in file_du_lieu(duong_dan))


quantize_dynamic(
    model_input=str(DUONG_FP32),
    model_output=str(DUONG_INT8),
    weight_type=QuantType.QInt8,
    per_channel=True,  # ràng buộc của kế hoạch Ngày 2
    use_external_data_format=True,  # model 2,16 GB — luôn bật cho chắc
)

kich_thuoc = {
    "fp32_GB": round(kich_thuoc_that(DUONG_FP32) / 1024**3, 3),
    "int8_GB": round(kich_thuoc_that(DUONG_INT8) / 1024**3, 3),
}
kich_thuoc["ti_le_thu_gon"] = round(kich_thuoc["fp32_GB"] / kich_thuoc["int8_GB"], 2)
print(json.dumps(kich_thuoc, indent=2, ensure_ascii=False))

for f in sorted(THU_MUC.iterdir()):
    if f.is_file():
        print(f"{f.stat().st_size / 1024**2:10.2f} MB  {f.name}")

# %% [markdown]
# ## 5. Kiểm khói: cả hai model có chạy và có cho ra 1024 chiều không
#
# Đây **chưa phải** cổng parity. Nó chỉ trả lời "model có nạp và chạy được không" — một
# model lượng tử hoá hỏng hoàn toàn vẫn qua được ô này.

# %%
# sess_fp32 và hai hàm mo_session/chay_onnx đã có từ bước kiểm tổng quát hoá ở trên —
# không định nghĩa lại, không mở lại session fp32 (2,27 GB).
sess_int8 = mo_session(DUONG_INT8)

v_fp32 = chay_onnx(sess_fp32, mau)
v_int8 = chay_onnx(sess_int8, mau)
print("fp32:", v_fp32.shape, "| int8:", v_int8.shape)
assert v_fp32.shape[-1] == v_int8.shape[-1] == SO_CHIEU_BAT_BUOC

# Chuẩn L2 còn giữ được sau khi lượng tử hoá không? Bước 7 rút gọn cosine thành tích vô
# hướng DỰA TRÊN giả định này — kiểm trước khi dựa vào nó.
print("chuẩn L2 int8:", np.linalg.norm(v_int8, axis=-1))

# %% [markdown]
# ## 6. `sha256` của artifact — điều kiện tái lập 3
#
# Chép nguyên khối in ra vào `artifacts/MODEL_REGISTRY.md`. Hash phải lấy từ **file thật**,
# không gõ tay: dòng hash chép sai thì sổ đăng ký thành vô dụng đúng lúc cần nó nhất.
#
# ⚠️ **Phải hash CẢ `.data`, không chỉ `.onnx`.** Sau khi gom trọng số, `.onnx` chỉ còn
# 0,55 MB chứa graph; toàn bộ 2,16 GB trọng số nằm ở `.data`. Hash mỗi `.onnx` thì một file
# `.data` hỏng hay bị thay vẫn cho ra đúng hash — đúng thứ mà sổ đăng ký sinh ra để chặn.

# %%
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def sha256_model(duong_dan: Path) -> dict[str, str]:
    """Hash MỌI file tạo nên model: .onnx (graph) + external data (trọng số).

    Dùng ``file_du_lieu()`` vì hai artifact có hai kiểu tên khác nhau — xem docstring
    của hàm đó. Hash sót file trọng số thì sổ đăng ký vẫn "khớp" khi trọng số đã hỏng.
    """
    kq = {duong_dan.name: sha256_file(duong_dan)}
    for p in file_du_lieu(duong_dan):
        kq[p.name] = sha256_file(p)
    return kq


so_dang_ky = {
    "model_id": MODEL_ID,
    "so_chieu": SO_CHIEU_BAT_BUOC,
    "opset": OPSET,
    "exporter": "TorchScript (dynamo=False)",
    "attention": "eager",
    "pooling": "CLS + chuan hoa L2",
    "luong_tu_hoa": "dynamic INT8, per-channel, QInt8",
    "sha256_fp32": sha256_model(DUONG_FP32),
    "sha256_int8": sha256_model(DUONG_INT8),
    **kich_thuoc,
    "phien_ban": PHIEN_BAN,
}
print(json.dumps(so_dang_ky, indent=2, ensure_ascii=False))

# %% [markdown]
# ---
# ## 🖐 7. CỔNG PARITY — phần bạn TỰ GÕ
#
# Phần còn lại của notebook này là ô 🖐 trong `planning.md` Ngày 2: *"tự gõ script đo"*.
# Nó là **bằng chứng trực tiếp của một chỉ số nghiệm thu**, nên không nhận code sinh sẵn.
#
# **Yêu cầu:** `cosine(fp32, int8) ≥ 0,995` trên **500 mẫu**.
#
# Bạn cần tự quyết và **ghi rõ vào báo cáo** ba điều dưới đây:
#
# 1. **500 câu lấy từ đâu?** Hôm nay mới gõ tay 200 câu với Dev B. Lấy đủ 500 bằng cách
#    nào — thêm câu sinh tự động, thêm đoạn cắt từ tài liệu thật, hay corpus công khai?
#    Đo parity trên tập không đại diện cho tiếng Việt nghiệp vụ thì con số 0,995 không
#    nói lên điều gì. ⚠️ **Đừng dùng `data/intent_test_human.jsonl`** — đó là tập test
#    đóng băng, dùng nó ở đây là làm nhiễm tập đánh giá.
# 2. **Báo cáo con số nào?** Trung bình, hay phân vị thấp nhất? Trung bình 0,997 vẫn có
#    thể che một nhóm câu rớt xuống 0,95. Kế hoạch ghi ngưỡng chứ không ghi thống kê —
#    chọn và nói rõ vì sao. Gợi ý: báo cả `mean` lẫn `min` lẫn `p5`.
# 3. **Độ dài câu có ảnh hưởng không?** Câu dài và câu ngắn thường lệch khác nhau. Một
#    histogram tách theo độ dài là thứ hội đồng hỏi được, và cũng là hình cho báo cáo.
#
# Hai vector đã chuẩn hoá L2 ở bước 2, nên cosine rút gọn thành tích vô hướng — nhưng
# hãy tự kiểm lại điều đó thay vì tin dòng này (ô cuối bước 5 in sẵn chuẩn L2 của bản INT8).
#
# **Ba ràng buộc kỹ thuật, không phải gợi ý:**
#
# - **Chia lô 16–32 câu.** `tokenizer(500_cau, padding=True)` pad TOÀN BỘ về độ dài câu dài
#   nhất: một câu 512 token là bạn có tensor `500×512` chạy qua model 568M trên CPU — rất
#   chậm và dễ hết RAM.
# - **Dùng lại `sess_fp32` / `sess_int8` đã mở ở bước 5.** Đừng gọi `mo_session()` trong
#   vòng lặp: mỗi lần là đọc lại 2,2 GB từ đĩa.
# - **`sha256` của tập 500 câu.** Điều kiện tái lập 3 của `notebooks/README.md` đòi hash
#   **cả dữ liệu vào lẫn artifact ra**. Không hash đầu vào thì con số parity không tái lập
#   được, và nó là con số đi thẳng vào báo cáo.
#
# **Về ngưỡng — đọc kỹ chỗ này.** `notebooks/README.md` ghi *"cosine(fp32, int8) >= 0,995
# trên 500 mẫu"*. Đọc đúng chữ thì đó là ngưỡng trên **`min`**, không phải trên `mean`.
# Gác bằng `mean` thì trung bình 0,997 vẫn xanh trong khi 30 câu rớt xuống 0,94 — đúng cái
# kịch bản README cảnh báo: *"lượng tử hoá hỏng thì hỏng âm thầm"*. Chọn thống kê nào là
# quyết định của bạn, nhưng **phải nói được vì sao** và phải báo cáo cả ba con số.
#
# 🚫 **Không đạt 0,995 thì DỪNG, đổi model.** Đừng hạ ngưỡng, đừng đổi tập mẫu cho dễ.
# Nếu `min` trượt mà `mean` đạt: đó là **kết quả nghiên cứu**, ghi thẳng vào báo cáo kèm
# phân tích nhóm câu nào rớt — không phải thứ để giấu sau con số trung bình.

# %% [markdown]
# ### Nạp và kiểm tập 500 câu (🤖 — chuẩn bị dữ liệu, không phải phép đo)
#
# Đưa file lên bằng `+ Add Input → Upload`, đặt tên dataset `parity-500`. Không chắc đường
# dẫn thì chạy `!ls -R /kaggle/input/` rồi chép nguyên dòng nó in ra.
#
# Ba phép kiểm dưới đây không phải thủ tục: tập đo mà nghèo nàn thì con số parity không nói
# lên điều gì. Đặc biệt là `max` độ dài — nếu nhóm B bị mô hình sinh ngắn hết thì tập mất
# trục "độ dài", mà đó chính là trục sai số lượng tử hoá phụ thuộc mạnh nhất.

# %%
# Tự tìm thay vì hardcode: Kaggle lồng dataset dưới /kaggle/input/datasets/<username>/<slug>/,
# nên đường dẫn có chứa TÊN TÀI KHOẢN. Ghi cứng nó vào đây là người khác chạy lại sẽ gãy —
# mà notebook phải chạy được ở máy người khác thì mới gọi là tái lập.
_tim = sorted(Path("/kaggle/input").rglob("parity_500.jsonl"))
assert _tim, "Chưa gắn dataset parity-500 vào session — bấm '+ Add Input'"
DUONG_PARITY = _tim[0]
print("dùng file:", DUONG_PARITY)

cau_parity = [
    json.loads(d) for d in DUONG_PARITY.read_text(encoding="utf-8").splitlines() if d.strip()
]

print("tổng:", len(cau_parity))
print("theo nhóm:", collections.Counter(c["nhom"] for c in cau_parity))

_trung = len(cau_parity) - len({c["text"].strip().lower() for c in cau_parity})
print("trùng lặp y hệt:", _trung)

_do_dai = sorted(len(c["text"].split()) for c in cau_parity)
print(f"độ dài (từ): min {_do_dai[0]} · p50 {_do_dai[len(_do_dai) // 2]} · max {_do_dai[-1]}")

_mo_dau = collections.Counter(" ".join(c["text"].split()[:3]).lower() for c in cau_parity)
print("5 khuôn mở đầu lặp nhiều nhất:", _mo_dau.most_common(5))

# Điều kiện tái lập 3: hash CẢ dữ liệu vào, không chỉ artifact ra.
sha_parity = sha256_file(DUONG_PARITY)
print("sha256 tập parity:", sha_parity)

assert len(cau_parity) == 500, f"Chưa đủ 500 mục, mới có {len(cau_parity)}"
assert _trung == 0, f"Có {_trung} mục trùng lặp y hệt"

# %%
BATCH_SIZE = 32
diem_cosine = []
nhom_danh_dau = []

# Biết trước có bao nhiêu mẫu bị cắt ở 512 token — đừng để im lặng. Đo thật: 0/500.
_do_dai_token = [len(tokenizer(c["text"])["input_ids"]) for c in cau_parity]
_bi_cat = sum(1 for d in _do_dai_token if d > 512)
print(
    f"độ dài token: min {min(_do_dai_token)} · max {max(_do_dai_token)} "
    f"· bị cắt ở 512: {_bi_cat}/500\n"
)

for i in range(0, len(cau_parity), BATCH_SIZE):
    lo = cau_parity[i : i + BATCH_SIZE]

    # Pad theo câu dài nhất của LÔ HIỆN TẠI. Tokenize cả 500 câu một lượt thì mọi câu bị pad
    # lên 334 token — chậm gấp nhiều lần và dễ hết RAM.
    enc = tokenizer(
        [c["text"] for c in lo],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    )

    v_fp32 = chay_onnx(sess_fp32, enc)
    v_int8 = chay_onnx(sess_int8, enc)

    # Cosine rút gọn thành tích vô hướng CHỈ KHI cả hai vector đều đơn vị.
    # Dung sai phải CHẶT HƠN biên của cổng (0,5%): |v| = 1,005 lọt qua dung sai 1% sẽ biến
    # cosine 0,993 thành 0,998 — đúng thứ mà guard này sinh ra để chặn.
    assert np.allclose(np.linalg.norm(v_fp32, axis=-1), 1.0, atol=1e-4), "Chuẩn L2 fp32 lệch"
    assert np.allclose(np.linalg.norm(v_int8, axis=-1), 1.0, atol=1e-4), "Chuẩn L2 int8 lệch"

    diem_cosine.extend(np.sum(v_fp32 * v_int8, axis=-1).tolist())
    nhom_danh_dau.extend(c["nhom"] for c in lo)

diem_cosine = np.array(diem_cosine)
nhom_danh_dau = np.array(nhom_danh_dau)

mean_tong = float(np.mean(diem_cosine))
p5_tong = float(np.percentile(diem_cosine, 5))
min_tong = float(np.min(diem_cosine))

print("=== PARITY TỔNG THỂ (500 MẪU) ===")
print(f"Mean : {mean_tong:.5f}")
print(f"P5   : {p5_tong:.5f}")
print(f"Min  : {min_tong:.5f}")

# Tách theo nhóm: nhóm C (không dấu, viết tắt) nhiều token hiếm hơn nên đuôi có thể xấu hơn.
# Nếu đúng thì đó là PHÁT HIỆN cho Chương 5, không phải lỗi.
print("\n=== PARITY THEO NHÓM ===")
for n in sorted(set(nhom_danh_dau)):
    d = diem_cosine[nhom_danh_dau == n]
    print(
        f"Nhóm {n} ({len(d):3d} mẫu) | Mean {d.mean():.5f} "
        f"| P5 {np.percentile(d, 5):.5f} | Min {d.min():.5f}"
    )

# Gác bằng MIN, không phải mean: mean 0,997 vẫn xanh khi 30 câu rớt xuống 0,94.
#
# ⚠️ KHÔNG dùng `assert` ở đây, có chủ đích: assert làm gãy lượt `Save & Run All (Commit)`
# ngay tại ô này, và lượt đó chính là bản duy nhất lưu vĩnh viễn được BẰNG CHỨNG của lần
# trượt. Cổng vẫn hiện rõ, chỉ là nó ghi nhận thay vì ném lỗi.
CONG_PARITY_DAT = bool(min_tong >= 0.995)
if CONG_PARITY_DAT:
    print("\nCỔNG PARITY XANH.")
else:
    print(f"\n[TRƯỢT] Cổng parity: min = {min_tong:.5f} < 0,995")
    print("  KHÔNG hạ ngưỡng. Hoãn phán quyết tới Ngày 7: đo Recall@5 fp32 vs INT8 trên")
    print("  bộ vàng — đó mới là chỉ số đích, cosine chỉ là chỉ số thay thế. ADR-0018.")

# %% [markdown]
# ### Tổng kết vào sổ đăng ký

# %%
# Xoá artifact vô dụng: bản int8-matmul tốn 1 298 MB mà parity không đổi (xem ADR-0018).
for _ten in ["bge-m3-int8-matmul.onnx", "bge-m3-int8-matmul.onnx.data"]:
    _p = THU_MUC / _ten
    if _p.exists():
        _p.unlink()
        print("đã xoá", _ten)

# Đo độ trễ 1 câu ngắn — đại diện cho CÂU TRUY VẤN (trên đường request, chịu ngân sách
# 120 ms), không phải đoạn tài liệu (chạy ở RUN_MODE=worker, ngoài đường request).
#
# ⚠️ Con số TUYỆT ĐỐI ở đây KHÔNG tái lập: hai lượt chạy trên "Kaggle CPU" cho 124,5/63,8 ms
# và 76,5/37,2 ms — chênh 1,6 lần tuỳ máy được cấp. Thứ tái lập được là TỈ LỆ fp32/INT8 ≈ 2×.
# p95 nghiệm thu đo ở Ngày 15 trên đúng cấp vCPU đã chốt, không lấy từ đây.
cau_ngan = tokenizer(["Chinh sach doi tra hang trong 7 ngay"], return_tensors="pt")
do_tre = {}
for _ten, _s in [("fp32", sess_fp32), ("int8", sess_int8)]:
    chay_onnx(_s, cau_ngan)  # lượt đầu: khởi động, bỏ qua
    _t = time.perf_counter()
    for _ in range(20):
        chay_onnx(_s, cau_ngan)
    do_tre[_ten] = round((time.perf_counter() - _t) / 20 * 1000, 1)
print("độ trễ 1 câu ~12 token (ms):", do_tre)

so_dang_ky["parity"] = {
    "nguong": 0.995,
    "dat": CONG_PARITY_DAT,
    "mean": round(mean_tong, 5),
    "p5": round(p5_tong, 5),
    "min": round(min_tong, 5),
    "theo_nhom": {
        n: {
            "so_mau": int((nhom_danh_dau == n).sum()),
            "mean": round(float(diem_cosine[nhom_danh_dau == n].mean()), 5),
            "min": round(float(diem_cosine[nhom_danh_dau == n].min()), 5),
        }
        for n in sorted(set(nhom_danh_dau))
    },
    "tap_do": {"so_mau": len(cau_parity), "sha256": sha_parity, "bi_cat_512": _bi_cat},
    "ghi_chu": (
        "TRUOT nguong 0,995. Tap tong hop, chua phai van ban nghiep vu that. "
        "Da BAC BO gia thuyet 'bang nhung la nguyen nhan': loai Gather khoi luong tu hoa "
        "cho mean 0,98503, khong doi so voi 0,98476 — sai so nam o activation cua 24 tang "
        "MatMul. KHONG ha nguong; hoan phan quyet toi Ngay 7 (ADR-0018)."
    ),
}
so_dang_ky["do_tre_1cau_12token_ms"] = {**do_tre, "may": "Kaggle CPU — KHONG tai lap duoc"}

print(json.dumps(so_dang_ky, indent=2, ensure_ascii=False))

# %% [markdown]
# ## 8. Sau khi cổng parity xanh
#
# 1. Tải `bge-m3-int8.onnx` về (Kaggle: Output → Download).
# 2. Điền dòng đầu tiên của `artifacts/MODEL_REGISTRY.md` từ khối `so_dang_ky` ở bước 6,
#    kèm số parity đo được.
# 3. Ghép cặp lại file này: `jupytext --set-formats ipynb,py:percent 06_export_onnx.ipynb`
#    rồi commit **cả hai**.
