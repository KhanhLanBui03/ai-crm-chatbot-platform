-- V216 — Độ trễ từng chặng của MỘT lượt xử lý. UC023 bước 10 · UC027 bước 8 · SCR036 (đợt GD2).
--
-- Không sửa V201–V215: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.
--
-- Trước V216, độ trễ từng chặng chỉ đi theo sự kiện ai.turn.completed sang
-- analytics.metrics_daily (java-core cộng dồn THEO NGÀY, cột stage_latency của V137). Số tổng theo
-- ngày trả lời được "trung bình chặng nào chậm", nhưng không trả lời được câu màn "Giám sát lượt xử
-- lý" phải trả lời: "lượt 5,6 giây NÀY chậm ở chặng nào". Nên ghi thêm vào chính dòng của lượt.
--
-- Khoá là tên chặng có hậu tố _ms, đúng như TurnRecord.latency_breakdown: guard_ms · classify_ms ·
-- embed_ms · retrieve_ms · rerank_ms · generate_ms · postguard_ms … Không chuẩn hoá khoá ở đây —
-- gộp chặng cho giao diện (embed + retrieve → "Truy hồi") là việc của java-core, cùng một luật với
-- AiPerformanceService.chang(), để hai màn cùng gọi một chặng bằng cùng một tên.
--
-- Lượt ghi trước V216 mang '{}' — giao diện không vẽ thanh độ trễ cho chúng, đúng hơn là vẽ số 0.
-- ADD COLUMN kế thừa quyền của bảng (V206): ai_app ghi và đọc được, không cần GRANT thêm.

ALTER TABLE ai.ai_interactions
    ADD COLUMN latency_breakdown jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(latency_breakdown) = 'object');

COMMENT ON COLUMN ai.ai_interactions.latency_breakdown IS
    'Độ trễ từng chặng của lượt (ms): {"guard_ms": 3, "retrieve_ms": 41, "generate_ms": 1980, …}. '
    'Cùng số với ChatResponse.latency_breakdown và sự kiện ai.turn.completed (trừ total_ms — đã ở '
    'latency_ms). Nguồn của LuotXuLyAi.latencyBreakdown (SCR036).';
