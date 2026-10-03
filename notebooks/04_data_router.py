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
# # UC022 — Huấn luyện Router Ý Định: Xử lý Dữ liệu & Đánh giá Gán nhãn chéo
#
# **Mục tiêu nghiên cứu:**
# 1. Xây dựng tập dữ liệu huấn luyện (Training Set) gồm 3.000 mẫu theo ma trận phân bố 6 văn phong thực tế tiếng Việt.
# 2. Thực hiện thuật toán khử trùng lặp gần giống (Near-duplicate Deduplication) dựa trên Jaccard 3-gram để tránh hiện tượng thổi phồng chỉ số.
# 3. Đánh giá độ đồng thuận liên người gán nhãn (**Inter-Annotator Agreement — Cohen's Kappa $\kappa$**) giữa 2 thành viên độc lập (Dev A và Dev B) trên tập test người thật 200 mẫu.
# 4. Bảo đảm 4 điều kiện tái lập khoa học theo Master Plan v8.0 (§5.8).

# %% [markdown]
# ## 1. Thiết lập môi trường & Bốn điều kiện tái lập (§5.8)
# - **Điều kiện 1:** Ghim seed ngẫu nhiên (`seed=42`).
# - **Điều kiện 2:** Ghim và kiểm tra phiên bản các thư viện hạt nhân.
# - **Điều kiện 3:** Đóng băng mã băm SHA-256 vào `artifacts/DATA_HASHES.txt`.
# - **Điều kiện 4:** Ghép cặp notebook `.ipynb` $\leftrightarrow$ `.py` và xuất metric ra file.

# %%
import hashlib
import json
import os
import platform
import random
import sys
from collections import Counter
from pathlib import Path
import matplotlib.pyplot as plt

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

print("=" * 60)
print("KIỂM TRA MÔI TRƯỜNG TÁI LẬP (REPRODUCIBILITY CHECK)")
print("=" * 60)
print(f"Hệ điều hành     : {platform.system()} {platform.release()}")
print(f"Phiên bản Python : {sys.version.split()[0]}")
import matplotlib
print(f"Matplotlib       : {matplotlib.__version__}")
print(f"Random Seed ghim : {RANDOM_SEED}")
print("=" * 60)

# %% [markdown]
# ## 2. Nạp dữ liệu huấn luyện và trực quan hóa phân bố 6 văn phong
#
# Khảo sát ma trận phân bố bắt buộc:
# - **25% Lịch sự đầy đủ (`polite_full`):** 750 mẫu
# - **25% Chat ngắn viết tắt (`short_abbrev`):** 750 mẫu
# - **20% Không dấu (`no_accent`):** 600 mẫu
# - **15% Lỗi chính tả (`typo`):** 450 mẫu
# - **10% Pha tiếng Anh (`en_mix`):** 300 mẫu
# - **5% Emoji cảm xúc (`emoji`):** 150 mẫu

# %%
raw_path = Path("../data/intent_train_raw.jsonl")
if not raw_path.exists():
    raw_path = Path("data/intent_train_raw.jsonl")

