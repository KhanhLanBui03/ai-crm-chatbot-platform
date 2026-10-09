# Ôn tập Ngày 8 — Nối truy hồi vào lượt chat (UC023, phần `retrieve`)

> Viết 08/10/2026 (lịch gốc 28/09). Quyết định: [ADR-0027](../adr/0027-luot-chat-pipeline-tuan-tu-khong-langgraph.md).
> Đọc trước buổi bảo vệ — mục 2 là ba câu "Phải giải thích được" của kế hoạch.

## 1. Hôm nay hệ thống chạy thế nào

```
POST /v1/ai/chat (X-Tenant-Id do gateway gắn)
  └─ service.answer_turn ─► run_turn (Dev B)
       3. guardrails   4. ai-classify   5. so ngưỡng
       6. mẫu câu (chào, hỏi lại, chuyển giao)  ── 0 LLM
       7. nhánh tri thức ─► RagAnswerer (Dev A, hôm nay)
            normalize_vi(câu gốc) ─► ai-embed ─► vector + (model_id, version)
            get_tenant_session(tenant) ─► hybrid.tim_kiem_lai(k=5)   ← một transaction, SET LOCAL
            needs_rerank? (cờ RERANK_ENABLED=false ⇒ chỉ ghi log)
            sàn từng đoạn 0,15 → bỏ đoạn quá xa
            sàn toàn tập 0,25  → không đoạn nào đạt ⇒ từ chối NOT_COVERED, KHÔNG gọi LLM
            ─► chặng sinh (Ngày 9)
       9–10. ghi lượt (finally — luôn chạy, kể cả khi hỏng)
```

Tệp chính:
- `src/ai/rag/answerer.py`: `RagAnswerer`, `truy_hoi_csdl`;
- `src/ai/rag/rerank/quyet_dinh.py`: `needs_rerank`, `xep_lai`;
- `src/ai/rag/retrieve/hybrid.py`: thêm cột `do_tuong_dong`;
- `src/ai/service.py`: một `RagAnswerer` cho mỗi event loop, dựng trong lifespan.

## 2. "Phải giải thích được"

**`AMBIGUITY_GAP` đo cái gì? Vì sao so hạng 1 với hạng 3 chứ không phải hạng 2?**
- Nó đo **độ phân định của top đầu**. Hạng 1 bỏ xa hạng 3 nghĩa là truy hồi đã chắc, rerank không đổi
  được gì đáng kể. Hạng 1 sát hạng 3 nghĩa là cả cụm đầu "na ná nhau": chỗ cross-encoder đọc kỹ từng
  cặp (câu hỏi, đoạn) mới đáng tiền.
- Không so với hạng 2 vì tài liệu doanh nghiệp hay có **hai đoạn gần trùng** (cùng chính sách ở hai
  phiên bản, bảng giá và trang khuyến mãi nói cùng một sản phẩm). Hạng 1 sát hạng 2 là bình thường,
  và cả hai thường cùng đúng. So với hạng 2 thì câu nào cũng thành "mơ hồ" và cổng mất tác dụng.
- **Đo trên cosine, không phải điểm RRF như kế hoạch ghi.** Điểm RRF với k = 60 chỉ nằm trong
  0,016–0,033, nên chênh giữa hai hạng bất kỳ luôn dưới 0,02 và "< 0,15" đúng với 100% câu. Cosine là
  thang tuyệt đối duy nhất mà truy hồi trả về. Ngưỡng 0,15 sẽ hiệu chỉnh khi có reranker thật, để tỉ
  lệ câu mơ hồ rơi vào 30–40%.

**Vì sao rerank 12 ứng viên chứ không rerank cả 20 (hay 30) đã lấy về?**
- Cross-encoder tốn thời gian **tuyến tính theo số cặp**: 12 thay vì 30 là bớt 60% thời gian của chặng
  đắt nhất đường ống.
- Đoạn đúng mà nằm ngoài top-12 của RRF thì cả hai làn đều xếp nó thấp. Rerank rất hiếm khi kéo được
  một đoạn như vậy lên top-5, nên phần đuôi tốn tiền mà gần như không đổi kết quả.

**Vì sao rerank mặc định TẮT dù nó cải thiện chất lượng?**
- Vì "cải thiện" là giả thuyết, còn chi phí độ trễ thì chắc chắn. Cổng bật đặt hai điều kiện cùng lúc:
  nDCG@5 tăng **≥ 5 điểm** VÀ p95 chat vẫn **< 4 s**. Chưa đo được thì không có căn cứ để trả giá.
