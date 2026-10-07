# Ôn tập Ngày 6 — Hybrid search, ai-embed thật, bộ vàng v1, baseline

> Viết 06/10/2026 sau khi khép Ngày 6. Số liệu: [`docs/report/uc023-ngay6-2026-10-06.md`](../report/uc023-ngay6-2026-10-06.md).
> Đọc trước buổi bảo vệ — mục 5 là các câu hội đồng dễ hỏi nhất.

## 1. Hôm nay hệ thống chạy thế nào

```
câu hỏi ──normalize_vi──┬─► ai-embed (bge-m3 INT8, lô 1) ─► vector 1024, đã chuẩn hoá L2
                        └─► build_tsquery (pyvi, <-> trong từ, | giữa từ) ─► tsquery
                                          │
        MỘT câu SQL, trong transaction đã SET app.tenant_id (ai_app, RLS FORCE):
          làn vector    ORDER BY embedding <=> q LIMIT 30 ─┐ row_number → hạng
          làn từ khoá   ORDER BY ts_rank DESC   LIMIT 30 ─┘ row_number → hạng
          RRF: điểm = Σ 1/(60 + hạng) ─► top-5
        cả hai làn lọc: tenant_id = ai.current_tenant() · tài liệu READY · đúng model + version
```

- `src/ai/rag/retrieve/hybrid.py`: câu SQL và tham số HNSW.
- `inference/src/roles/embed.py`: ai-embed.
- `tests/eval/`: harness đo.

Dense / sparse / hybrid chạy **cùng một câu SQL**. Muốn tắt làn nào thì truyền `None` cho làn đó, nên
ba chế độ chỉ khác nhau đúng một biến. Đó là điều kiện để phép so sánh có nghĩa.

## 2. "Phải giải thích được"

**RRF hoạt động thế nào? Vì sao dùng thứ hạng an toàn hơn dùng điểm thô?**
- Mỗi làn tự xếp hạng ứng viên của mình. Mỗi đoạn được cộng `1/(60 + hạng)` cho mỗi làn có nó. Đoạn
  được cả hai làn xếp cao sẽ lên đầu.
- Hai làn đo bằng hai thang không so được với nhau: khoảng cách cosine `<=>` (càng nhỏ càng gần) và
  `ts_rank` (càng lớn càng khớp, độ lớn tuỳ số từ khớp và vị trí khớp). Cộng điểm thô thì phải chuẩn
  hoá hai thang. Chuẩn
  hoá kiểu nào cũng giả định về phân phối, và giả định đó vỡ khi kho đổi.
- Thứ hạng thì luôn là 1, 2, 3…, không cần chuẩn hoá gì. ADR-0006 cấm "cải tiến" thành tổng có
  trọng số vì chính lý do này.

**Vì sao `k = 60`?**
Là hằng số kinh nghiệm của bài báo gốc về RRF (Cormack và cộng sự, 2009), không có lý do "đẹp". Nói
thẳng như vậy mạnh hơn bịa lý do. Về tác dụng: `k` lớn làm khoảng cách giữa hạng 1 và hạng 10 nhỏ
lại, nên một làn không áp đảo được làn kia chỉ nhờ một hạng đầu.

**Vì sao hard negative phải lấy SAU khi hybrid chạy?**
Hard negative là đoạn hệ thống **thực sự nhầm**: lọt top-5 nhưng sai. Chỉ chạy hệ thống mới biết nó
nhầm ở đâu. Negative ngẫu nhiên thì quá dễ, model không học được gì. *Phần fine-tune đã bỏ (27/09),
nhưng câu hỏi này vẫn có thể bị hỏi.*

## 3. Quyết định hôm nay và vì sao

