package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.OutboxEvent;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * Bảng không có RLS (V112 mục 4). Chỉ hai đường được chạm: ghi thêm từ service trong transaction
 * nghiệp vụ, và job phát ({@code platform/messaging/OutboxPublisher}) — không truy vấn theo yêu
 * cầu người dùng.
 */
@Repository
public interface OutboxEventRepository extends JpaRepository<OutboxEvent, Long> {

    /**
     * Giành quyền làm job phát duy nhất tới hết transaction. {@code false} = một instance
     * java-core khác đang phát lô của nó.
     *
     * <p>Khoá cả job chứ không {@code FOR UPDATE SKIP LOCKED} từng dòng: SKIP LOCKED cho hai
     * instance chia nhau các dòng, instance thứ hai có thể phát sự kiện 2 của một tenant trong
     * lúc instance đầu còn giữ sự kiện 1 — thứ tự trong tenant, thứ mà khoá phân vùng
     * {@code tenant_id} sinh ra để giữ, vỡ ngay ở nguồn. Một job phát lô 100 mỗi 500 ms là đủ
     * xa so với lưu lượng của SME.
     *
     * <p>Hai số nguyên: 110 = migration tạo bảng (V110), 1 = job phát. Không va với khoá
     * {@code (18, hashtext(…))} mà ai-service dùng để cấp version tài liệu.
     */
    @Query(nativeQuery = true, value = "SELECT pg_try_advisory_xact_lock(110, 1)")
    boolean tryLockPublisher();

    /** Lô sự kiện chưa phát, cũ trước. Chỉ mục bộ phận {@code ix_outbox_unpublished} phủ điều kiện lọc. */
    @Query(nativeQuery = true, value = """
            SELECT * FROM platform.outbox_events
             WHERE published_at IS NULL
             ORDER BY id
             LIMIT :limit
            """)
    List<OutboxEvent> findUnpublished(@Param("limit") int limit);
}
