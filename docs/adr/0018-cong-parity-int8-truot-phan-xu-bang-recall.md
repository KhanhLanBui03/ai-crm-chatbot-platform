# ADR-0018 — Cổng parity INT8 trượt: hoãn phán quyết, phân xử bằng Recall@5 ở Ngày 7

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-09-26
- **Làn sở hữu:** Track B (module AI) · Dev A
- **Quan hệ:** thi hành [ADR-0015](0015-cau-truc-src-hai-tang-theo-master-plan-v8.md) (kiến
  trúc hai tầng, `inference/` chạy ONNX trên CPU) · ràng buộc số chiều đến từ
  [ADR-0007](0007-pgvector-thay-vector-db-rieng.md) và `V203` (`vector(1024)`)
- **Số 0017 để dành** cho bốn quyết định hợp đồng của Dev B (tên endpoint · bộ topic Kafka ·
  chỗ đặt bộ vàng · cỡ tập test). Chưa viết nên số này nhảy qua.

## Bối cảnh

Kế hoạch Ngày 2 đặt một cổng chặn: export encoder sang ONNX, lượng tử hoá INT8 động
per-channel, và **`cosine(fp32, int8) ≥ 0,995` trên 500 mẫu** (§5.8, `notebooks/README.md`).
Không đạt thì *"artifact không được lên S3"* và kế hoạch ghi *"dừng, đổi model"*.

Đã export và đo xong. **Cổng trượt** — và không phải trượt sát mép:

| Thống kê | Đo được | Ngưỡng |
|---|---|---|
| `mean` | **0,98476** | 0,995 |
| `p5` | 0,97762 | |
| `min` | **0,96692** | 0,995 |

Ngay cả *trung bình* cũng dưới ngưỡng, tức sai số lớn hơn mức cho phép khoảng **10 lần** trên
toàn bộ phân phối, không phải ở vài mẫu đuôi.

### Tách theo nhóm văn bản

Tập đo 500 mẫu gồm ba nhóm, cố ý trải rộng trên trục *độ dài* và *độ hiếm từ vựng* — hai trục
mà sai số lượng tử hoá phụ thuộc mạnh nhất:

| Nhóm | Mô tả | n | `mean` | `min` |
|---|---|---|---|---|
| A | câu hỏi ngắn, có dấu, từ phổ thông | 200 | 0,98760 | 0,98022 |
| B | đoạn tài liệu dài (tới 334 token) | 200 | 0,98188 | 0,96781 |
| C | không dấu · viết tắt · sai chính tả | 100 | 0,98482 | **0,96692** |

Đuôi xấu nhất rơi vào nhóm C — đúng nhóm mà UC022 phải xử lý hằng ngày, và cũng đúng nhóm có
nhiều token hiếm nhất.

### Giả thuyết đã bị bác bỏ bằng thí nghiệm

Nghi phạm đầu tiên là **bảng nhúng từ vựng**: `word_embeddings` chiếm 976 MB / 45% model, có
250 002 hàng với dải giá trị rất rộng giữa token phổ biến và token hiếm. Tỉ lệ thu gọn đo được
là **3,98 lần** — gần đúng 4, nghĩa là bảng nhúng **đã bị** lượng tử hoá cùng mọi thứ khác.

Thí nghiệm kiểm chứng: lượng tử hoá lại với `op_types_to_quantize=["MatMul"]`, giữ `Gather`
(bảng nhúng) ở fp32.

| | `mean` | Kích thước |
|---|---|---|
| Lượng tử hoá toàn bộ | 0,98476 | 541 MB |
| Chỉ `MatMul`, giữ bảng nhúng fp32 | **0,98503** | 1 298 MB |

**Không đổi.** Trả thêm 757 MB để đổi lấy `mean` nhích 0,0003 — tức nằm trong nhiễu. Giả
thuyết sai: nguồn sai số **không** phải bảng nhúng, mà nằm ở 24 tầng `MatMul`, nhiều khả năng
ở khâu lượng tử hoá **activation** mà `quantize_dynamic` làm per-tensor ngay lúc chạy. Họ
XLM-R có outlier activation đã được ghi nhận rộng rãi; nén per-tensor lên phân phối có outlier
là công thức mất độ phân giải.

