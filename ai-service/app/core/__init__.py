"""Tiện ích dùng chung: log JSON có Trace ID, ngoại lệ, số liệu Prometheus.

Trace ID lấy từ header X-Trace-Id do gateway gắn, đưa vào mọi dòng log và truyền tiếp
sang mọi lời gọi đi ra — kể cả header của bản tin Kafka (kế hoạch mục 4.5).

Chỉ số tối thiểu: độ trễ theo từng chặng, số lượt gọi mô hình ngôn ngữ, tỉ lệ lỗi tool,
độ trễ tiêu thụ Kafka.
"""
