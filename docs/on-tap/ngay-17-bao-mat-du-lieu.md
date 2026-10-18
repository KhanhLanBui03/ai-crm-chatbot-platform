# Ôn tập Ngày 17 — Mô hình ngôn ngữ có thành đường vòng qua RLS không?

> Viết 18/10/2026 (lịch gốc 07/10). Số liệu: [`docs/report/bao-mat-ngay17-2026-10-18.md`](../report/bao-mat-ngay17-2026-10-18.md).
> Mã đo: `ai-service/tests/eval/bao_mat_ngay17.py` · dữ liệu: `ai-service/tests/eval/bao_mat/`.
> Liên quan: [ADR-0007](../adr/0007-pgvector-thay-vector-db-rieng.md) (lọc `tenant_id` trong truy vấn) ·
> [ADR-0029](../adr/0029-tu-choi-bon-ly-do-va-nguong-tu-duong-cong.md) (sàn cosine = 0) · [ADR-0033](../adr/0033-xoa-du-lieu-ca-nhan-phia-ai.md) (`contact_id`) ·
> [ADR-0035](../adr/0035-dinh-tuyen-duoi-nguong-cong-xac-suat-theo-o.md) (router cộng theo ô) · `docs/threat-model.md` T5, T6, T8.
>
> **Trạng thái:** N17 đóng, **cổng ra đạt \***. Đây là ngày cuối của đợt; sau đó sang tích hợp giao diện.

## 1. Năm con số phải nhớ

| | Số | Ý nghĩa |
|---|---|---|
| Rò rỉ qua đường ngôn ngữ | **0 / 19 câu** | không câu trả lời, trích dẫn hay đoạn truy hồi nào của A chứa dữ liệu B |
| Tầng truy hồi | **0 / 380 đoạn** | 19 câu × top-20 của A, không đoạn nào thuộc tenant khác |
| A từ chối câu hợp lệ | **11 / 11** | cả 11 lượt **qua Gemini**, lý do `NOT_COVERED` |
| Router đưa câu nha khoa vào hỏi lại | **19 / 30** | ~60% câu viết ra không tới được nhánh tri thức |
| Tài liệu riêng của khách bị trích cho khách khác | **hạng 2 / 20** | lỗ hổng `contact_id` tái hiện, giá riêng `61.500.000` lộ ra |

## 2. Hai câu "phải giải thích được" của kế hoạch

**Vì sao "trả lời đúng bằng tài liệu của B" cũng là sai, không chỉ "trả lời sai"?**
Vì câu hỏi là của khách tenant A, và A **không có** tài liệu đó. Nếu A trả lời đúng thì dữ liệu của B đã đi
được tới khách của A. Đó chính là rò rỉ giữa tenant, dù câu trả lời "đúng". "Trả lời sai bằng tài liệu A" là
lỗi khác: mô hình lấy chính sách bảo hành máy lạnh để trả lời câu hỏi về bảo hành răng sứ, tức là bịa. Chỉ có
**từ chối** là đúng. Vì vậy báo cáo chia ba kết cục: LỘ · TỪ CHỐI · KHÔNG TỪ CHỐI.

**RLS đã chặn ở tầng SQL rồi, vậy bài (1) chứng minh thêm điều gì?**
`test_rls.py` chứng minh câu SQL không đọc được hàng của tenant khác. Nhưng giữa câu hỏi của khách và câu trả
lời còn nhiều tầng: router, truy hồi, lời nhắc, Gemini, hậu kiểm. Bài (1) kiểm **cả đường đi** từ đầu tới cuối:
1. **Tầng truy hồi** (ADR-0007): đoạn của B không lọt vào top-20 của A (0/380). Tầng này vẫn là RLS cộng với
   lọc `tenant_id` trong câu SQL, nhưng được thử bằng câu hỏi thật qua đúng hàm production.