### Độ trễ — phần đang đạt, nhưng con số tuyệt đối KHÔNG tái lập

Đo trên CPU Kaggle, một câu ~12 token (đại diện cho **câu truy vấn**, không phải đoạn tài liệu):

| Lượt chạy | fp32 | INT8 | Tỉ lệ |
|---|---|---|---|
| Phiên tương tác | 124,5 ms | 63,8 ms | 1,95× |
| Phiên Commit (batch) | **76,5 ms** | **37,2 ms** | 2,06× |

Cùng notebook, cùng phiên bản, hai lượt chạy độc lập — **chênh 1,6 lần**. Máy batch của lượt
Commit sạch hơn và ít tranh chấp CPU hơn máy của phiên tương tác.

Kết luận rút ra phải đúng mức: **tỉ lệ fp32/INT8 ≈ 2× là tái lập được**, còn **con số tuyệt đối
thì không** — nên chúng chỉ là tham khảo, không phải p95 nghiệm thu. p95 thật đo ở Ngày 15 trên
đúng cấp vCPU đã chốt. Cột `p95 đo thật` của `MODEL_REGISTRY.md` để trống tới lúc đó.

Dù vậy, điều cần cho quyết định này vẫn vững: INT8 nhanh gấp đôi, và ở **cả hai** lượt đo nó
nằm trong ngân sách 120 ms, trong khi fp32 thì hoặc trượt hẳn (124,5 ms) hoặc chỉ còn 36% dư
địa (76,5 ms) — mà dư địa đó phải chia tiếp cho tokenize, gọi mạng và phần còn lại của đường
ống. Bỏ INT8 để quay về fp32 **không** phải một lựa chọn.

Phân biệt phải giữ cho đúng: nhúng **câu hỏi** nằm trên đường request và chịu ngân sách 120 ms;
nhúng **đoạn tài liệu** (dài hơn chục lần, đắt hơn tương ứng) chạy ở `RUN_MODE=worker`, ngoài
đường request, nên không tính vào ngân sách đó.

### Artifact thì tái lập được từng byte

Hai lượt chạy độc lập, hai session khác nhau, cho ra **bốn `sha256` trùng khít**:

| File | sha256 |
|---|---|
| `bge-m3-fp32.onnx` | `ff81fec3…415fa5f` |
| `bge-m3-fp32.data` | `303112e4…d8e1f0` |
| `bge-m3-int8.onnx` | `71e2aa91…2723510` |
| `bge-m3-int8.onnx.data` | `65925f1e…3f2703` |

Và `parity.mean` ra đúng `0,98476` ở cả hai lượt. Điều kiện tái lập 1 (ghim seed) và 2 (ghim
phiên bản) của `notebooks/README.md` không phải thủ tục hình thức — đây là bằng chứng chúng có
hiệu lực. Đáng đưa vào báo cáo cạnh chính con số parity.

Đặt cạnh nhau, hai kết quả này cho một kết luận có ích ngoài phạm vi ADR: **artifact tái lập
được, phép đo thời gian thì không.** Mọi ngưỡng dạng "p95 < X ms" trong đồ án chỉ có nghĩa khi
đi kèm cấu hình máy; mọi ngưỡng dạng "cosine ≥ X" hay "sha256 = …" thì tái lập được ở bất kỳ
đâu. Đó là lý do cột `p95 đo thật` để trống tới Ngày 15, còn cột `sha256` điền ngay hôm nay.

---

## Quyết định

1. **Không hạ ngưỡng 0,995.** Giữ nguyên trong `notebooks/README.md` và mọi bảng chỉ số.
2. **Ghi cổng parity Ngày 2 là TRƯỢT**, kèm đủ số đo ở trên, trong `MODEL_REGISTRY.md` và
   báo cáo. Không làm tròn, không chọn thống kê có lợi.
3. **Vẫn dùng bản INT8 cho Ngày 3–7.** Nó là artifact duy nhất vào được ngân sách độ trễ, và
   đường ống RAG cần một encoder chạy được để đi tiếp.
