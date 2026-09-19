"""``make_session`` — ghim số luồng cho ONNX Runtime (Master Plan §5.4).

BẪY LỚN NHẤT KHI CHẠY ONNX TRÊN KUBERNETES
-------------------------------------------
ONNX Runtime đọc **số CPU của NODE**, không đọc ``limits.cpu`` của container. Trên
một node 16 vCPU, pod được cấp 2 vCPU vẫn tạo 16 luồng. Kết quả: 16 luồng tranh nhau
2 vCPU, context-switch liên tục, p95 xấu hơn hẳn so với chạy 2 luồng — và không có
gì trong log chỉ ra nguyên nhân.

Vì vậy **luôn đặt tường minh**, không bao giờ để mặc định::

    sess_options.intra_op_num_threads = <đúng limits.cpu>
    sess_options.inter_op_num_threads = 1

``inter_op = 1`` vì các model ở đây chạy tuần tự một đồ thị; song song ở mức
inter-op chỉ thêm chi phí điều phối mà không có nhánh nào để chạy song song.

CẤU HÌNH ĐỘNG THEO CẤP MODEL — §5.4, bảng bắt buộc áp dụng
-----------------------------------------------------------
    requests.cpu == limits.cpu      → QoS Guaranteed, tránh CFS throttling
    OMP_NUM_THREADS == limits.cpu   → bất biến 3 kiểm ở /ready

Fix cứng một con số là sai theo cả hai hướng: model nhỏ thì thừa luồng (overhead),
model lớn thì thiếu luồng (vượt ngân sách p95). Cấp S/M/L chốt ở Ngày 21 dựa trên
bảng benchmark ``bench_cpu.py``, không chốt bằng cảm tính.

Bằng chứng phải có trong báo cáo (Ngày 46): chạy ``bench_cpu.py`` HAI LẦN trong pod
— một lần ghim đúng số luồng, một lần để mặc định — rồi đưa bảng chênh lệch p95 vào.

TODO: ``make_session(model_path, num_threads)`` trả ``onnxruntime.InferenceSession``.
TODO: đọc ``limits.cpu`` từ cgroup thay vì tin ``os.cpu_count()``.
"""