2. **Tầng ngôn ngữ:** Gemini nhận 5 đoạn điện máy cho một câu hỏi nha khoa. Nó **có thể** "lấy tạm" chính sách
   bảo hành của A để trả lời. Nó đã không làm vậy: 11/11 lần trả `KHONG_DU_CAN_CU`. Tầng này RLS không chạm tới
   được, và chỉ bài (1) đo được nó.

Lưu ý thêm: với sàn cosine toàn tập = 0 (ADR-0029), **mọi** lời từ chối ở bài này đều do Gemini quyết, không có
lời từ chối nào do sàn. Chạy `LLM_MODE=mock` thì bài này vô nghĩa, vì LLM giả luôn "trả lời" và trích `[1]`.

## 3. Đối chứng dương — ý quan trọng nhất về cách đo

A từ chối thì **chưa chứng minh được gì** nếu chính B cũng không trả lời được câu đó. Có thể tài liệu B chưa
nạp, có thể câu hỏi bị router đưa đi chỗ khác. Vì thế mỗi câu hỏi B trước. Câu chỉ **hợp lệ** khi B trả lời
đúng: có dấu của B trong câu trả lời và có trích dẫn tài liệu B.

Router phân loại theo **câu chữ**, không theo tenant. Nên câu nào B trả lời được qua nhánh tri thức thì ở A cũng
đi nhánh tri thức. Đối chứng dương vì thế loại luôn được mọi câu bị "hỏi lại", mà không cần quy tắc riêng nào.

**Dấu** (canary) là những giá trị chỉ B có, ví dụ `18.750.000`, `15 năm`, `21 tháng`. Kịch bản tự kiểm ba điều
trước khi chạy: dấu có 0 lần trong kho A, có trong kho B, và không nằm trong câu hỏi. Điều cuối cần vì A từ chối
mà nhắc lại câu hỏi thì không được tính là lộ.

## 4. Bốn phát hiện hội đồng có thể hỏi

**(a) Router nhận ra rất ít câu tri thức nha khoa.** 19/30 câu đi `CLARIFY`. Bảy câu qua được đều mang cụm "bao
nhiêu tiền / chi phí / bảng giá" (`PRICING_POLICY 0,940`, nhiều khả năng là tầng luật từ khoá của ai-classify).
Router học trên câu phần mềm nên với lĩnh vực mới còn tệ hơn điện máy (32/100 theo ADR-0035). Đây không phải lỗ
hổng cách ly, vì câu bị hỏi lại thì không truy hồi gì cả. Nhưng đây là hạn chế lớn về chất lượng cho tenant mới.

**(b) Lỗ hổng `contact_id` — rò rỉ TRONG một tenant.** Hợp đồng ưu đãi riêng của một khách nằm trong kho chung,
và câu trả lời cho khách khác nêu rõ *"Riêng đối với khách hàng KH-B17-0042, mức giá ưu đãi… là 61.500.000
đồng"*. `contact_id` (V214) mới dùng để **xoá** (UC041), chưa dùng để **lọc truy hồi**. Muốn sửa thì `ChatRequest`
phải mang `contact_id` của người hỏi, tức là đổi hợp đồng với java-core. Việc này làm cùng đợt tích hợp giao diện.

**(c) java-core ghi bí mật vào log.** `AuthService.java` in mã OTP, token đặt lại mật khẩu và token xác thực
email ở dạng rõ, kèm email. Ai đọc được log là chiếm được tài khoản (T8). Phát hiện này gửi Dev B, không tính vào
cổng của Dev A.

**(d) `mask_pii` không che họ tên.** SĐT, email, CCCD đều được thay bằng `[REDACTED_*]`, nhưng "Lê Văn Thử" thì
đi nguyên vào `ai_interactions.user_query` **và** vào lời nhắc gửi Gemini. Họ tên tiếng Việt khó bắt bằng luật vì
trùng với danh từ thường. Đây là hạn chế cần ghi vào chương 3.

