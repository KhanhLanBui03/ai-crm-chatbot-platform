# Ôn tập Ngày 2 — Tầng truy cập CSDL có RLS và export encoder sang ONNX INT8

> Viết bù 06/10/2026. Code: `ai-service/src/ai/db/session.py`, `notebooks/06_export_onnx.py`.
> Quyết định: ADR-0001, ADR-0016, ADR-0021 (cổng parity trượt).

## "Phải giải thích được"

**Vì sao `SET LOCAL` chứ không phải `SET`? Bỏ `LOCAL` thì hỏng ở đâu, và vì sao test vẫn có thể xanh?**
- `SET app.tenant_id = A` dính vào **kết nối** và theo kết nối trả về pool. Request sau của tenant B
  mượn đúng kết nối đó mà quên đặt lại thì đọc được dữ liệu của A. Không exception, không log.
- `SET LOCAL` (trong code là `set_config(..., true)`, vì `SET LOCAL` không nhận bind parameter)
  **chết theo transaction**, nên không bao giờ theo kết nối về pool.
- **Vì sao test vẫn xanh nếu bỏ `LOCAL`:** lỗi chỉ lộ khi một kết nối đã dùng cho tenant A được
  **tái sử dụng** cho tenant B **mà không** đặt lại. Test thường làm khác:
  - mỗi test một kết nối mới;
  - hoặc luôn đặt tenant trước mỗi truy vấn;
  - hoặc chạy tuần tự một tenant.

  Đúng như vậy trong repo: viết `SET` thay `SET LOCAL` trong `session.py` thì ba ca (a) (b) (c) của
  `tests/integration/test_rls.py` **vẫn xanh**, vì ca (b) chạy trên một kết nối mới. Test bắt được
  lỗi này là **ca (d)** `test_pool_khong_ro_tenant_sang_luot_sau`:
  - `pool_size=1` buộc hai lượt dùng chung đúng một kết nối;
  - lượt 1 đặt tenant;
  - lượt 2 không đặt và phải nổ 42501. Dùng `SET` thì biến còn trên kết nối, không nổ, và test đỏ.

**Vì sao runtime dùng `ai_app` mà không dùng `crm_owner`, dù `crm_owner` cũng bị `FORCE RLS`?**
`FORCE` chỉ kéo chủ bảng vào RLS. Nó **không** thắng được superuser hay `BYPASSRLS`, mà `crm_owner`
có cả hai. Xem ghi chú Ngày 1.

**Lượng tử hoá INT8 per-channel khác per-tensor ở chỗ nào, và vì sao ngưỡng là 0,995?**
- **Per-tensor:** một thang (scale) cho cả ma trận.
- **Per-channel:** mỗi kênh đầu ra (mỗi cột trọng số) một thang riêng. Các kênh có dải giá trị rất
  khác nhau, nên per-channel giữ độ phân giải tốt hơn.
- Notebook 06 lượng tử hoá **trọng số per-channel**. Nhưng `quantize_dynamic` lượng tử hoá
  **activation per-tensor ngay lúc chạy**, và đó mới là nguồn sai số chính (ADR-0021: giữ bảng nhúng
  fp32 cũng không cải thiện).
- **0,995** là ngưỡng của `notebooks/README.md`: cosine fp32 ↔ INT8 trên 500 mẫu. Ý tưởng là đủ cao
  để thứ hạng láng giềng gần như không đổi. Bản thân con số là **quy ước**, không suy ra từ lý thuyết.
- Vì vậy khi trượt (`mean` 0,98476), ADR-0021 phân xử bằng thứ cần thật là **Recall@5 trên bộ vàng**,
  không hạ ngưỡng.

## Cập nhật 06/10 — liên quan trực tiếp

Activation per-tensor tính trên **cả lô**, nên cùng một câu nhúng chung lô khác nhúng riêng
(~0,985). Notebook đo parity theo lô có pad. Có thể một phần "trượt parity" là do cách đo. Ngày 7 đo
lại ở lô 1. Chi tiết: ghi chú Ngày 6 mục 3.