4. **Hoãn phán quyết tới Ngày 7**, phân xử bằng **Recall@5 fp32 so với INT8 trên bộ vàng**,
   **đi kèm** phép so fine-tune ↔ pretrained mà Ngày 7 đã có trong kế hoạch. Dùng lại đúng
   bộ máy đó: cùng bộ vàng v1 của Ngày 6, cùng **paired bootstrap KTC 95%**.
   Tiêu chí — dùng ý nghĩa thống kê, không dùng một ngưỡng chênh lệch tuỳ tiện:
   - KTC 95% của hiệu Recall@5 (fp32 − INT8) **chứa 0** → sai số lượng tử hoá không phân biệt
     được với nhiễu. Kết luận: ngưỡng cosine 0,995 là *chỉ số thay thế* đặt chặt quá so với
     model này. Ghi rõ kèm bằng chứng, giữ INT8, đóng ADR này ở trạng thái *Chấp nhận*.
   - KTC 95% **không chứa 0** và nghiêng về fp32 → sai số có hại thật. Khi đó mới đầu tư lượng
     tử hoá **tĩnh có hiệu chuẩn** (tập 500 câu đã có, dùng luôn làm calibration set), hoặc đổi
     encoder. Viết ADR mới thay thế ADR này.
5. **Vá đường lùi của Ngày 7, vì nó đang trỏ vào chỗ hỏng.** Kế hoạch Ngày 7 ghi *"parity bản
   fine-tune không đạt → DỪNG, giữ bản pretrained"*. Nhưng bản pretrained **chính là bản vừa
   trượt ở ADR này** — đường lùi đó vô hiệu. Đường lùi thật của Ngày 7 là: giữ pretrained
   **fp32** cho nhánh đối chứng, và quyết định ship dựa trên Recall@5 chứ không dựa trên cổng
   parity. Sửa dòng đó trong `planning.md` trước khi tới Ngày 7.
6. **Xoá bản `int8-matmul`** khỏi mọi nơi. Nó tốn 1 298 MB mà không cải thiện gì; giữ lại chỉ
   tạo ra một lựa chọn giả trong các phiên sau.

## Vì sao không làm khác

**Vì sao không hạ ngưỡng xuống 0,98?** Vì con số sẽ "đạt" mà không ai học được gì, và mọi
ngưỡng khác trong đồ án lập tức mất giá trị — nếu ngưỡng nào cũng chỉnh được cho khớp kết quả
thì bảy chỉ số nghiệm thu §1.6 chỉ còn là trang trí.

**Vì sao không đổi model ngay như kế hoạch ghi?** Vì chưa biết nguyên nhân. Thí nghiệm ở trên
đã bác bỏ nghi phạm dễ thấy nhất, và nghi phạm còn lại — lượng tử hoá activation per-tensor —
là **đặc tính của phương pháp, không phải của model**. Đổi sang một encoder 1024 chiều khác
(`multilingual-e5-large` cũng dựa trên XLM-R) nhiều khả năng cho kết quả tương tự. Đổi model
mà không biết vì sao là đánh đổi ba ngày lấy một canh bạc.

**Vì sao không lượng tử hoá tĩnh ngay hôm nay?** Vì `quantize_static` trên model 2,16 GB
external data là rủi ro thật về RAM và thời gian trên Kaggle, và quan trọng hơn: **chưa biết
chỉ số thay thế này có dự báo đúng chỉ số đích hay không**. Đầu tư vài giờ tối ưu cosine trước
khi biết cosine có liên hệ gì với Recall@5 là sai thứ tự. Nếu Recall@5 không đổi thì toàn bộ
công đó là công thừa.

**Vì sao không quay về fp32?** Nó ăn gấp đôi ngân sách độ trễ cho cùng một câu — lượt đo xấu
đã vượt hẳn 120 ms, lượt đo tốt còn đúng 36% dư địa cho **toàn bộ** phần còn lại của đường ống
(tokenize, gọi mạng, truy vấn vector, rerank). Và đó là đo trên một câu 12 token, máy chưa có
tải. Parity của fp32 hoàn hảo theo định nghĩa, nhưng nó không giải được bài toán mà INT8 sinh
ra để giải.

## Đánh đổi