raw_records = []
with open(raw_path, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            raw_records.append(json.loads(line))

print(f"Tổng số mẫu thô nạp được: {len(raw_records)}")
style_counts = Counter(r["style"] for r in raw_records)
intent_counts = Counter(r["intent"] for r in raw_records)

# %%
# Vẽ biểu đồ phân bố 6 văn phong
styles = ["polite_full", "short_abbrev", "no_accent", "typo", "en_mix", "emoji"]
style_labels = ["Lịch sự đầy đủ\n(25%)", "Chat ngắn viết tắt\n(25%)", "Không dấu\n(20%)", "Lỗi chính tả\n(15%)", "Pha tiếng Anh\n(10%)", "Kèm Emoji\n(5%)"]
counts = [style_counts[s] for s in styles]
percentages = [c / len(raw_records) * 100 for c in counts]

plt.figure(figsize=(10, 5))
bars = plt.bar(style_labels, percentages, color=['#2b5c8f', '#3670a0', '#4a8bad', '#65a5be', '#8abecf', '#b2d7e0'])
plt.title("Phân bố 6 Văn phong trong Tập Dữ liệu Huấn luyện Thô (3.000 mẫu)", fontsize=13, fontweight='bold', pad=15)
plt.ylabel("Tỉ lệ phần trăm (%)", fontsize=11)
plt.ylim(0, 32)
plt.grid(axis='y', linestyle='--', alpha=0.5)

for bar, pct in zip(bars, percentages):
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{pct:.1f}%\n({int(pct*30)} mẫu)", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
eval_dir = Path("../reports/eval") if Path("../reports").exists() else Path("reports/eval")
eval_dir.mkdir(parents=True, exist_ok=True)
chart_path = eval_dir / "intent_styles_distribution.png"
plt.savefig(chart_path, dpi=200)
print(f"-> Đã lưu biểu đồ phân bố vào {chart_path}")
plt.close()

# %% [markdown]
# ## 3. Đánh giá Khử trùng lặp gần giống (Near-duplicate Deduplication)
#
# Khi sinh dữ liệu tự động hoặc thu thập thực tế, khoảng 25-35% mẫu là bản sao gần giống.
# Sử dụng character 3-gram Jaccard Similarity (ngưỡng $\ge 0.88$) để làm sạch.

# %%
dedup_path = Path("../data/intent_train_dedup.jsonl")
if not dedup_path.exists():
    dedup_path = Path("data/intent_train_dedup.jsonl")

clean_records = []
with open(dedup_path, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            clean_records.append(json.loads(line))

raw_total = len(raw_records)
clean_total = len(clean_records)
removed_total = raw_total - clean_total
dedup_rate = (removed_total / raw_total) * 100

print("KẾT QUẢ KHỬ TRÙNG LẶP:")
print(f"  - Số mẫu ban đầu (Raw)       : {raw_total:,} mẫu")
print(f"  - Số bản sao loại bỏ (Removed): {removed_total:,} mẫu")
print(f"  - Số mẫu sạch giữ lại (Clean) : {clean_total:,} mẫu")
print(f"  - Tỉ lệ làm sạch (Dedup Rate) : {dedup_rate:.2f}%")

# %% [markdown]
# ## 4. Đánh giá Gán nhãn chéo độc lập & Chỉ số Cohen's Kappa ($\kappa$)
#
# Đo lường thỏa thuận liên người gán nhãn giữa Dev A và Dev B trên 200 câu test người thật.
# Thang đo Landis & Koch (1977):
# - $\kappa \ge 0.81$: Almost Perfect Agreement (Đồng thuận gần như tuyệt đối).

# %%
report_path = eval_dir / "annotation_kappa_report.json"
with open(report_path, encoding="utf-8") as f:
    kappa_data = json.load(f)

print("KẾT QUẢ THẨM ĐỊNH COHEN'S KAPPA:")
print(f"  - Tổng số mẫu đánh giá       : {kappa_data['sample_count']}")
print(f"  - Số ca đồng thuận tuyệt đối : {kappa_data['agreed_count']} ({kappa_data['observed_agreement_po']*100:.1f}%)")
print(f"  - Tỉ lệ đồng thuận ngẫu nhiên: {kappa_data['chance_agreement_pe']*100:.1f}%")
print(f"  - Chỉ số Cohen's Kappa κ     : {kappa_data['cohens_kappa']}")
print(f"  - Đánh giá học thuật         : {kappa_data['interpretation']}")
print(f"  - Số ca bất đồng đã giải quyết: {kappa_data['disagreed_count']} ca")

# %% [markdown]
# ### Ma trận Nhầm lẫn Gán nhãn (Confusion Matrix: Dev A vs Dev B)

# %%
intents = [
    "GREETING", "KB_SEARCH", "PRICING_POLICY",
    "COMPLAINT_SUPPORT", "HANDOFF_HUMAN", "TECH_ERROR", "BUYING_INTENT"
]
cm = kappa_data["confusion_matrix"]
matrix_data = [[cm[row][col] for col in intents] for row in intents]

fig, ax = plt.subplots(figsize=(8, 7))
cax = ax.matshow(matrix_data, cmap=plt.cm.Blues, alpha=0.85)

for i in range(len(intents)):
    for j in range(len(intents)):
        val = matrix_data[i][j]
        color = 'white' if val > 15 else 'black'
        fontweight = 'bold' if val > 0 else 'normal'
        ax.text(j, i, str(val), va='center', ha='center', color=color, fontweight=fontweight, fontsize=10)

fig.colorbar(cax)
ax.set_xticks(range(len(intents)))
ax.set_yticks(range(len(intents)))
ax.set_xticklabels(intents, rotation=35, ha='left', fontsize=8.5)
ax.set_yticklabels(intents, fontsize=8.5)
plt.title("Ma trận Nhầm lẫn Gán nhãn: Dev A (Cột) vs Dev B (Dòng)\n(Chỉ số Cohen's Kappa κ = 0.9300)", fontsize=11, fontweight='bold', pad=25)
plt.xlabel("Nhãn phân loại bởi Dev A", fontsize=10, labelpad=10)
plt.ylabel("Nhãn phân loại bởi Dev B (Ground Truth)", fontsize=10)
plt.tight_layout()

cm_chart_path = eval_dir / "kappa_confusion_matrix.png"
plt.savefig(cm_chart_path, dpi=200)
print(f"-> Đã lưu ma trận nhầm lẫn vào {cm_chart_path}")
plt.close()

# %% [markdown]
# ## 5. Đóng băng mã SHA-256 dữ liệu tái lập (§5.8)

# %%
clean_file = Path("../data/intent_train_dedup.jsonl")
if not clean_file.exists():
    clean_file = Path("data/intent_train_dedup.jsonl")

file_hash = hashlib.sha256(clean_file.read_bytes()).hexdigest()
print(f"Mã băm SHA-256 tập train sạch : {file_hash}")

hashes_file = Path("../artifacts/DATA_HASHES.txt")
if not hashes_file.exists():
    hashes_file = Path("artifacts/DATA_HASHES.txt")

current_hashes = hashes_file.read_text(encoding="utf-8")
print("\nNỘI DUNG SỔ ĐÓNG BĂNG HASH (artifacts/DATA_HASHES.txt):")
print("-" * 60)
print(current_hashes.strip())
print("-" * 60)
assert file_hash in current_hashes, "Mã băm chưa được ghi nhận vào DATA_HASHES.txt!"
print("XÁC THỰC THÀNH CÔNG: Dữ liệu đã đóng băng toàn vẹn.")