1. **ai-embed chạy lô 1.** Đây là phát hiện quan trọng nhất hôm nay.
   - Hiện tượng: INT8 động tính thang lượng tử hoá activation trên **cả tensor của lô**. Cùng một đoạn,
     nhúng chung lô với đoạn khác, cho cosine chỉ còn ~0,985 so với khi nhúng một mình.
   - Hệ quả nếu ghép lô: vector của đoạn phụ thuộc vào "hàng xóm" tình cờ trong lô. Câu hỏi lúc chat
     luôn nhúng một mình, nên hai phía lệch nhau.
   - Lô 1 còn **nhanh gấp 3** trên CPU (9,8 so với 3,1 đoạn/s): không tốn tính toán cho vị trí pad.
   - Liên hệ ADR-0021: con số 0,985 trùng `parity.mean` 0,98476 ở đó. Có thể cổng parity trượt một
     phần **vì cách đo** (notebook đo theo lô có pad), chưa chắc vì lượng tử hoá. Ngày 7 kiểm bằng
     cách đo fp32 ↔ INT8 ở lô 1.
2. **`model_version` tính từ sha256 của graph, không đọc từ biến môi trường.** Biến môi trường khai
   sai được, hash thì không. Kho ghim `int8-71e2aa91` trên từng đoạn, và truy hồi lọc đúng chuỗi đó
   (bất biến 1).
3. **Bộ vàng do AI làm.** Ba chốt chống tự thiên vị:
   - câu hỏi viết chỉ từ mục lục;
   - danh sách ứng viên khoá bằng hash trước khi xem đoạn;
   - luật cắt định trước (xáo seed 42, lấy tới đủ 100 câu có đáp án).

   Vì sao chỉ từ mục lục: nhìn đoạn rồi đặt câu hỏi thì người viết chép chữ của đoạn, làn từ khoá
   được lợi oan. Giới hạn phải tự nói ra: chỉ có một người gán, không có độ đồng thuận giữa hai
   người gán.
4. **`plan_cache_mode = force_custom_plan`.** psycopg3 tự chuẩn bị câu lệnh sau 5 lần chạy, rồi
   Postgres có thể chuyển sang kế hoạch chung. Khi đó kế hoạch đổi giữa một lượt đo: 5 câu đầu đi
   một đường, các câu sau đi đường khác. Ép kế hoạch riêng cho mỗi câu để số đo có một nghĩa duy nhất.
5. **Nhân bản 20 tenant bằng cách CHÉP vector, không nhúng lại.** Cùng nội dung, cùng model (lô 1)
   thì ra cùng vector. Nhúng lại 19 lần chỉ tốn CPU để ra đúng các dòng đó.
6. **19 tenant giống hệt tenant gốc là ca khó nhất cho HNSW.** Láng giềng gần nhất của mọi câu hỏi
   có 95% là đoạn của tenant khác. HNSW lọc tenant SAU khi quét, nên nếu không có `iterative_scan`
   thì sẽ hụt. Kho thật của 20 SME khác nhau còn dễ hơn ca này.
7. **Bản 1 chính sách đổi trả nằm trong kho ở trạng thái `ARCHIVED`.** Đó là trạng thái thật của kho
   sau khi UC020 lưu trữ bản cũ. Bộ vàng không bao giờ trỏ vào bản 1; nó có mặt để điều kiện
   `status = 'READY'` có việc để làm trong phép đo.

## 4. Kết quả và cách đọc

| | recall@5 | nDCG@5 |
|---|---|---|
| dense | **0,800** | **0,678** |
| sparse | 0,530 | 0,410 |
| hybrid | 0,740 | 0,631 |

Số trên đo qua ai-embed **trong container**, tức đường production, nên là số chính thức. Chạy tay
trên macOS thì dense ra 0,790. Cùng model INT8 nhưng vector lệch theo nền tảng: cosine trung bình
0,9956, thấp nhất 0,982. Vì vậy **kho và câu hỏi phải nhúng cùng một đường** (báo cáo Ngày 6 mục 6).

- **Cổng 1 trượt:** hybrid − dense = −6,0 điểm, KTC 95% [−13; +1].
  - **KTC chứa 0** nghĩa là trên 100 câu này không phân biệt được hybrid với dense.
  - Không được nói "hybrid tệ hơn". Phải nói "không thấy hybrid tốt hơn; điểm ước lượng nghiêng về
    dense".
