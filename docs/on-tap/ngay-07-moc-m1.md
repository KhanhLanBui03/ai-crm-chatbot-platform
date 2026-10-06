# Ôn tập Ngày 7 — Mốc M1: chốt encoder INT8, đóng bảng thoát M1

> Viết 06/10/2026. Quyết định: [ADR-0026](../adr/0026-bo-fine-tune-embedding.md) (bỏ fine-tune) ·
> [ADR-0021](../adr/0021-cong-parity-int8-truot-phan-xu-bang-recall.md) cập nhật 2 (ship INT8, bỏ
> đo fp32) · [ADR-0006](../adr/0006-hybrid-search-rrf-rerank.md) cập nhật 06/10 (giữ hybrid).

## 1. Hôm nay chốt gì

- **Encoder ship:** `bge-m3-int8`, pretrained, chạy **lô 1** trong container `ai-embed`
  (`inference/compose.inference.yml`, cổng 8091, image 383 MB).
- **Truy hồi ship:** hybrid RRF k = 60, mỗi làn 30 ứng viên.
- **Rerank vẫn làm** ở Ngày 8, sau feature flag, mặc định TẮT.
- **Bỏ:** fine-tune (27/09) và phép đo đối chứng fp32 ↔ INT8 (06/10). Lý do chung: luồng chính
  phải chạy được trước.

## 2. Bảng thoát M1

| # | Điều kiện | Kết quả |
|---|---|---|
| 1 | Tài liệu thật vào `knowledge_chunks` | ✅ |
| 2 | Test cách ly tenant xanh trong CI | ✅ (bước cách ly) |
| 3 | Hybrid ≥ dense + 5 điểm | ❌ −6,0 [−13; +1] |
| 4 | Router trong `ai-classify` | ✅ (Dev B) |
| — | Parity INT8 ≥ 0,995 | ❌ 0,98476, chưa phân xử |

Ô ❌ ghi nguyên, không làm tròn, không đổi ngưỡng. Một bảng toàn ✅ mà không ai tin còn tệ hơn một
bảng có ô ❌ được giải thích rõ.

## 3. "Phải giải thích được"

**Vì sao ship INT8 khi cổng parity trượt và không có đối chứng fp32?**
- Parity (cosine fp32 ↔ INT8 ≥ 0,995) là **chỉ số thay thế**. Thứ thật cần là truy hồi đúng. Trên bộ
  vàng, INT8 cho recall@5 0,800 (dense) và 0,740 (hybrid), đủ để luồng chính chạy và đo tiếp.
- **Nói thẳng giới hạn:** không biết INT8 làm mất bao nhiêu so với fp32, vì đã chọn không đo.
- **Có một manh mối làm nhẹ lo ngại:** chính bản INT8, nhúng theo lô 32 so với nhúng riêng, cũng chỉ
  đạt cos ~0,985. Con số này trùng `parity.mean`. Vậy một phần "trượt parity" có thể nằm ở cách đo
  theo lô. Giả thuyết này **chưa kiểm**, nên chỉ nói là giả thuyết.
- INT8 là artifact duy nhất vào được ngân sách độ trễ: fp32 nặng 2,1 GB, INT8 0,53 GB.

**Vì sao dùng paired bootstrap chứ không so hai con số trần?**
- Hai cấu hình chạy trên **cùng 100 câu**. Câu khó thì khó cho cả hai.
- So hai con số trần là bỏ qua cặp đó, nên độ bất định bị thổi phồng: phần lớn dao động đến từ độ khó
  của từng câu, không phải từ cấu hình.
- Paired bootstrap lấy mẫu lại **theo câu**, mỗi lần tính hiệu của cùng câu đó (B = 10 000, seed 42).
  KTC thu được là KTC của **hiệu**, tức đúng thứ cần biết.

**Hiệu −6 điểm nhưng KTC 95% chứa 0 thì kết luận gì?**
- "Trên 100 câu này, **không phân biệt được** hybrid với dense."
- **Không** được nói "hybrid tệ hơn 6 điểm". Cũng **không** được nói "hai cách bằng nhau": chứa 0
  không chứng minh bằng nhau, chỉ là chưa đủ bằng chứng để nói khác nhau.
- Muốn kết luận chắc hơn thì cần nhiều câu hơn. Đó là việc mở rộng bộ vàng ở Ngày 13.

**Vì sao trượt điều kiện #3 mà không cắt rerank?**
- Luật "trượt M1 → cắt rerank, bỏ semantic cache" viết để **gỡ lịch** khi các ngày trước trễ.
- Ở đây ô #3 trượt vì **kết quả đo**, không vì trễ lịch. Cắt rerank cũng không làm hybrid tốt lên.
- Ngược lại, rerank (cross-encoder xếp lại 12 ứng viên đầu sau RRF) là tầng **có thể sửa** đúng lỗi đo
  được: làn từ khoá yếu đẩy đoạn sai lên top-5.
- Rerank vẫn giữ cổng riêng: bật khi tăng ≥ 5 điểm nDCG@5 và p95 chat < 4 s.

## 4. Một ràng buộc mới phải nhớ

**Kho và câu hỏi phải nhúng bằng cùng một đường `ai-embed`.**
- Cùng `int8-71e2aa91`, cùng onnxruntime 1.30, nhưng macOS và container Linux cho vector lệch nhau:
  cos trung bình 0,9956, thấp nhất 0,982, chỉ 53/112 câu trùng khít. GEMM INT8 khác nhau một chút
  giữa nền tảng, rồi lượng tử hoá động khuếch đại sai khác đó.
- Hệ quả đo được: dense đổi 1 câu (0,790 → 0,800) khi chuyển đường nhúng. Vì vậy số chính thức lấy từ
  đường container, tức đường production.
- `model_version` không mã hoá nền tảng. Đổi image hoặc nền tảng thì phải nhúng lại kho, như khi đổi
  model.

## 5. Câu hội đồng dễ hỏi

**"Bảng M1 của em có hai ô đỏ, vậy là trượt mốc?"**
- Trả lời: hai ô đỏ là **kết quả đo**, không phải việc chưa làm. Cả hai có số, có KTC hoặc ngưỡng, có
  ADR giải thích.
- Luồng chính vẫn đi tiếp, vì cả hai ô không chặn luồng chạy: encoder chạy được, truy hồi chạy được,
  chỉ là chưa đạt kỳ vọng ban đầu.
