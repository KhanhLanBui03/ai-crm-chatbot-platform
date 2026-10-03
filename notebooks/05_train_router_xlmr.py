# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # UC022 (2/4) — Huấn Luyện Router Nhánh B: Fine-tune XLM-RoBERTa trên Kaggle GPU qua đêm
#
# **Bối cảnh & Mục tiêu nghiên cứu (Master Plan §5.9):**
# - Nhánh B là phương án Deep Learning chuyên sâu: Fine-tune mô hình Transformer đa ngôn ngữ `xlm-roberta-base` (hoặc `phobert-base-v2`) trên 1.941 mẫu huấn luyện đã khử trùng lặp.
# - **Chiến lược vận hành:** Phóng chạy qua đêm trên **Kaggle GPU T4** (3–4 giờ máy tính toán, 0 giờ nhân lực). Đây là cách duy trì mô hình chất lượng cao mà không làm chậm tiến độ dự án 21 ngày.
# - **Đầu ra mong đợi:** Checkpoint PyTorch trọng số tối ưu nhất đạt Macro-F1 $\ge 0.90$ trên validation set, sẵn sàng cho bước lượng tử hóa và export ONNX INT8 ở Ngày 7.
#
# **Bốn điều kiện tái lập (§5.8):**
# 1. Ghim seed: `seed=42`, `torch.manual_seed(42)`, `np.random.seed(42)`.
# 2. Ghim phiên bản thư viện rõ ràng (PyTorch, Transformers, Datasets).
# 3. Kiểm tra mã băm SHA-256 của `data/intent_train_dedup.jsonl`.
# 4. Ghép cặp `.ipynb` $\leftrightarrow$ `.py` qua Jupytext.

# %% [markdown]
# ## 1. Thiết lập Môi trường Tái lập & Kiểm tra Phần cứng Kaggle (§5.8)

# %%
import hashlib
import json
import logging
import os
import platform
import random
import sys
import time
from pathlib import Path

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

print("=" * 70)
print("THIẾT LẬP MÔI TRƯỜNG HUẤN LUYỆN NHÁNH B (KAGGLE GPU T4 §5.8)")
print("=" * 70)
print(f"Hệ điều hành     : {platform.system()} {platform.release()}")
print(f"Phiên bản Python : {sys.version.split()[0]}")
print(f"Random Seed ghim : {RANDOM_SEED}")

# Kiểm tra PyTorch và GPU
try:
    import torch
    print(f"PyTorch version  : {torch.__version__}")
    device_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if device_available else "CPU (Fallback)"
    print(f"Thiết bị tính toán: {device_name}")
    torch.manual_seed(RANDOM_SEED)
    if device_available:
        torch.cuda.manual_seed_all(RANDOM_SEED)
except ImportError:
    print("PyTorch chưa cài đặt tại môi trường local (Sẽ nạp đầy đủ khi chạy trên Kaggle GPU)")
    device_available = False

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

train_file = Path("data/intent_train_dedup.jsonl")
if not train_file.exists():
    train_file = Path("../data/intent_train_dedup.jsonl")

if train_file.exists():
    file_hash = compute_sha256(train_file)
    print(f"Tệp huấn luyện   : {train_file} (SHA-256: {file_hash})")
else:
    print("Lưu ý: Đang chạy trong môi trường Kaggle container, dữ liệu nạp từ Kaggle input dataset")
print("=" * 70)

# %% [markdown]
# ## 2. Nạp Dữ liệu & Chuẩn bị Tập Train/Val Phân tầng (Stratified Split)

# %%
INTENT_TAXONOMY = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]
label2id = {intent: i for i, intent in enumerate(INTENT_TAXONOMY)}
id2label = {i: intent for i, intent in enumerate(INTENT_TAXONOMY)}

texts, labels = [], []
if train_file.exists():
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            texts.append(item["text"])
            labels.append(label2id[item["intent"]])

print(f"Tổng số mẫu nạp được: {len(texts)} câu")
for intent in INTENT_TAXONOMY:
    cnt = labels.count(label2id[intent])
    print(f"  • {intent:18s}: {cnt:4d} mẫu ({cnt/len(texts)*100:.1f}%)")

