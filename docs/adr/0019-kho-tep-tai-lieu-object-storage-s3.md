# ADR-0019 — Tệp tài liệu gốc lưu ở object storage giao thức S3 (RustFS ở dev, AWS S3 trên cloud)

- **Trạng thái:** Chấp nhận (27/09/2026)
- **Ngày:** 2026-09-27
- **Làn sở hữu:** Cả hai — java-core ghi tệp, ai-service đọc tệp

## Bối cảnh

UC018 yêu cầu lưu tệp gốc "vào kho lưu trữ theo đường dẫn có chứa `tenant_id`" — cô lập ngay ở
tầng lưu trữ, không chỉ ở câu truy vấn. Đặc tả không chỉ định công nghệ. Ranh giới hai làn đặt
ở URI tệp: java-core nhận tệp từ người dùng và ghi vào kho, ai-service đọc tệp để kiểm định dạng
(UC018) và phân tích cú pháp (UC019), java-core không bao giờ đọc nội dung tệp.

Ba ràng buộc có sẵn trong repo:

1. **ai-service chạy hai vai trò ở hai pod riêng** (`RUN_MODE=api|worker`, §3.9.1), scale bằng
   `replicas`. Pod API nhận yêu cầu tải lên, pod worker phân tích tệp — hai pod có thể nằm trên
   hai node khác nhau.
2. **Master Plan đã chốt nguyên tắc không giữ trạng thái:** "instance không giữ trạng thái nào —
   mọi thứ nạp lại từ S3 khi khởi động". Artifact model đã đi theo đường Kaggle → S3 → EKS qua IRSA.
3. **Image ai-service đang nợ dung lượng** (776 MB, ngưỡng < 400 MB) — mọi phụ thuộc mới phải cân.

Bản đầu của route UC018 (commit `641bec1`) dùng volume dùng chung giữa java-core và ai-service.
ADR này thay thiết kế đó trước khi có dòng code nào phụ thuộc vào hệ thống tệp.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Volume dùng chung (đường dẫn trên đĩa) | Đơn giản nhất khi chạy compose một máy; không thêm dịch vụ | Trên EKS cần volume ReadWriteMany (EFS/NFS) cho java-core, pod API và pod worker — thêm hạ tầng, chậm, đắt. Làm ai-service giữ trạng thái, ngược nguyên tắc của Master Plan |
| B. Object storage giao thức S3 | Không giữ trạng thái; nhiều pod đọc cùng lúc không cần chung đĩa; cùng đường với artifact model; phân quyền theo policy (java-core chỉ ghi, ai-service chỉ đọc) | Thêm một dịch vụ ở dev; ai-service phải tải tệp về tệp tạm để kiểm định dạng |
| C. Lưu nội dung tệp trong PostgreSQL (`bytea`) | Cùng transaction với bản ghi tài liệu; RLS phủ luôn nội dung tệp | Phình CSDL và bản sao lưu với tệp tới 20 MiB; java-core phải ghi vào schema `knowledge` của Track B — vi phạm ranh giới hai làn |

Với phương án B, máy chủ S3 cho môi trường dev:

| Máy chủ | Kết luận |
|---|---|
| MinIO | **Loại.** Ngừng phát hành image từ 10/2025, chế độ chỉ bảo trì từ 12/2025, repo bị lưu trữ vĩnh viễn ngày 25/04/2026. Đã kiểm ngày 27/09/2026: `minio/minio` trả 404 trên Docker Hub, không tag nào trên Docker Hub lẫn quay.io còn kéo được |
| MinIO do Chainguard build | Loại. Upstream đã lưu trữ nên không còn bản vá bảo mật; bản miễn phí chỉ có tag `latest`, không ghim được phiên bản |
| SeaweedFS | Trưởng thành, nhưng cấu hình nhiều thành phần (master, volume, filer, cổng S3) và không có giao diện quản lý tiện cho nhóm dev |
| **RustFS 1.0.0** | **Chọn.** Cùng API S3, dùng được với client của MinIO, có giao diện web; bản chính thức 1.0.0 ngày 16/09/2026; Apache-2.0; một container, ghim được phiên bản |

## Quyết định

Tệp tài liệu gốc lưu ở object storage giao thức S3 dưới key `{tenant_id}/…`: RustFS 1.0.0 trong
docker compose ở môi trường dev, AWS S3 trên cloud; ai-service đọc bằng thư viện `minio` cho Python.

## Lập luận

- **Giao thức S3 là hợp đồng, máy chủ thay được.** Chính quá trình ra quyết định này đã chứng minh
  điều đó: đổi từ MinIO sang RustFS không phải sửa dòng code nào, chỉ đổi image trong compose.
  Lên AWS S3 cũng chỉ đổi `S3_ENDPOINT` và bỏ khoá để dùng IAM role.
