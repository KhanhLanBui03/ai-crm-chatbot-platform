#!/usr/bin/env python3
"""[R&D] So sánh nhánh Router (UC022 3/4): Macro-F1 + KTC bootstrap, đường cong abstention,
độ trễ đo thật, và (tuỳ chọn) export ONNX INT8 + cổng parity.

NGUYÊN TẮC: mọi con số trong báo cáo phải là SỐ ĐO THẬT. Phiên bản cũ của script này sinh
ngẫu nhiên dự đoán nhánh B (xác suất đúng 88,5%) và gán cứng độ trễ 168,2 ms / 0,182 ms —
đã gỡ toàn bộ.

- Nhánh C: đánh giá đúng LogisticRegression, là mô hình được đóng gói vào ONNX.
- Nhánh B: chỉ đánh giá khi notebook 05 (Kaggle) đã xuất ``reports/eval/router_branch_b_predictions.jsonl``
  (và ``router_branch_b_latency.json`` cho p95 CPU). Không có thì ghi NOT_EVALUATED.
- ``--no-export``: chỉ đánh giá, KHÔNG export lại ONNX và KHÔNG sửa ``artifacts/DATA_HASHES.txt``.

    python scripts/evaluate_router_branches_comparison.py --no-export
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

# Đảm bảo ai-service/src nằm trên sys.path
current_dir = Path(__file__).resolve().parent
ai_service_src = (current_dir.parent / "ai-service" / "src").resolve()
if str(ai_service_src) not in sys.path:
    sys.path.insert(0, str(ai_service_src))

import joblib
import matplotlib.pyplot as plt
import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("router.compare_and_export")

RANDOM_SEED = 42
BOOTSTRAP_ROUNDS = 1000
VECTOR_DIM = 1024
np.random.seed(RANDOM_SEED)

INTENT_TAXONOMY = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]


def compute_sha256(filepath: str | Path) -> str:
    """Tính mã băm SHA-256 của tệp tin."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def plot_confusion_matrix(cm: np.ndarray, labels: list[str], output_path: str, title: str) -> None:
    """Vẽ và lưu biểu đồ heatmap ma trận nhầm lẫn."""
    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    cax = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    fig.colorbar(cax)

    tick_marks = np.arange(len(labels))
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = cm[i, j]
            ax.text(
                j, i, f"{val:d}",
                horizontalalignment="center",
                verticalalignment="center",
                color="white" if val > thresh else "black",
                fontweight="bold" if val > 0 else "normal",
                fontsize=10
            )

    ax.set_ylabel("Thực Tế (Ground Truth)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Dự Đoán (Predicted)", fontsize=10, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    logger.info("Đã lưu biểu đồ: %s", output_path)


def plot_abstention_curve(thresholds: list[float], accuracies: list[float], coverages: list[float], opt_threshold: float, opt_acc: float, opt_cov: float, output_path: str) -> None:
    """Vẽ đồ thị đường cong Abstention: Độ chính xác giữ lại và Tỷ lệ giữ lại theo ngưỡng tin cậy."""
    _fig, ax1 = plt.subplots(figsize=(9, 6))

    color_acc = "tab:blue"
    ax1.set_xlabel("Ngưỡng Tin Cậy (Confidence Threshold τ)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Độ Chính Xác Phần Giữ Lại (Retained Accuracy)", color=color_acc, fontsize=11, fontweight="bold")
    line1 = ax1.plot(thresholds, accuracies, color=color_acc, linewidth=2.5, marker="o", label="Retained Accuracy")
    ax1.tick_params(axis="y", labelcolor=color_acc)
    ax1.axhline(y=0.95, color="green", linestyle="--", linewidth=1.5, label="Mục tiêu Accuracy >= 0.95")
    ax1.set_ylim(0.70, 1.02)
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2 = ax1.twinx()
    color_cov = "tab:orange"
    ax2.set_ylabel("Tỷ Lệ Giữ Lại (Coverage / Retention Rate)", color=color_cov, fontsize=11, fontweight="bold")
    line2 = ax2.plot(thresholds, coverages, color=color_cov, linewidth=2.0, linestyle="-.", marker="s", label="Coverage")
    ax2.tick_params(axis="y", labelcolor=color_cov)
    ax2.set_ylim(0.0, 1.05)

    # Đánh dấu điểm ngưỡng tối ưu được chọn
    ax1.plot(opt_threshold, opt_acc, marker="*", markersize=14, color="red", label=f"Điểm chọn τ*={opt_threshold:.2f} (Acc={opt_acc:.2%}, Cov={opt_cov:.1%})")

    lines = line1 + line2 + [plt.Line2D([0], [0], color="green", linestyle="--"), plt.Line2D([0], [0], marker="*", color="red", linestyle="None", markersize=10)]
    labels = ["Retained Accuracy", "Coverage", "Ngưỡng mục tiêu 95%", f"Điểm chọn τ*={opt_threshold:.2f} (Acc={opt_acc:.1%})"]
    ax1.legend(lines, labels, loc="lower left", fontsize=10)

    plt.title("ĐƯỜNG CONG BỎ PHIẾU TRẮNG (ABSTENTION CURVE - UC022 §5.9)\nCân bằng Độ chính xác và Tỷ lệ giữ lại để Fallback sang LLM", fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    logger.info("Đã lưu đồ thị Abstention curve: %s", output_path)


def paired_bootstrap_test(y_true: list[str], y_pred_b: list[str], y_pred_c: list[str], n_rounds: int = BOOTSTRAP_ROUNDS, seed: int = RANDOM_SEED) -> dict[str, Any]:
    """Kiểm định Paired Bootstrap lấy mẫu có hoàn lại B=1000 lần để tính KTC 95%."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    f1_b_list = []
    f1_c_list = []
    delta_list = []

    y_true_arr = np.array(y_true)
    y_b_arr = np.array(y_pred_b)
    y_c_arr = np.array(y_pred_c)

    for _ in range(n_rounds):
        idx = rng.choice(n, size=n, replace=True)
        sample_true = y_true_arr[idx]
        sample_b = y_b_arr[idx]
        sample_c = y_c_arr[idx]

        f1_b = f1_score(sample_true, sample_b, average="macro", zero_division=0)
        f1_c = f1_score(sample_true, sample_c, average="macro", zero_division=0)

        f1_b_list.append(f1_b)
        f1_c_list.append(f1_c)
        delta_list.append(f1_b - f1_c)

    ci_b = (float(np.percentile(f1_b_list, 2.5)), float(np.percentile(f1_b_list, 97.5)))
    ci_c = (float(np.percentile(f1_c_list, 2.5)), float(np.percentile(f1_c_list, 97.5)))
    ci_delta = (float(np.percentile(delta_list, 2.5)), float(np.percentile(delta_list, 97.5)))

    # Two-sided p-value: Tỷ lệ lần delta <= 0 nếu giả thuyết B > C
    p_value = float(np.mean(np.array(delta_list) <= 0.0))

    return {
        "rounds": n_rounds,
        "ci_95_branch_b": [round(ci_b[0], 4), round(ci_b[1], 4)],
        "ci_95_branch_c": [round(ci_c[0], 4), round(ci_c[1], 4)],
        "ci_95_delta": [round(ci_delta[0], 4), round(ci_delta[1], 4)],
        "mean_delta": round(float(np.mean(delta_list)), 4),
        "p_value": round(p_value, 4),
        "statistically_significant": bool(ci_delta[0] > 0.0 or ci_delta[1] < 0.0),
    }


BRANCH_B_PRED_PATH = Path("reports/eval/router_branch_b_predictions.jsonl")
BRANCH_B_LATENCY_PATH = Path("reports/eval/router_branch_b_latency.json")
LATENCY_BUDGET_MS = 60.0  # §5.3 dòng 2 — p95 bước phân loại trên CPU


def load_branch_b(test_ids: list[int]) -> tuple[list[str] | None, dict[str, Any] | None]:
    """Đọc kết quả THẬT của nhánh B do notebook 05 (Kaggle) xuất ra. Không có thì trả None.

    - ``router_branch_b_predictions.jsonl``: mỗi dòng ``{"id": int, "pred": "<INTENT>"}``,
      đủ 200 id của tập test.
    - ``router_branch_b_latency.json``: ``{"p95_cpu_ms": float, "model_size_mb": float,
      "measured_on": "<máy đo>"}`` — đo trên CPU, không phải GPU Kaggle.

    Phiên bản cũ SINH NGẪU NHIÊN dự đoán nhánh B (đúng 88,5%) và gán cứng p95 = 168,2 ms.
    Đã gỡ: không có file thật thì nhánh B được ghi là CHƯA ĐÁNH GIÁ.
    """
    preds = None
    if BRANCH_B_PRED_PATH.is_file():
        rows = [json.loads(line) for line in BRANCH_B_PRED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_id = {int(r["id"]): r["pred"] for r in rows}
        missing = [i for i in test_ids if i not in by_id]
        if missing:
            logger.error("File dự đoán nhánh B thiếu %d id (vd %s) — bỏ qua nhánh B", len(missing), missing[:5])
        else:
            bad = {p for p in by_id.values() if p not in INTENT_TAXONOMY}
            if bad:
                logger.error("Nhánh B có nhãn ngoài taxonomy %s — bỏ qua nhánh B", bad)
            else:
                preds = [by_id[i] for i in test_ids]
    latency = None
    if BRANCH_B_LATENCY_PATH.is_file():
        latency = json.loads(BRANCH_B_LATENCY_PATH.read_text(encoding="utf-8"))
    return preds, latency


def measure_branch_c_latency(embedder: Any, sess: ort.InferenceSession, texts: list[str], repeats: int = 3) -> dict[str, float]:
    """Đo p50/p95 MỘT câu trên CPU máy hiện tại: embedder trong tiến trình + ONNX INT8.

    Lưu ý khi trích dẫn: embedder ở đây là feature hashing (vài trăm micro giây), KHÔNG phải
    BGE-M3. Nếu thay bằng vector thật từ ai-embed qua HTTP thì độ trễ sẽ lớn hơn nhiều —
    con số này chỉ đúng cho artifact hiện tại.
    """
    input_name = sess.get_inputs()[0].name
    full, head = [], []
    for _ in range(repeats):
        for t in texts:
            t0 = time.perf_counter()
            vec = embedder.transform_single(t).reshape(1, -1).astype(np.float32)
            t1 = time.perf_counter()
            sess.run(None, {input_name: vec})
            t2 = time.perf_counter()
            full.append((t2 - t0) * 1000)
            head.append((t2 - t1) * 1000)
    return {
        "p50_ms_embed_plus_classifier": round(float(np.percentile(full, 50)), 3),
        "p95_ms_embed_plus_classifier": round(float(np.percentile(full, 95)), 3),
        "p95_ms_classifier_only": round(float(np.percentile(head, 95)), 3),
        "samples": len(full),
        "machine": f"{platform.system()} {platform.machine()} / {platform.processor() or 'cpu'}",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="So sánh nhánh router + abstention + (tuỳ chọn) export ONNX")
    ap.add_argument(
        "--no-export",
        action="store_true",
        help="KHÔNG export lại ONNX và KHÔNG sửa artifacts/DATA_HASHES.txt — chỉ đánh giá artifact đã đóng băng",
    )
    args = ap.parse_args()

    logger.info("=" * 75)
    logger.info("UC022 (3/4): SO SÁNH NHÁNH ROUTER, ABSTENTION%s", "" if args.no_export else ", EXPORT ONNX INT8")
    logger.info("=" * 75)

    test_file = Path("data/intent_test_human.jsonl")
    if not test_file.is_file():
        logger.error("Không tìm thấy tệp test: %s", test_file)
        sys.exit(1)

    test_items = [json.loads(line) for line in test_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    test_ids = [int(item["id"]) for item in test_items]
    test_texts = [item["text"] for item in test_items]
    test_labels = [item["intent"] for item in test_items]
    logger.info("Nạp %d mẫu test người thật (SHA-256: %s)", len(test_texts), compute_sha256(test_file))

    # 1. Nhánh C — đánh giá ĐÚNG mô hình được ship: LogisticRegression (chính là đồ thị ONNX).
    #    Bản cũ báo cáo dự đoán của kNN trong khi ONNX đóng gói LogisticRegression.
    artifact_c_path = Path("artifacts/router_branch_c.joblib")
    if not artifact_c_path.is_file():
        logger.error("Không tìm thấy artifact Nhánh C: %s", artifact_c_path)
        sys.exit(1)

    artifact_c = joblib.load(artifact_c_path)
    embedder = artifact_c["embedder"]
    clf_lr = artifact_c["classifier_lr"]
    clf_knn = artifact_c["classifier_knn"]

    X_test = embedder.transform(test_texts)
    prob_c = clf_lr.predict_proba(X_test)
    pred_c = clf_lr.classes_[np.argmax(prob_c, axis=1)].tolist()
    acc_c = accuracy_score(test_labels, pred_c)
    f1_c = f1_score(test_labels, pred_c, average="macro")
    f1_knn = f1_score(test_labels, clf_knn.predict(X_test).tolist(), average="macro")
    logger.info("Nhánh C (LogisticRegression — mô hình ship): Accuracy = %.4f | Macro-F1 = %.4f", acc_c, f1_c)
    logger.info("  (tham khảo, KHÔNG ship) kNN: Macro-F1 = %.4f", f1_knn)
    logger.info("  Lưu ý: số trên là MỘT tầng ONNX trên toàn bộ 200 câu, chưa gồm luật tầng 1 của ai-classify")

    # 2. Nhánh B — chỉ từ kết quả THẬT
    pred_b, latency_b = load_branch_b(test_ids)
    branch_b_evaluated = pred_b is not None
    if branch_b_evaluated:
        acc_b = accuracy_score(test_labels, pred_b)
        f1_b = f1_score(test_labels, pred_b, average="macro")
        logger.info("Nhánh B (XLM-R, từ %s): Accuracy = %.4f | Macro-F1 = %.4f", BRANCH_B_PRED_PATH, acc_b, f1_b)
        bootstrap_res = paired_bootstrap_test(test_labels, pred_b, pred_c, n_rounds=BOOTSTRAP_ROUNDS, seed=RANDOM_SEED)
        logger.info("  KTC 95%% B: %s · C: %s · Δ(B-C): %s", bootstrap_res["ci_95_branch_b"],
                    bootstrap_res["ci_95_branch_c"], bootstrap_res["ci_95_delta"])
    else:
        logger.warning("NHÁNH B CHƯA ĐÁNH GIÁ: không có %s. Không so sánh, không bootstrap B–C.", BRANCH_B_PRED_PATH)
        acc_b = f1_b = None
        bootstrap_res = None

    # KTC 95% cho riêng nhánh C — luôn tính được
    rng = np.random.default_rng(RANDOM_SEED)
    y_true_arr, y_c_arr = np.array(test_labels), np.array(pred_c)
    f1_c_boot = []
    for _ in range(BOOTSTRAP_ROUNDS):
        idx = rng.choice(len(test_labels), size=len(test_labels), replace=True)
        f1_c_boot.append(f1_score(y_true_arr[idx], y_c_arr[idx], average="macro", zero_division=0))
    ci_c = [round(float(np.percentile(f1_c_boot, 2.5)), 4), round(float(np.percentile(f1_c_boot, 97.5)), 4)]
    logger.info("  KTC 95%% Macro-F1 nhánh C (bootstrap B=%d): %s", BOOTSTRAP_ROUNDS, ci_c)

    # 3. Đường cong abstention cho nhánh C — trên xác suất và dự đoán của CÙNG một mô hình
    max_confs = np.max(prob_c, axis=1)
    thresholds = [round(float(t), 2) for t in np.arange(0.10, 0.90, 0.05)]
    acc_curve, cov_curve = [], []
    opt = None
    for tau in thresholds:
        mask = max_confs >= tau
        cov = float(np.mean(mask))
        acc_ret = float(accuracy_score(y_true_arr[mask], y_c_arr[mask])) if mask.any() else float("nan")
        acc_curve.append(acc_ret)
        cov_curve.append(cov)
        if opt is None and mask.any() and acc_ret >= 0.95:
            opt = (tau, acc_ret, cov)
    if opt is None:
        logger.warning("Không ngưỡng nào đạt độ chính xác phần giữ lại >= 0,95 trên đường cong này")
        opt_threshold, opt_acc, opt_cov = None, None, None
    else:
        opt_threshold, opt_acc, opt_cov = opt
        logger.info("  τ nhỏ nhất đạt >= 0,95: %.2f (acc %.2f%%, coverage %.2f%%)", opt_threshold, opt_acc * 100, opt_cov * 100)
    tau_prod = 0.65
    i65 = thresholds.index(tau_prod)
    logger.info("  Tại τ đang chạy %.2f: acc phần giữ lại %.2f%%, coverage %.2f%%", tau_prod, acc_curve[i65] * 100, cov_curve[i65] * 100)

    # 4. ONNX: export lại (mặc định, như trước) hoặc dùng artifact đã đóng băng (--no-export)
    onnx_int8_path = Path("artifacts/router_model.onnx")
    if args.no_export:
        logger.info("--no-export: dùng %s đã đóng băng, không sửa DATA_HASHES.txt", onnx_int8_path)
    else:
        onnx_fp32_path = Path("artifacts/router_model_fp32.onnx")
        initial_type = [("float_input", FloatTensorType([None, VECTOR_DIM]))]
        onnx_model = convert_sklearn(clf_lr, name="intent_router_v1", initial_types=initial_type, target_opset=15)
        onnx_fp32_path.write_bytes(onnx_model.SerializeToString())
        quantize_dynamic(model_input=str(onnx_fp32_path), model_output=str(onnx_int8_path), weight_type=QuantType.QUInt8)
        onnx_fp32_path.unlink(missing_ok=True)

    sess = ort.InferenceSession(str(onnx_int8_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    res_onnx = sess.run(None, {input_name: X_test.astype(np.float32)})
    probs_onnx = np.array([[row[c] for c in clf_lr.classes_] for row in res_onnx[1]])
    max_diff = float(np.max(np.abs(prob_c - probs_onnx)))
    label_parity = float(np.mean(np.argmax(probs_onnx, axis=1) == np.argmax(prob_c, axis=1)))
    logger.info("Parity: max |ΔP| = %.2e · khớp nhãn = %.4f", max_diff, label_parity)
    assert max_diff < 1e-4, f"LỖI CỔNG PARITY: Sai số {max_diff} vượt ngưỡng 1e-4"
    onnx_hash = compute_sha256(onnx_int8_path)

    if not args.no_export:
        hashes_file = Path("artifacts/DATA_HASHES.txt")
        if hashes_file.is_file():
            lines = [ln for ln in hashes_file.read_text(encoding="utf-8").splitlines()
                     if "artifacts/router_model.onnx" not in ln and ln.strip()]
            lines.append(f"{onnx_hash}  artifacts/router_model.onnx")
            hashes_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info("Đã cập nhật mã băm ONNX vào artifacts/DATA_HASHES.txt")

    # 5. Độ trễ nhánh C — ĐO THẬT trên máy chạy script (bản cũ gán cứng 0,182 ms)
    latency_c = measure_branch_c_latency(embedder, sess, test_texts)
    logger.info("Độ trễ nhánh C: %s", latency_c)

    # 6. Quy tắc chốt §5.9 — chỉ áp được khi có số đo thật của cả hai nhánh
    b_p95 = latency_b.get("p95_cpu_ms") if latency_b else None
    if not branch_b_evaluated:
        decision = ("Nhánh B chưa được đánh giá trên tập test (không có file dự đoán thật). "
                    "Nhánh C là nhánh DUY NHẤT đã đánh giá — ship nhánh C; chưa có cơ sở so sánh B–C.")
    elif b_p95 is None:
        decision = "Đã có Macro-F1 nhánh B nhưng chưa có p95 CPU đo thật — chưa áp được quy tắc phá thế hoà §5.9."
    elif b_p95 > LATENCY_BUDGET_MS:
        decision = f"Nhánh B vượt ngân sách {LATENCY_BUDGET_MS:.0f} ms (p95 {b_p95} ms đo thật) — loại theo §5.9, ship nhánh C."
    else:
        decision = "Cả hai nhánh trong ngân sách — chốt theo KTC Macro-F1 (§5.9), xem bảng."
    logger.info("QUYẾT ĐỊNH: %s", decision)

    # 7. Biểu đồ — chỉ vẽ nhánh nào có số liệu thật
    plot_confusion_matrix(
        confusion_matrix(test_labels, pred_c, labels=INTENT_TAXONOMY), labels=INTENT_TAXONOMY,
        output_path="reports/eval/router_branch_c_confusion_matrix.png",
        title=f"Ma Trận Nhầm Lẫn Nhánh C: ai-embed + LogReg (Macro-F1={f1_c:.4f})",
    )
    if branch_b_evaluated:
        plot_confusion_matrix(
            confusion_matrix(test_labels, pred_b, labels=INTENT_TAXONOMY), labels=INTENT_TAXONOMY,
            output_path="reports/eval/router_branch_b_confusion_matrix.png",
            title=f"Ma Trận Nhầm Lẫn Nhánh B: XLM-R (Macro-F1={f1_b:.4f})",
        )
    plot_abstention_curve(
        thresholds=thresholds, accuracies=acc_curve, coverages=cov_curve,
        opt_threshold=opt_threshold if opt_threshold is not None else tau_prod,
        opt_acc=opt_acc if opt_acc is not None else acc_curve[i65],
        opt_cov=opt_cov if opt_cov is not None else cov_curve[i65],
        output_path="reports/eval/router_abstention_curve.png",
    )

    # 8. Báo cáo JSON
    report = {
        "metadata": {
            "use_case": "UC022 (3/4)",
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "onnxruntime": ort.__version__,
                "random_seed": RANDOM_SEED,
            },
            "test_set_sha256": compute_sha256(test_file),
            "decision": decision,
            "note": "Mọi số liệu trong báo cáo này là số đo thật; nhánh không có số đo thì ghi null.",
        },
        "branch_c_ai_embed": {
            # SemanticDenseEmbedder là feature hashing n-gram ký tự + IDF (1024 chiều) — docstring
            # của nó tự ghi "mô phỏng" BGE-M3. KHÔNG được mô tả là vector BGE-M3 của ai-embed.
            "architecture": "Feature hashing char 3/4-gram + IDF (1024 chiều, SemanticDenseEmbedder — "
                            "chưa phải BGE-M3) + LogisticRegression -> ONNX INT8",
            "macro_f1": round(f1_c, 4),
            "accuracy": round(acc_c, 4),
            "ci_95_macro_f1": ci_c,
            "knn_reference_macro_f1": round(f1_knn, 4),
            "latency": latency_c,
            "model_size_kb": round(onnx_int8_path.stat().st_size / 1024, 2),
        },
        "branch_b_xlmr": {
            "status": "EVALUATED" if branch_b_evaluated else "NOT_EVALUATED",
            "predictions_file": str(BRANCH_B_PRED_PATH) if branch_b_evaluated else None,
            "macro_f1": round(f1_b, 4) if f1_b is not None else None,
            "accuracy": round(acc_b, 4) if acc_b is not None else None,
            "latency": latency_b,
        },
        "paired_bootstrap_b_vs_c": bootstrap_res,
        "abstention_analysis": {
            "curve": [{"tau": t, "retained_accuracy": None if a != a else round(a, 4), "coverage": round(c, 4)}
                      for t, a, c in zip(thresholds, acc_curve, cov_curve)],
            "smallest_tau_reaching_0_95": opt_threshold,
            "production_tau": tau_prod,
            "at_production_tau": {"retained_accuracy": round(acc_curve[i65], 4), "coverage": round(cov_curve[i65], 4)},
        },
        "onnx_parity_gate": {
            "model_path": str(onnx_int8_path),
            "re_exported": not args.no_export,
            "max_abs_diff_sklearn_vs_onnx_int8": max_diff,
            "label_agreement": label_parity,
            "tolerance": 1e-4,
            "status": "PASSED",
            "sha256": onnx_hash,
        },
    }
    out = json.dumps(report, ensure_ascii=False, indent=2)
    Path("reports/eval/router_branches_comparison_report.json").write_text(out, encoding="utf-8")
    docs_report = Path("docs/report")
    docs_report.mkdir(parents=True, exist_ok=True)
    (docs_report / "router_branches_comparison_report.json").write_text(out, encoding="utf-8")
    logger.info("Đã lưu báo cáo: reports/eval/ và docs/report/router_branches_comparison_report.json")


if __name__ == "__main__":
    main()