- §5.3 quy tắc 2: khi ngân sách độ trễ căng, rerank là thứ **cắt đầu tiên**. Để sau cờ thì cắt được
  bằng `.env`, không phải sửa code.
- Hiện thêm một lý do thực tế: `inference/src/roles/rerank.py` vẫn là bản giả (Jaccard). Bật cờ lúc
  này là xếp hạng lại bằng phép đếm từ chung.

## 3. Quyết định hôm nay và vì sao

1. **Không dựng LangGraph (ADR-0027).**
   - Luồng chỉ có một đường chính, ba nhánh mẫu câu tách ra ở đúng một chỗ, không có vòng lặp.
   - Giá trị của LangGraph (vòng lặp tác tử, chờ người duyệt, trạng thái bền) thuộc nhóm MCP, mà nhóm
     này đã hoãn.
   - Dev B đã có `run_turn` kèm 26 ca test. Hợp đồng giữa hai người chỉ là một Protocol hẹp
     (`KnowledgeAnswerer`), không phải một `AgentState` chung.
2. **Truy hồi dùng câu GỐC (`request.message`), không dùng câu đã mở rộng teencode.**
   - Câu gốc đi qua `normalize_vi`, là cùng hàm chuẩn hoá lúc nạp (luật "một hàm cho cả hai đầu").
   - Đó cũng đúng là đường đã đo ở E3 (dense 0,800, hybrid 0,740).
   - `normalize_vietnamese_text` của guardrails làm đổi 7/112 câu bộ vàng ("ko" → "không"). Đổi đầu
     vào truy hồi là đổi một biến chưa đo.
3. **Sàn liên quan áp lên cosine, và chặn TRƯỚC khi gọi LLM.**
   - Không đoạn nào đủ gần thì gửi LLM cũng chỉ nhận lại "không đủ căn cứ" sau 1–2 s, mà vẫn tốn
     một lượt.
   - Chặn sớm thì lượt đó tính vào KPI "≥ 55% lượt không gọi LLM".
4. **Một `RagAnswerer` sống suốt tiến trình**, không tạo mới mỗi lượt:
   - circuit breaker phải nhớ các lượt hỏng trước (tạo mới thì mạch không bao giờ mở);
   - httpx giữ kết nối, khỏi tốn ~200 ms bắt tay TLS mỗi lượt.
5. **Làm nóng pyvi lúc khởi động.** Lần tách từ đầu tiên nạp mô hình CRF mất ~1,6 s (đo được). Không
   làm nóng thì lượt chat đầu tiên sau mỗi lần khởi động pod chịu trọn khoản đó.

## 4. Bằng chứng

- `tests/integration/test_rag_answerer.py`: hai tenant có tài liệu **giống hệt** nhau, cùng vector.
  - Kết quả: mọi trích dẫn chỉ thuộc tenant đang hỏi.
  - Kiểm ngược: cho `RagAnswerer` mở phiên bằng tenant khác ⇒ test **đỏ**.
- `tests/unit/test_rag_answerer.py` (12 ca):
  - dưới sàn ⇒ từ chối, 0 lượt LLM;
  - rerank tắt ⇒ truy hồi k = 5; bật và mơ hồ ⇒ 12 ứng viên, thứ tự đổi.
- E3 chạy lại sau khi thêm cột cosine: **0,800 / 0,740, không đổi** (thứ hạng giữ nguyên).
- Toàn bộ `pytest tests`: 490 qua. Lỗi duy nhất là `test_intent_train_dedup_integrity`, lỗi hash CRLF
  có sẵn của Dev B.

## 5. Điểm yếu đã biết — nói trước khi bị hỏi

- **Sàn 0,25 gần như không chặn gì với bge-m3.** Câu ngoài phạm vi ("lịch thi đấu bóng đá", "thủ đô
  nước Pháp") vẫn có cosine 0,35–0,46 với kho. Lớp chặn thật lúc này là LLM trả `KHONG_DU_CAN_CU`.
  Ngày 10 phải hiệu chỉnh sàn bằng đường cong trên 12 câu ngoài kho + 100 câu có đáp án.
- Chưa có số nDCG@5 có/không rerank: chờ reranker ONNX thật (Khối 2).
- `ai-classify` chưa chạy được (thiếu `router_model.onnx`, nợ của Dev B), nên mọi câu đều đi nhánh
  RAG khi chạy trên máy. Đường nhanh "chào shop → 0 LLM" chưa kiểm được đầu–cuối.