- **Không giữ trạng thái** — khớp nguyên tắc của Master Plan và bỏ được nhu cầu volume RWX giữa
  các pod.
- **Thư viện `minio` thay vì `boto3`:** thêm khoảng 8,5 MB so với khoảng 27 MB (riêng `botocore`
  25 MB) — đáng kể khi image đang nợ dung lượng. Nói S3 chuẩn nên chạy được với mọi máy chủ S3,
  hỗ trợ IRSA (`IamAwsProvider`). SDK vẫn được bảo trì (commit gần nhất 23/08/2026) dù máy chủ
  MinIO đã lưu trữ.
- **413 trước khi tải:** ai-service lấy dung lượng bằng HEAD rồi mới tải, và tải tối đa
  `giới hạn + 1` byte — tệp quá lớn bị loại mà không phải kéo về.

## Đánh đổi

1. **Thêm hạ tầng ở dev:** một container RustFS và một container khởi tạo bucket chạy một lần.
2. **RustFS còn trẻ** (1.0.0 ra đời chưa tới hai tuần lúc chọn). Giảm rủi ro: chỉ dùng ở dev,
   production là AWS S3; code chỉ dùng ba thao tác S3 cơ bản (HEAD, GET theo khoảng byte, PUT).
3. **ai-service tải cả tệp (tối đa 20 MiB) về tệp tạm** cho mỗi lượt tải lên, để nhận ra DOCX
   (danh mục ZIP nằm ở cuối tệp). Tốn I/O và độ trễ hơn đọc trực tiếp trên volume.
4. **Một bucket chung cho mọi tenant:** quyền đọc của ai-service phủ toàn bucket, nên chốt chặn
   cô lập tenant nằm ở code (`rag/ingest/luu_tru.kiem_uri_thuoc_tenant`), không nằm ở policy của
   kho. Bucket riêng cho từng tenant bị loại vì giới hạn số bucket của S3 và chi phí vận hành với
   quy mô SME; siết bằng policy theo tiền tố (STS session tag) để lại cho giai đoạn sau.
5. **Dev dùng chung tài khoản gốc của RustFS** cho java-core và ai-service — chưa tách quyền.
   Trên cloud tách bằng IAM: java-core chỉ `PutObject`, ai-service chỉ `GetObject` (thêm
   `DeleteObject` khi làm UC020/UC041).
6. **Phụ thuộc SDK của một công ty đã lưu trữ máy chủ mã nguồn mở.** Nếu SDK ngừng bảo trì, chuyển
   sang `boto3` (+~18 MB); mọi lời gọi S3 gói trong một tệp `integrations/object_storage.py` nên
   việc đổi chỉ khoanh ở đó.

## Hệ quả

- **Hợp đồng java-core ↔ ai-service:** `file_uri` có dạng `s3://{bucket}/{tenant_id}/…/{tên-tệp}`;
  thêm mã lỗi `503 STORAGE_UNAVAILABLE` (kho S3 không đọc được — phía gọi nên thử lại). Cần cập
  nhật `docs/openapi/` sau khi soạn nháp ở `docs/contracts/` (luật contract-first).
- **Lược đồ:** không đổi. `knowledge_documents.file_path` lưu URI `s3://` dựng lại từ bucket và
  key đã kiểm, không lưu nguyên văn chuỗi phía gọi gửi.
- **java-core (mục C của Ngày 3):** ghi tệp vào bucket bằng MinIO Java SDK hoặc AWS SDK v2, key
  bắt đầu bằng `tenant_id` lấy từ JWT.
- **Vận hành dev:** compose thêm `rustfs` (API cổng 9010, giao diện web 9011) và `rustfs-init`;
  `.env.example` thêm `S3_*`. Cổng 9000 trên máy chủ giữ cho `mcp-server-mock`.
- **Kiểm thử:** fixture `kho_s3` dựng RustFS bằng testcontainers với cùng image; không dùng module
  MinIO của testcontainers vì nó kéo image đã bị gỡ.
- **UC019, UC020, UC041:** worker đọc tệp qua cùng adapter; gỡ tài liệu và xoá dữ liệu cá nhân cần
  quyền xoá object — mở rộng quyền của ai-service đúng lúc đó, không mở trước.
- **Báo cáo:** chương kiến trúc (vì sao không giữ trạng thái) và mô hình mối đe dọa (cô lập tenant
  ở tầng lưu trữ — URI trỏ sang tenant khác bị chặn trước khi tải).
