"""Ba vai trò của image ``ai-inference``, chọn bằng ``MODEL_ROLE`` (§3.9.1).

    embed.py     UC019, UC023   encoder      cấp M hoặc L   ~45% lượt chat + luồng index
    rerank.py    UC023          cross-encoder cấp S hoặc M  ~30-40% nhánh RAG
    classify.py  UC022, UC030   router+scorer cấp S         100% lượt chat

Bảng phân bổ chính thức: Master Plan §3.2.1. Không model nào nằm trong ``ai-service``,
bất kể kích thước — kể cả lead scorer chỉ 2 MB (lý do ở §3.2.2).
"""
