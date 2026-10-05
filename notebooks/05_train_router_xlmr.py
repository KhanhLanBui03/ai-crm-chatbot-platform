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
# # UC022 (2/4) — Nhánh B: fine-tune XLM-RoBERTa base `[R&D]`
#
# Chạy trên **Kaggle GPU T4**. Notebook này làm trọn ba việc và xuất đúng ba file mà
# `scripts/evaluate_router_branches_comparison.py` đọc:
#
# | File (trong `/kaggle/working/`) | Nội dung |
# |---|---|
# | `router_branch_b_predictions.jsonl` | dự đoán cho đủ 200 câu test: `{"id", "pred", "confidence"}` |
# | `router_branch_b_latency.json` | p50/p95 suy luận MỘT câu trên **CPU 2 luồng** (như `ai-classify`) |
# | `router_branch_b_summary.json` | Macro-F1 validation + test, phiên bản thư viện, hash dữ liệu |
#
# ## Cách chạy trên Kaggle
#
# 1. **Tạo Dataset** (Kaggle → Datasets → New): tải lên hai file `data/intent_train_dedup.jsonl`
#    và `data/intent_test_human.jsonl`. Tên gợi ý: `ai-crm-intent-router-data`.
# 2. **Tạo Notebook**, File → Import Notebook → chọn `notebooks/05_train_router_xlmr.ipynb`.
# 3. Cột phải: **Add Input** → chọn dataset ở bước 1 · **Accelerator: GPU T4 x1** ·
#    **Internet: On** (để tải `xlm-roberta-base`).
# 4. **Save Version → Save & Run All (Commit)** — chạy nền, tắt máy được.
# 5. Sáng hôm sau: mở version đã chạy → tab **Output** → tải 3 file, chép vào `reports/eval/`
#    của repo, rồi chạy `python scripts/evaluate_router_branches_comparison.py --no-export`.
#
# **Không chỉnh sửa số liệu đầu ra bằng tay.** Notebook không chạy hết thì không có số — ghi
# "nhánh B chưa đánh giá" trong báo cáo.
#
# ## Bốn điều kiện tái lập (§5.8)
# 1. Seed 42 cho `random`, `numpy`, `torch`, và `Trainer`.
# 2. In phiên bản thư viện vào `router_branch_b_summary.json`.
# 3. Kiểm SHA-256 hai file dữ liệu với `artifacts/DATA_HASHES.txt` — lệch thì DỪNG.
# 4. Ghép cặp `.ipynb` ↔ `.py` bằng jupytext.

# %% [markdown]
# ## 1. Môi trường, seed, dữ liệu

# %%
import hashlib
import json
import os
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
torch.cuda.manual_seed_all(RANDOM_SEED)

# Hash đã đóng băng trong artifacts/DATA_HASHES.txt — lệch là đang huấn luyện/đánh giá trên dữ liệu khác
EXPECTED_SHA256 = {
    "intent_train_dedup.jsonl": "d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d",
    "intent_test_human.jsonl": "8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf",
}

# SMOKE_TEST: chạy thử ở máy dev bằng mô hình tí hon để bắt lỗi code trước khi tốn một đêm GPU.
# Kết quả smoke test KHÔNG phải số liệu nhánh B — vì vậy nó không bao giờ ghi vào reports/eval/.
SMOKE_TEST = os.getenv("ROUTER_B_SMOKE") == "1"
if SMOKE_TEST:
    OUT_DIR = Path(os.environ["ROUTER_B_OUT"])
elif Path("/kaggle/working").is_dir():
    OUT_DIR = Path("/kaggle/working")
else:
    OUT_DIR = Path("reports/eval")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_file(name: str) -> Path:
    """Tìm file dữ liệu trong /kaggle/input (mọi dataset đã gắn) hoặc data/ của repo."""
    candidates = list(Path("/kaggle/input").rglob(name)) if Path("/kaggle/input").is_dir() else []
    candidates += [Path("data") / name, Path("../data") / name]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(f"Không tìm thấy {name} — đã gắn dataset ở bước 3 chưa?")


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


data_paths = {name: find_file(name) for name in EXPECTED_SHA256}
for name, path in data_paths.items():
    got = sha256(path)
    assert got == EXPECTED_SHA256[name], f"HASH LỆCH {name}: {got} != {EXPECTED_SHA256[name]}"
    print(f"OK  {name:28s} {got}")

train_rows = load_jsonl(data_paths["intent_train_dedup.jsonl"])
test_rows = load_jsonl(data_paths["intent_test_human.jsonl"])
assert len(test_rows) == 200, len(test_rows)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Python {sys.version.split()[0]} · torch {torch.__version__} · thiết bị: "
      f"{torch.cuda.get_device_name(0) if DEVICE == 'cuda' else 'CPU'}")
print(f"Train: {len(train_rows)} câu · Test: {len(test_rows)} câu")