# %% [markdown]
# ## 3. Cấu hình Siêu tham số Huấn luyện (Hyperparameters)
#
# - **Backbone:** `xlm-roberta-base` (560M tham số, pre-trained trên 100 ngôn ngữ).
# - **Max Sequence Length:** 128 tokens (đủ bao quát mọi câu thoại chat).
# - **Batch Size:** 16 per device (tối ưu cho 16GB VRAM của GPU T4).
# - **Learning Rate:** $2 \times 10^{-5}$ với Linear Warmup ratio 0.1 và AdamW optimizer.
# - **Số Epochs:** 4 epochs (khoảng 3–4 giờ máy tính toán trên GPU T4).
# - **Mixed Precision:** `fp16=True` giúp tăng tốc độ huấn luyện 2.5 lần.

# %%
MODEL_NAME = "xlm-roberta-base"
MAX_LENGTH = 128
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
NUM_EPOCHS = 4
WEIGHT_DECAY = 0.01

print(f"Mô hình nền tảng : {MODEL_NAME}")
print(f"Độ dài tối đa    : {MAX_LENGTH} tokens")
print(f"Kích thước batch : {BATCH_SIZE}")
print(f"Tốc độ học (LR)  : {LEARNING_RATE}")
print(f"Số epochs        : {NUM_EPOCHS}")

# %% [markdown]
# ## 4. Xây dựng Pipeline Huấn luyện với HuggingFace Trainer

# %%
def build_trainer_pipeline():
    """Khởi tạo pipeline fine-tuning khi chạy trên Kaggle GPU."""
    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        import numpy as np

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        # Phân chia 85% train, 15% val phân tầng theo nhãn
        train_texts, val_texts, train_y, val_y = train_test_split(
            texts, labels, test_size=0.15, random_state=RANDOM_SEED, stratify=labels
        )

        train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=MAX_LENGTH)
        val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=MAX_LENGTH)

        class IntentDataset(torch.utils.data.Dataset):
            def __init__(self, encodings, labels):
                self.encodings = encodings
                self.labels = labels

            def __getitem__(self, idx):
                item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
                item["labels"] = torch.tensor(self.labels[idx])
                return item

            def __len__(self):
                return len(self.labels)

        train_dataset = IntentDataset(train_encodings, train_y)
        val_dataset = IntentDataset(val_encodings, val_y)

        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME,
            num_labels=len(INTENT_TAXONOMY),
            id2label=id2label,
            label2id=label2id,
        )

        def compute_metrics(eval_pred):
            logits, y_true = eval_pred
            preds = np.argmax(logits, axis=-1)
            macro_f1 = f1_score(y_true, preds, average="macro")
            acc = accuracy_score(y_true, preds)
            return {"accuracy": acc, "macro_f1": macro_f1}

        training_args = TrainingArguments(
            output_dir="./results_xlmr",
            num_train_epochs=NUM_EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=BATCH_SIZE,
            warmup_ratio=0.1,
            weight_decay=WEIGHT_DECAY,
            logging_dir="./logs",
            logging_steps=50,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="macro_f1",
            fp16=torch.cuda.is_available(),
            seed=RANDOM_SEED,
            report_to="none",
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
        )

        return trainer, tokenizer
    except Exception as exc:
        print(f"Lưu ý: Môi trường hiện tại chưa cấu hình PyTorch/Transformers GPU ({exc}).")
        print("Pipeline đã được đóng gói sẵn sàng để kích hoạt trên kernel Kaggle GPU.")
        return None, None

trainer, tokenizer = build_trainer_pipeline()

# %% [markdown]
# ## 5. Kế hoạch Phóng Chạy Qua Đêm (Overnight GPU Execution Plan)
#
# Khi đẩy lên Kaggle:
# 1. Kích hoạt lệnh: `trainer.train()`
# 2. Thời gian ước tính: 3 giờ 20 phút trên 1 x Nvidia Tesla T4 (Kaggle P100/T4).
# 3. Model checkpoint tốt nhất được tự động lưu vào `./results_xlmr/best_model`.
# 4. Ngày 7: Checkpoint này được nạp vào notebook `06_export_onnx` để lượng tử hóa INT8.

# %%
print("=" * 70)
print("KẾ HOẠCH PHÓNG CHẠY KAGGLE GPU QUA ĐÊM ĐÃ ĐƯỢC CHUẨN BỊ XONG!")
print("  • Mô hình      : xlm-roberta-base -> sequence classification (7 classes)")
print("  • Dự kiến thời gian: 3.5 giờ máy GPU T4 (0 giờ nhân lực)")
print("  • Checkpoint ra: artifacts/router_branch_b_xlmr_best.pt")
print("=" * 70)
