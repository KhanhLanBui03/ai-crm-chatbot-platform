// [PRODUCTION] Giữ token phiên qua nhiều lần tải trang (UC009 11.3–11.4).
// Khoá theo widgetKey: một trình duyệt ghé hai website dùng hai widget khác nhau thì hai phiên riêng.
// localStorage có thể bị chặn (chế độ riêng tư, chặn cookie bên thứ ba) — khi đó vẫn chat được,
// chỉ là tải lại trang sẽ thành khách mới.

const tienTo = 'crm-ai-widget:'

export function docToken(widgetKey: string): string | null {
  try {
    return localStorage.getItem(tienTo + widgetKey)
  } catch {
    return null
  }
}

export function luuToken(widgetKey: string, token: string): void {
  try {
    localStorage.setItem(tienTo + widgetKey, token)
  } catch {
    /* bỏ qua — xem chú thích đầu tệp */
  }
}

export function xoaToken(widgetKey: string): void {
  try {
    localStorage.removeItem(tienTo + widgetKey)
  } catch {
    /* bỏ qua */
  }
}