# %% [markdown]
# ## 2. Nhãn và chia train / validation
#
# Validation tách từ **tập train** (dữ liệu sinh từ template), 15%, phân tầng. Điểm validation vì
# vậy đo trên cùng phân phối với train và sẽ cao hơn điểm trên câu người thật — **chỉ dùng để chọn
# checkpoint**, không dùng để so sánh với nhánh C. So sánh dùng 200 câu test.

# %%
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

INTENT_TAXONOMY = [
    "GREETING", "KB_SEARCH", "PRICING_POLICY", "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN", "TECH_ERROR", "BUYING_INTENT",
]
label2id = {lab: i for i, lab in enumerate(INTENT_TAXONOMY)}
id2label = {i: lab for lab, i in label2id.items()}

if SMOKE_TEST:  # 20 câu mỗi nhãn — đủ cho chia phân tầng, chạy vài giây
    train_rows = [r for lab in INTENT_TAXONOMY for r in [x for x in train_rows if x["intent"] == lab][:20]]
texts = [r["text"] for r in train_rows]
labels = [label2id[r["intent"]] for r in train_rows]
tr_x, va_x, tr_y, va_y = train_test_split(
    texts, labels, test_size=0.15, random_state=RANDOM_SEED, stratify=labels
)
print(f"train {len(tr_x)} · validation {len(va_x)}")

# %% [markdown]
# ## 3. Fine-tune `xlm-roberta-base`

# %%
import transformers
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "optimum-intel-internal-testing/tiny-random-xlm-roberta" if SMOKE_TEST else "xlm-roberta-base"
MAX_LENGTH = 128
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
NUM_EPOCHS = 1 if SMOKE_TEST else 4
WEIGHT_DECAY = 0.01

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


class IntentDataset(torch.utils.data.Dataset):
    def __init__(self, xs: list[str], ys: list[int]):
        self.enc = tokenizer(xs, truncation=True, max_length=MAX_LENGTH)
        self.ys = ys

    def __getitem__(self, i):
        item = {k: v[i] for k, v in self.enc.items()}
        item["labels"] = self.ys[i]
        return item

    def __len__(self):
        return len(self.ys)


def compute_metrics(eval_pred):
    logits, y_true = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"accuracy": accuracy_score(y_true, preds), "macro_f1": f1_score(y_true, preds, average="macro")}


model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, num_labels=len(INTENT_TAXONOMY), id2label=id2label, label2id=label2id
)