## 5. Ba lần cách đo tự lộ lỗi — và cách xử lý đúng

Đây là phần đáng học nhất của ngày. Cả ba lần đều được ghi vào báo cáo, **không** sửa lặng lẽ:

| Lỗi | Phát hiện lúc | Xử lý |
|---|---|---|
| Dò dấu theo biên `\w` bỏ lọt `420.000đ` | chạy thử, **trước** lượt thật | sửa thành biên "không sát chữ số" (**siết**), ghi bổ sung §1.3 trước khi chạy |
| Ghép kết nối theo cổng ra **0 dòng** (proxy của Docker Desktop đổi cổng), mà `all([])` vẫn in "ĐẠT" | **sau** lượt chạy role | tuyên bố lượt đó **vô hiệu**; đổi sang đối chiếu số đếm, có điều kiện "> 0 kết nối" (**siết**) |
| Mẫu SĐT khớp nhầm `007073-6763` giữa một UUID | **sau** khi quét | giữ **TRƯỢT**; đo lại như một phép đo mới, chốt trước, đánh dấu `*` và gọi là "lạc quan" |

Ba nguyên tắc rút ra:
- **Phép kiểm "đạt" trên tập rỗng là phép kiểm hỏng.** `all()` trên danh sách rỗng luôn `True`. Mọi tiêu chí
  dạng "mọi X đều Y" cần thêm "và có ít nhất một X".
- **Sau khi thấy số thì chỉ được siết.** Nới mẫu SĐT là nới, nên số cũ phải giữ và số mới mang `*`.
- **Đối chứng dương cho chính bộ dò.** "0 kết quả" chỉ có nghĩa khi bộ dò bắt được thứ đã cài vào. Bộ quét log
  đã được thử bằng ba dòng giả (JSON `\uXXXX`, chữ bỏ dấu, dạng thô) trước khi tin con số 0.

## 6. Lệnh để tự chạy lại

```bash
# Hạ tầng + ba service (xem .claude/CLAUDE.md mục Lệnh)
docker compose up -d postgres redis kafka rustfs-init
docker compose -f inference/compose.inference.yml up -d ai-embed ai-rerank   # ai-classify chạy sẵn
cd java-core && EUREKA_CLIENT_ENABLED=false mvn spring-boot:run -Dspring-boot.run.profiles=local
cd ai-service && LLM_MODE=remote python -m src.entrypoint > ../reports/eval/n17-ai-service.log 2>&1
cd ai-service && RUN_MODE=worker python -m src.entrypoint > ../reports/eval/n17-ai-worker.log 2>&1

cd ai-service && source .venv/bin/activate
python -m tests.eval.bao_mat_ngay17 dung-b            # tenant B qua UC018/019 thật (chạy lại không tạo trùng)
python -m tests.eval.bao_mat_ngay17 cach-ly           # bài (1) lượt đầu — ≤ 20 lượt Gemini
python -m tests.eval.bao_mat_ngay17 sang              # sàng bộ câu bổ sung — 0 LLM
python -m tests.eval.bao_mat_ngay17 cach-ly-bo-sung   # chạy câu đã giữ + kết luận gộp
python -m tests.eval.bao_mat_ngay17 role              # (a) (b′) (c)
python -m tests.eval.bao_mat_ngay17 do-pii [--dot 2]  # đầu dò PII
python -m tests.eval.bao_mat_ngay17 contact-id        # lỗ hổng contact_id — 1 lượt Gemini
python -m tests.eval.bao_mat_ngay17 cache             # bài (2)
python -m tests.eval.bao_mat_ngay17 quet-log [--dot 2 --tu <T0>]   # bài (3) — chạy SAU CÙNG
```

Đầu ra ở `reports/eval/n17/*.json` (gitignored). Tenant B: `eca6b30b-114c-4695-a26f-0916c215adf5`, quản trị
`quantri@nha-khoa-b17.test`.
