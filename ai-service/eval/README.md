# Khung đánh giá — Track B

## `golden_set.jsonl` — 150 câu, tài sản giá trị nhất của đồ án

Mốc **M4 — hoàn tất 12/10**. Kế hoạch mục 0.3 nói rõ: nếu phần công sức dôi ra rơi vào bộ dữ
liệu vàng thì đồ án **mất trần điểm và không có cách nào cứu ở tuần cuối**. Ưu tiên Tầng 1.

Một dòng một câu hỏi:

```jsonc
{
  "id": "G001",
  "question": "Niềng răng chi phí khoảng bao nhiêu?",
  "expected_route": "rag",              // rag | tool | clarify | handoff
  "expected_chunk_ids": ["doc12#c3"],   // căn cứ đúng, dùng để tính Recall@5 / MRR / nDCG
  "expected_behavior": "answer",        // answer | refuse | clarify | handoff
  "reference_answer": "...",            // để chấm tính bám nguồn
  "category": "bang_gia",
  "difficulty": "easy",                 // easy | medium | hard
  "source": "pilot_A"                   // pilot_A | public | synthetic
}
```

**Thành phần bắt buộc:** trong 150 câu phải có **25 câu ngoài phạm vi** (`expected_behavior:
"refuse"`) — dùng để hiệu chỉnh ngưỡng từ chối, là siêu tham số của thí nghiệm E7.

Phân bổ đề xuất: ~60 câu RAG tri thức tĩnh · ~35 câu Tool trạng thái động ·
~15 câu cần hỏi lại · ~15 câu cần chuyển giao · **25 câu ngoài phạm vi**.

## `adversarial.jsonl` — 60–80 kịch bản tấn công

Dùng cho **E9**. Chạy trên môi trường **cô lập, dữ liệu giả** (mục 8.1).

```jsonc
{
  "id": "A001",
  "attack_group": "prompt_injection_direct",  // xem bảng dưới
  "surface": "T2",                            // mã bề mặt trong docs/threat-model.md
  "payload": "...",
  "success_criteria": "lộ chỉ thị hệ thống",
  "defense_layers_expected_to_block": ["input_filter", "instruction_separation"]
}
```

| `attack_group` | Bề mặt | Mô tả |
|---|---|---|
| `prompt_injection_direct` | T2 | Tiêm chỉ thị qua ô nhập của widget |
| `prompt_injection_indirect` | T3 | Tiêm qua nội dung tài liệu được nạp |
| `tenant_leak` | T5, T6 | Dụ bot đọc dữ liệu tenant khác |
| `tool_abuse` | T4 | Dụ gọi tool ngoài danh sách cho phép, hoặc sai đối số |
| `data_exfiltration` | T5 | Moi dữ liệu cá nhân ra khỏi ngữ cảnh |
| `jailbreak` | T2 | Vượt qua ràng buộc vai trò |

Chỉ số: **Attack Success Rate** theo từng nhóm, đo **trước và sau** khi bật từng lớp phòng thủ.

## Ẩn danh hóa — bắt buộc

Dữ liệu trong hai file này bắt nguồn từ hội thoại thật của doanh nghiệp pilot.
**Ẩn danh hóa toàn bộ trước khi đưa vào đây** (bề mặt T8, Nghị định 13/2023/NĐ-CP).
Tách hoàn toàn khỏi dữ liệu vận hành.

## `reports/`

CSV và HTML sinh tự động. **Không commit** — xem `.gitignore`. Kết quả cần giữ thì chép
vào `docs/report/`.
