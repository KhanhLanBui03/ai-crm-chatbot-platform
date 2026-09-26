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
# --- 0. Phụ thuộc. Kaggle đã có sẵn torch/transformers; onnx thì thường phải cài thêm.
# !pip install -q "onnx>=1.17" "onnxruntime>=1.20"

# %%
import hashlib
import json
import random
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
backbone = AutoModel.from_pretrained(MODEL_ID).eval()

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
)
print("fp32:", DUONG_FP32, f"{DUONG_FP32.stat().st_size / 1024**3:.2f} GB")

# %%
# --- Ô DỰ PHÒNG: chỉ chạy nếu ô trên báo lỗi vượt 2 GB protobuf.
# m = onnx.load(str(DUONG_FP32), load_external_data=True)
# onnx.save_model(
#     m, str(DUONG_FP32),
#     save_as_external_data=True, all_tensors_to_one_file=True,
#     location="bge-m3-fp32.data", size_threshold=1024,
# )

# %%
# Kiểm graph hợp lệ trước khi lượng tử hoá — quantize trên graph hỏng cho lỗi khó đọc.
onnx.checker.check_model(str(DUONG_FP32))
print("graph fp32 hợp lệ")

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

# %%
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402

qua_2gb = DUONG_FP32.stat().st_size > 2 * 1024**3

quantize_dynamic(
    model_input=str(DUONG_FP32),
    model_output=str(DUONG_INT8),
    weight_type=QuantType.QInt8,
    per_channel=True,  # ràng buộc của kế hoạch Ngày 2
    use_external_data_format=qua_2gb,
)

kich_thuoc = {
    "fp32_GB": round(DUONG_FP32.stat().st_size / 1024**3, 3),
    "int8_GB": round(DUONG_INT8.stat().st_size / 1024**3, 3),
}
kich_thuoc["ti_le_thu_gon"] = round(kich_thuoc["fp32_GB"] / kich_thuoc["int8_GB"], 2)
print(json.dumps(kich_thuoc, indent=2, ensure_ascii=False))

# %% [markdown]
# ## 5. Kiểm khói: cả hai model có chạy và có cho ra 1024 chiều không
#
# Đây **chưa phải** cổng parity. Nó chỉ trả lời "model có nạp và chạy được không" — một
# model lượng tử hoá hỏng hoàn toàn vẫn qua được ô này.

# %%
def chay_onnx(duong_dan: Path, enc: dict) -> np.ndarray:
    sess = ort.InferenceSession(str(duong_dan), providers=["CPUExecutionProvider"])
    return sess.run(
        ["embedding"],
        {
            "input_ids": enc["input_ids"].numpy(),
            "attention_mask": enc["attention_mask"].numpy(),
        },
    )[0]


v_fp32 = chay_onnx(DUONG_FP32, mau)
v_int8 = chay_onnx(DUONG_INT8, mau)
print("fp32:", v_fp32.shape, "| int8:", v_int8.shape)
assert v_fp32.shape[-1] == v_int8.shape[-1] == SO_CHIEU_BAT_BUOC

# %% [markdown]
# ## 6. `sha256` của artifact — điều kiện tái lập 3
#
# Chép nguyên khối in ra vào `artifacts/MODEL_REGISTRY.md`. Hash phải lấy từ **file thật**,
# không gõ tay: dòng hash chép sai thì sổ đăng ký thành vô dụng đúng lúc cần nó nhất.

# %%
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


so_dang_ky = {
    "model_id": MODEL_ID,
    "so_chieu": SO_CHIEU_BAT_BUOC,
    "opset": OPSET,
    "pooling": "CLS + chuan hoa L2",
    "luong_tu_hoa": "dynamic INT8, per-channel, QInt8",
    "sha256_fp32": sha256_file(DUONG_FP32),
    "sha256_int8": sha256_file(DUONG_INT8),
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
# hãy tự kiểm lại điều đó thay vì tin dòng này.
#
# 🚫 **Không đạt 0,995 thì DỪNG, đổi model.** Đừng hạ ngưỡng, đừng đổi tập mẫu cho dễ.

# %%
# 🖐 Code đo parity của bạn viết ở đây.

# %% [markdown]
# ## 8. Sau khi cổng parity xanh
#
# 1. Tải `bge-m3-int8.onnx` về (Kaggle: Output → Download).
# 2. Điền dòng đầu tiên của `artifacts/MODEL_REGISTRY.md` từ khối `so_dang_ky` ở bước 6,
#    kèm số parity đo được.
# 3. Ghép cặp lại file này: `jupytext --set-formats ipynb,py:percent 06_export_onnx.ipynb`
#    rồi commit **cả hai**.
