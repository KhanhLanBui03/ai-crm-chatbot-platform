-- V214 — Gắn tài liệu tri thức với khách hàng để xoá được dữ liệu cá nhân theo khách.
-- UC041 · ADR-0033 · kế hoạch Ngày 12 (ô "chỉ mục bộ phận theo contact_id")
--
-- Không sửa V201–V213: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.
--
-- Trước V214, không bảng nào của schema knowledge có liên kết tới khách hàng: kho tri thức chỉ nhận
-- tệp do nhân viên tải lên, và "xoá mọi đoạn theo contact_id" (đặc tả UC041) không có gì để lọc.
-- Nhưng doanh nghiệp vẫn có tài liệu mang dữ liệu của MỘT khách — hợp đồng, báo giá riêng, biên bản
-- bảo hành — và khi khách yêu cầu xoá thì những tài liệu đó phải đi theo.
--
-- ĐẶT Ở knowledge_documents, KHÔNG nhân bản xuống knowledge_chunks (Master Plan §4.2 từng đặt ở
-- ai.chunks): đoạn không bao giờ tồn tại ngoài tài liệu của nó (FK ON DELETE CASCADE, V203), và mọi
-- đoạn của một tài liệu cùng thuộc một khách. Nhân bản xuống đoạn là ghi cùng một giá trị lên hàng
-- nghìn dòng, và phải giữ chúng khớp nhau mỗi lần gắn lại liên kết.
--
-- uuid, KHÔNG REFERENCES engagement.contacts: không có khoá ngoại nào từ dải V2xx sang schema của
-- Track A (ADR-0002, migration/README.md) — contact_id là tham chiếu LOGIC như conversation_id.

ALTER TABLE knowledge.knowledge_documents
    ADD COLUMN contact_id uuid;

COMMENT ON COLUMN knowledge.knowledge_documents.contact_id IS
    'Khách hàng mà tài liệu mang dữ liệu cá nhân của họ (UC041) — NULL với tài liệu chung của cửa '
    'hàng. Tham chiếu logic sang engagement.contacts, không có khoá ngoại (ADR-0002). Bản bóng nạp '
    'lại chép theo (document_repository.tao_ban_bong).';

-- Chỉ mục BỘ PHẬN: tuyệt đại đa số tài liệu là tài liệu chung (contact_id NULL). Chỉ mục đủ dòng
-- sẽ chứa toàn NULL để phục vụ một thao tác hiếm (một yêu cầu xoá) — bộ phận chỉ giữ đúng những dòng
-- mà truy vấn xoá cần tìm. tenant_id đứng đầu như mọi chỉ mục khác của Track B: RLS thêm
-- tenant_id = ai.current_tenant() vào MỌI truy vấn.
CREATE INDEX ix_doc_khach
    ON knowledge.knowledge_documents (tenant_id, contact_id)
    WHERE contact_id IS NOT NULL;