**Được:** đi tiếp được Ngày 3–7 với một artifact đạt ngân sách độ trễ; giữ nguyên tính nghiêm
của mọi ngưỡng; và có một chuỗi thực nghiệm *đo → chẩn đoán → bác bỏ giả thuyết → hoãn phán
quyết cho chỉ số đích* — mạnh hơn hẳn một dòng "parity đạt" cho Chương 5.

**Mất:** mang một ô DoD trượt qua năm ngày. Nếu Ngày 7 cho thấy Recall@5 **có** tụt thì kết quả
truy hồi của Ngày 3–6 phải đo lại bằng encoder mới — rủi ro này là có thật và được chấp nhận
một cách có ý thức, không phải bỏ qua.

**Rủi ro đã lường:** Ngày 7 vốn đã là mốc M1 và đã rất đầy. Thêm một phép so nữa (fp32 ↔ INT8)
bên cạnh phép so đã có (fine-tune ↔ pretrained) làm nó đầy hơn. Giảm nhẹ: chỉ cần nhúng lại
**tập chunk của bộ vàng**, không phải toàn bộ kho tri thức — bộ vàng 84 cặp chỉ chạm vài trăm
chunk, nhúng lại trong vài phút chứ không phải 15–30 phút như reindex đầy đủ.

## Hệ quả

- `artifacts/MODEL_REGISTRY.md`: dòng `encoder` ghi `parity 0,985 — TRƯỢT (ADR-0018)`, không
  để trống và không ghi "đạt".
- Kế hoạch Ngày 7 thêm một ô: **đo Recall@5 fp32 vs INT8 trên bộ vàng**, dùng chung paired
  bootstrap với phép so fine-tune. Ô đó là điều kiện đóng ADR này.
- Kế hoạch Ngày 7 **sửa dòng đường lùi**: "giữ bản pretrained" không còn là đường lùi hợp lệ
  cho cổng parity, vì pretrained cũng trượt cổng đó.
- `notebooks/06_export_onnx.ipynb`: ô parity **không** dùng `assert` làm cổng — nó ghi nhận
  `CONG_PARITY_DAT` và in rõ kết quả trượt. Lý do: `assert` làm gãy lượt `Save & Run All`,
  khiến không có version nào lưu được chính bằng chứng của lần trượt.
- Bản fp32 (2,16 GB) **phải giữ lại** tới hết Ngày 7 — không có nó thì không có đối chứng.

## Số đo và cách tái lập

| | |
|---|---|
| Model | `BAAI/bge-m3`, 1024 chiều, opset 17 |
| Pooling | token CLS + chuẩn hoá L2, **đưa vào trong graph ONNX** |
| Exporter | TorchScript (`dynamo=False` — torch 2.10 mặc định `True`, cần `onnxscript`) |
| Attention | `eager` (ép, thay cho SDPA mặc định) |
| Lượng tử hoá | `quantize_dynamic`, `QInt8`, `per_channel=True` |
| Phiên bản | torch 2.10.0+cpu · transformers 5.0.0 · onnx 1.22.0 · onnxruntime 1.30.0 |
| Kích thước | fp32 2,112 GB → INT8 0,531 GB (**3,98 lần**) |
| Tập đo | 500 mẫu **tổng hợp** (A 200 · B 200 · C 100), `sha256` `4340c12c706b7c3d…35ec0cfd` |
| Cắt ở 512 token | **0/500** (dài nhất 334 token) — không mẫu nào bị cắt âm thầm |
| Graph tổng quát hoá | lệch PyTorch vs ONNX fp32 = `2,57e-07` ở `(5, 43)` so với `(2, 13)` lúc export |

> ⚠️ **Giới hạn của phép đo này phải ghi trong báo cáo:** tập 500 câu là **văn bản tổng hợp do
> LLM sinh**, không phải tài liệu nghiệp vụ thật. Phân phối của nó sạch hơn và trang trọng hơn
> thực tế. Đo lại trên 500 đoạn chunk thật ở Ngày 5 và báo cáo **cả hai** con số.

**`sha256` của artifact:** lấy từ output khối `so_dang_ky` của lượt `Save & Run All (Commit)`
trên Kaggle — không chép từ lượt chạy tương tác, vì lượt đó đã mất theo session.
Điền vào `MODEL_REGISTRY.md`, không gõ tay.
