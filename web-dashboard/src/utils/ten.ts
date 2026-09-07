/**
 * Viết tắt tên người: **họ + tên**, không phải hai từ cuối.
 *
 * Tên tiếng Việt có tên đệm, nên lấy hai từ cuối sẽ ra "Trần Quốc Dũng" → "QD" và
 * "Phạm Hoài An" → "HA" — đọc lên không nhận ra ai. Lấy từ đầu và từ cuối cho "TD" và "PA",
 * đúng cách người Việt viết tắt tên.
 */
export function chuCaiDau(hoTen: string): string {
  const tu = hoTen.trim().split(/\s+/).filter(Boolean)
  if (tu.length === 0) return '?'
  if (tu.length === 1) return tu[0].slice(0, 2).toUpperCase()
  return (tu[0][0] + tu[tu.length - 1][0]).toUpperCase()
}

/** Tiền tố loại hình doanh nghiệp — không mang thông tin nhận dạng nên bỏ khi viết tắt. */
const TIEN_TO = new Set([
  'công', 'ty', 'cty', 'tnhh', 'mtv', 'cổ', 'phần', 'cp', 'doanh', 'nghiệp',
  'tập', 'đoàn', 'hợp', 'tác', 'xã', 'chi', 'nhánh', 'tư', 'nhân',
])

/**
 * Viết tắt tên doanh nghiệp cho ô nhận diện ở sidebar.
 *
 * Cắt thẳng hai ký tự đầu sẽ ra "Công ty TNHH Cát Tường" → "CÔ", vô nghĩa. Bỏ tiền tố loại
 * hình trước rồi mới lấy chữ cái đầu của phần tên riêng → "CT".
 */
export function vietTatDoanhNghiep(ten: string): string {
  const tu = ten.trim().split(/\s+/).filter(Boolean)
  const rieng = tu.filter((t) => !TIEN_TO.has(t.toLowerCase().replace(/[^\p{L}]/gu, '')))
  const nguon = rieng.length > 0 ? rieng : tu
  if (nguon.length === 0) return '?'
  if (nguon.length === 1) return nguon[0].slice(0, 2).toUpperCase()
  return (nguon[0][0] + nguon[nguon.length - 1][0]).toUpperCase()
}