- **Cổng 2 đạt (Δ = 0), nhưng chưa thử thách HNSW.** "Dùng HNSW = 0%" nghĩa là với 190 đoạn mỗi
  tenant, bộ tối ưu chọn chỉ mục `tenant_id` rồi tính khoảng cách chính xác. Đó là lựa chọn đúng: rẻ
  hơn và không hụt. Đường HNSW có lọc tenant được khoá bằng test tích hợp ép kế hoạch.
- **Vì sao hybrid không thắng:**
  - Làn từ khoá yếu (0,53).
  - RRF chia đều trọng số cho hai làn. Ở 67 câu có dấu, làn yếu đẩy đoạn sai lên nhiều hơn đoạn đúng
    nó cứu được (dense 0,88 → hybrid 0,82).
  - Ở 14 câu **không dấu** thì ngược lại: dense chỉ 0,29, hybrid 0,43. Hai làn bù nhau đúng như
    ADR-0006 lập luận, nhưng chỉ ở nhóm này.

## 5. Câu hội đồng dễ hỏi

**"Hybrid thua dense trên chính bộ vàng của em, sao vẫn chọn hybrid?"**
- Trả lời thẳng bằng ba ý:
  1. Hiệu số không có ý nghĩa thống kê.
  2. Hybrid thắng rõ ở câu không dấu, mà khách nhắn chat thật gõ không dấu nhiều. Bằng chứng ngay
     trong kho mẫu: `cau-hoi-giao-hang-khong-dau.txt` tổng hợp từ tin nhắn fanpage. Bộ vàng chỉ có
     14% câu không dấu.
  3. Tầng rerank (Ngày 8) được thiết kế để xếp lại ứng viên của cả hai làn.
- **Không** nói "em đã chỉnh để hybrid thắng". Bộ vàng đóng băng trước lần đo đầu tiên, và cấu hình
  không đổi sau khi thấy số.

**"Sao không đổi RRF thành tổng có trọng số, cho làn vector nặng hơn?"**
- Chọn trọng số cần dữ liệu riêng để chỉnh. Chỉnh trên chính bộ vàng thì con số trên bộ vàng không
  còn là phép đo. ADR-0006 chọn RRF chính vì không có tham số để chỉnh.

**"Em có chắc bộ vàng không thiên vị làn vector không, khi AI vừa viết câu hỏi vừa gán?"**
- Câu hỏi viết từ mục lục, nên nếu có thiên vị thì thiên vị làn **từ khoá** (từ trong heading), không
  phải làn vector. Vậy kết quả "dense hơn" khó là do bộ vàng.
- Giới hạn còn lại: chỉ một người gán.

## 6. Hệ quả — đã chốt 06/10

Người dùng chốt: **giữ hybrid**, **không cắt rerank**, làn từ khoá để sau. Thêm: **bỏ đo fp32 ↔ INT8**
(ghi chú Ngày 7). Bảng dưới giữ nguyên lập luận lúc đề xuất.

| Việc | Lựa chọn | Đề xuất |
|---|---|---|
| Cấu hình ship của truy hồi | (a) giữ hybrid RRF như ADR-0006 · (b) đổi sang dense-only (ADR mới thay một phần ADR-0006) | **(a)** — hiệu số chưa có ý nghĩa thống kê, hybrid thắng ở câu không dấu |
| Luật "trượt M1 → cắt rerank Ngày 8, bỏ semantic cache Ngày 16" | áp đúng chữ · hoặc coi điều kiện #3 là kết quả kỹ thuật, không phải trễ lịch | Không cắt rerank vì lý do này. Rerank là tầng có thể sửa nhiễu do hợp nhất, và luật đó viết cho trường hợp trượt **lịch** |
| Cải thiện làn từ khoá (ADR-0025 "làn từ khoá theo âm tiết" đang treo) | làm · hoặc để sau | Nếu làm: cần một tập phát triển **tách khỏi** bộ vàng. Chỉnh rồi đo lại trên chính bộ vàng là overfit |
