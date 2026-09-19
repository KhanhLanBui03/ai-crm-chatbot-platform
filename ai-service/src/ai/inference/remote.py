"""Backend ``remote`` + circuit breaker — Master Plan §3.8.

MA TRẬN SUY GIẢM — §3.8.1, kiểm đủ ba trường hợp ở Ngày 34
------------------------------------------------------------
Nguyên tắc: tầng suy luận chết thì **suy giảm**, không trả 5xx cho người dùng.

    ai-embed chết    → chuyển sang truy hồi CHỈ TỪ KHOÁ (sparse-only),
                       đánh cờ degraded=true. Vẫn trả lời được.
    ai-rerank chết   → bỏ bước rerank, vẫn trả lời bằng thứ hạng RRF.
    ai-classify chết → /ready trả 503, KHÔNG nhận yêu cầu mới.

``ai-classify`` là ngoại lệ vì nó chạy 100% lượt chat và là cửa vào của guardrails
— không có nó thì không còn lớp kiểm duyệt nào, nên fail-closed là đúng.

CIRCUIT BREAKER — ba trạng thái, cho cả ba client suy luận lẫn LLM API
----------------------------------------------------------------------
    closed → open → half-open → closed

    Retry:     429 · 5xx · timeout
    KHÔNG retry: 400 · 401 · 422   (hỏng ở phía mình, thử lại cũng hỏng)

Chuỗi timeout phải TĂNG DẦN từ trong ra ngoài (§3.10.2): client suy luận < tổng
ngân sách của ai-service < idle_timeout của ALB (120 s). Đặt ngược thì ALB cắt
kết nối trước khi ứng dụng kịp trả lỗi tử tế, và log không cho biết gì.

TODO: ``CircuitBreaker`` ba trạng thái + đếm lỗi theo cửa sổ trượt.
TODO: ``RemoteInferenceClient`` dùng httpx.AsyncClient, timeout theo từng vai trò.
TODO: ghi ``degraded=true`` vào telemetry mỗi lần suy giảm (UC039).
"""
