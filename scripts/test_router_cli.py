#!/usr/bin/env python3
"""Công cụ kiểm thử nhanh Router Ý Định (Intent Router CLI Test Tool).

Hỗ trợ kiểm thử trực tiếp kiến trúc định tuyến 3 tầng (UC022):
- Tầng 1: Rule-based Regex (bắt từ khóa khẩn cấp / xã giao)
- Tầng 2: ONNX Model INT8 (suy luận vector BGE-M3 1024 chiều)
- Tầng 3: Abstention Gate Fallback sang LLM (khi độ tự tin < τ* = 0.65)

Cách dùng:
1. Chạy bộ câu mẫu chuẩn:
   python scripts/test_router_cli.py

2. Kiểm thử 1 câu tùy ý:
   python scripts/test_router_cli.py "Báo giá gói Pro cho công ty 20 người"

3. Chế độ tương tác nhập trực tiếp:
   python scripts/test_router_cli.py --interactive
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Đảm bảo đường dẫn import cho ai-service và inference
_repo_root = Path(__file__).resolve().parent.parent
_ai_service_src = _repo_root / "ai-service" / "src"
_inference_src = _repo_root / "inference" / "src"

if str(_ai_service_src) not in sys.path:
    sys.path.insert(0, str(_ai_service_src))
if str(_repo_root / "inference") not in sys.path:
    sys.path.insert(0, str(_repo_root / "inference"))

from src.roles.classify import ClassifyRequest, classify

# Danh sách câu mẫu bao quát 3 tầng định tuyến và các biến thể thực tế
SAMPLE_QUERIES = [
    ("Xin chào bạn, chúc một ngày làm việc tốt lành!", "GREETING", "Tầng 1 (Rule-based Regex)"),
    ("Cho mình gặp trực tiếp nhân viên tư vấn người thật", "HANDOFF_HUMAN", "Tầng 1 (Rule khẩn cấp)"),
    ("Hệ thống bị lỗi 500 không đăng nhập vào dashboard được", "TECH_ERROR", "Tầng 1 (Rule báo lỗi)"),
    ("Bảng giá gói cước dịch vụ CRM hàng tháng là bao nhiêu?", "PRICING_POLICY", "Tầng 2 (ONNX INT8)"),
    ("Bên bạn có tích hợp Zalo Official Account không?", "KB_SEARCH", "Tầng 2 (ONNX INT8)"),
    ("Tôi muốn ký hợp đồng mua gói Enterprise cho 50 user", "BUYING_INTENT", "Tầng 2 (ONNX INT8)"),
    ("Dịch vụ bên bạn hỗ trợ quá chậm, tôi rất thất vọng", "COMPLAINT_SUPPORT", "Tầng 2 (ONNX INT8)"),
    ("cái này dùng sao", "KB_SEARCH / ABSTENTION", "Tầng 3 (Abstention Gate -> LLM)"),
    ("cho hỏi thêm chút về cái đó", "ABSTENTION", "Tầng 3 (Câu mờ nhạt -> LLM)"),
]


async def run_single_test(text: str) -> None:
    req = ClassifyRequest(text=text)
    t0 = time.perf_counter()
    res = await classify(req)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    intent = res["intent"]
    conf = res["confidence"]
    tier = res["tier_used"]
    fallback = res["fallback_to_llm"]
    probs = res["probabilities"]

    # Phân loại màu / biểu tượng hiển thị
    tier_label = {
        "tier1_rule": "⚡ TẦNG 1: Rule-based Regex",
        "tier2_onnx": "🧠 TẦNG 2: ONNX Model INT8",
        "tier3_llm_fallback": "🛡️ TẦNG 3: Abstention Gate -> LLM Fallback",
    }.get(tier, tier)

    print("-" * 75)
    print(f"📝 Câu nhập vào     : \"{text}\"")
    print(f"🎯 Ý định phân loại : {intent}")
    print(f"📊 Độ tự tin       : {conf * 100:.2f}%")
    print(f"🚀 Tầng xử lý       : {tier_label}")
    print(f"🤖 Fallback sang LLM: {'CÓ (Câu khó/mơ hồ)' if fallback else 'KHÔNG (Tự tin cao)'}")
    print(f"⏱️ Độ trễ xử lý    : {latency_ms:.3f} ms")

    # Hiển thị Top-3 xác suất
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
    top_probs_str = " | ".join([f"{k}: {v*100:.1f}%" for k, v in sorted_probs])
    print(f"📈 Phân bố Top-3   : {top_probs_str}")
    print("-" * 75)


async def run_sample_suite() -> None:
    print("=" * 80)
    print("🤖 BỘ KIỂM THỬ MẪU 3 TẦNG ĐỊNH TUYẾN Ý ĐỊNH (ROUTER UC022)")
    print("=" * 80)

    for i, (query, expected, note) in enumerate(SAMPLE_QUERIES, 1):
        req = ClassifyRequest(text=query)
        t0 = time.perf_counter()
        res = await classify(req)
        lat = (time.perf_counter() - t0) * 1000.0

        fb_tag = "[LLM]" if res["fallback_to_llm"] else "[AUTO]"
        tier_short = {
            "tier1_rule": "Tier-1 Rule",
            "tier2_onnx": "Tier-2 ONNX",
            "tier3_llm_fallback": "Tier-3 LLM ",
        }.get(res["tier_used"], res["tier_used"])

        print(f"[{i:02d}] {fb_tag} {tier_short} | Conf: {res['confidence']*100:5.1f}% | Lat: {lat:5.2f}ms | Intent: {res['intent']:<17} | \"{query}\"")

    print("=" * 80)
    print("💡 Ghi chú:")
    print("   • Tier-1 Rule: Bắt tức thì các từ khóa khẩn cấp / xã giao (< 0.05 ms).")
    print("   • Tier-2 ONNX: Suy luận ma trận nhẹ trên vector BGE-M3 1024 chiều (< 0.5 ms).")
    print("   • Tier-3 LLM : Tự động bỏ phiếu trắng khi tự tin < 65% để gọi LLM phân tích sâu.")
    print("=" * 80)


async def run_interactive_mode() -> None:
    print("=" * 75)
    print("💬 CHẾ ĐỘ KIỂM THỬ TƯƠNG TÁC ROUTER Ý ĐỊNH")
    print("Nhập câu chat bất kỳ để kiểm tra (Gõ 'exit' hoặc 'q' để thoát).")
    print("=" * 75)

    while True:
        try:
            user_input = input("\n👉 Nhập câu hỏi: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Tạm biệt!")
                break
            await run_single_test(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát.")
            break


def main() -> None:
    import asyncio

    parser = argparse.ArgumentParser(description="Kiểm thử Router Ý Định UC022")
    parser.add_argument("query", nargs="?", type=str, help="Câu nói cần phân loại")
    parser.add_argument("-i", "--interactive", action="store_true", help="Chế độ nhập tương tác trực tiếp")
    args = parser.parse_args()

    os.environ["MODEL_ROLE"] = "classify"
    os.environ["OMP_NUM_THREADS"] = "2"

    if args.interactive:
        asyncio.run(run_interactive_mode())
    elif args.query:
        asyncio.run(run_single_test(args.query))
    else:
        asyncio.run(run_sample_suite())


if __name__ == "__main__":
    main()