# Warmup 10% số bước. Tính tay thành warmup_steps vì transformers 5.x đã bỏ warmup_ratio,
# còn Kaggle có thể đang chạy 4.x hoặc 5.x — warmup_steps có ở cả hai.
WARMUP_STEPS = int(0.1 * NUM_EPOCHS * -(-len(tr_x) // BATCH_SIZE))

args = TrainingArguments(
    output_dir=str(OUT_DIR / "xlmr_ckpt"),
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=64,
    learning_rate=LEARNING_RATE,
    warmup_steps=WARMUP_STEPS,
    weight_decay=WEIGHT_DECAY,
    eval_strategy="epoch",          # tên cũ "evaluation_strategy" đã bị bỏ ở transformers mới
    save_strategy="epoch",
    save_total_limit=1,             # /kaggle/working giới hạn ~20 GB; mỗi checkpoint ~1 GB
    load_best_model_at_end=True,
    metric_for_best_model="macro_f1",
    fp16=(DEVICE == "cuda"),
    seed=RANDOM_SEED,
    data_seed=RANDOM_SEED,
    logging_steps=25,
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=IntentDataset(tr_x, tr_y),
    eval_dataset=IntentDataset(va_x, va_y),
    data_collator=DataCollatorWithPadding(tokenizer),
    compute_metrics=compute_metrics,
)

t0 = time.time()
train_result = trainer.train()
train_seconds = time.time() - t0
val_metrics = trainer.evaluate()
print(f"Huấn luyện xong sau {train_seconds / 60:.1f} phút")
print("Validation (chỉ để chọn checkpoint):", val_metrics)

# %% [markdown]
# ## 4. Dự đoán trên 200 câu test người thật → `router_branch_b_predictions.jsonl`

# %%
model = trainer.model.eval()


@torch.no_grad()
def predict(batch_texts: list[str], device: str) -> tuple[list[str], list[float]]:
    enc = tokenizer(batch_texts, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt").to(device)
    probs = torch.softmax(model(**enc).logits.float(), dim=-1)
    conf, idx = probs.max(dim=-1)
    return [id2label[int(i)] for i in idx], [float(c) for c in conf]


model.to(DEVICE)
preds, confs = [], []
for i in range(0, len(test_rows), 32):
    p, c = predict([r["text"] for r in test_rows[i:i + 32]], DEVICE)
    preds += p
    confs += c

with open(OUT_DIR / "router_branch_b_predictions.jsonl", "w", encoding="utf-8") as f:
    for r, p, c in zip(test_rows, preds, confs, strict=True):
        f.write(json.dumps({"id": r["id"], "pred": p, "confidence": round(c, 6)}, ensure_ascii=False) + "\n")

y_test = [r["intent"] for r in test_rows]
test_f1 = f1_score(y_test, preds, average="macro")
test_acc = accuracy_score(y_test, preds)
print(f"TEST 200 câu người thật — Accuracy {test_acc:.4f} · Macro-F1 {test_f1:.4f}")
print(classification_report(y_test, preds, labels=INTENT_TAXONOMY, digits=4, zero_division=0))

# %% [markdown]
# ## 5. Độ trễ một câu trên CPU 2 luồng → `router_branch_b_latency.json`
#
# `ai-classify` chạy `cpus: 2`, `OMP_NUM_THREADS=2` (inference/compose.inference.yml), và ngân
# sách §5.3 là **p95 ≤ 60 ms trên CPU**. Đo trên GPU không trả lời được câu hỏi đó.
#
# Đo hai biến thể, đều batch 1, gồm cả tokenize:
# - **FP32** — mô hình như vừa huấn luyện.
# - **INT8 dynamic** (`torch.ao.quantization.quantize_dynamic` trên các lớp Linear) — gần với cách
#   ship qua ONNX INT8. `p95_cpu_ms` báo cáo lấy **biến thể nhanh hơn**, tức có lợi cho nhánh B:
#   nếu ngay cả bản nhanh nhất vẫn vượt 60 ms thì kết luận loại nhánh B là chắc chắn.

# %%
import copy

CPU_THREADS = 2
torch.set_num_threads(CPU_THREADS)
cpu_fp32 = copy.deepcopy(model).to("cpu").float().eval()
cpu_int8 = torch.ao.quantization.quantize_dynamic(copy.deepcopy(cpu_fp32), {torch.nn.Linear}, dtype=torch.qint8)
latency_texts = [r["text"] for r in test_rows]


@torch.no_grad()
def bench(m, warmup: int = 10) -> dict:
    for t in latency_texts[:warmup]:
        m(**tokenizer(t, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"))
    times = []
    for t in latency_texts:
        t0 = time.perf_counter()
        m(**tokenizer(t, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"))
        times.append((time.perf_counter() - t0) * 1000)
    return {"p50_ms": round(float(np.percentile(times, 50)), 2),
            "p95_ms": round(float(np.percentile(times, 95)), 2),
            "samples": len(times)}


lat_fp32 = bench(cpu_fp32)
lat_int8 = bench(cpu_int8)
print("CPU FP32 :", lat_fp32)
print("CPU INT8 :", lat_int8)

ckpt_dir = OUT_DIR / "xlmr_best"
trainer.save_model(str(ckpt_dir))
tokenizer.save_pretrained(str(ckpt_dir))
size_mb = sum(p.stat().st_size for p in ckpt_dir.rglob("*") if p.is_file()) / 1024 / 1024

best = min((lat_fp32, "fp32"), (lat_int8, "int8_dynamic"), key=lambda x: x[0]["p95_ms"])
latency = {
    "p95_cpu_ms": best[0]["p95_ms"],
    "p50_cpu_ms": best[0]["p50_ms"],
    "variant": best[1],
    "fp32": lat_fp32,
    "int8_dynamic": lat_int8,
    "cpu_threads": CPU_THREADS,
    "model_size_mb": round(size_mb, 1),
    "measured_on": (f"{'Kaggle' if Path('/kaggle').is_dir() else platform.node()} CPU · "
                    f"{platform.processor() or platform.machine()} · torch {torch.__version__}"),
    "note": "batch 1, gồm tokenize; CPU Kaggle khác CPU production — đo lại trên máy đích nếu cần",
}
(OUT_DIR / "router_branch_b_latency.json").write_text(json.dumps(latency, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(latency, ensure_ascii=False, indent=2))

# %% [markdown]
# ## 6. Tổng kết → `router_branch_b_summary.json`

# %%
summary = {
    "model": MODEL_NAME,
    "hyperparameters": {"max_length": MAX_LENGTH, "batch_size": BATCH_SIZE, "learning_rate": LEARNING_RATE,
                        "epochs": NUM_EPOCHS, "weight_decay": WEIGHT_DECAY, "seed": RANDOM_SEED},
    "data_sha256": {name: sha256(p) for name, p in data_paths.items()},
    "train_size": len(tr_x),
    "validation_size": len(va_x),
    "train_minutes": round(train_seconds / 60, 1),
    "validation": {k: v for k, v in val_metrics.items() if isinstance(v, (int, float))},
    "test_200_human": {"accuracy": round(test_acc, 4), "macro_f1": round(test_f1, 4)},
    "latency_cpu": latency,
    "environment": {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    },
    "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
(OUT_DIR / "router_branch_b_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("\nTải 3 file router_branch_b_*.json(l) từ tab Output về reports/eval/ của repo.")
