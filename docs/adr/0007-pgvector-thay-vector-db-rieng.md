# ADR-0007 — pgvector trong cùng cụm PostgreSQL thay vì vector DB riêng

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track B

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Lưu embedding bằng `pgvector` (HNSW, m=16, ef_construction=64) ngay trong cụm PostgreSQL 16 đang dùng cho dữ liệu nghiệp vụ. Không vận hành Qdrant/Milvus riêng.

## Lập luận

Tránh vận hành thêm một hệ lưu trữ. Quan trọng hơn: cho phép lọc `tenant_id` ngay trong truy vấn vector, tức là cô lập tenant được đảm bảo ở cùng một chỗ với dữ liệu nghiệp vụ — nhất quán với ADR-0001.

## Đánh đổi

Kém hơn cơ sở dữ liệu vector chuyên dụng ở quy mô hàng chục triệu vector. Chấp nhận được với phân khúc SME; ghi vào Hướng phát triển nếu quy mô vượt ngưỡng.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
