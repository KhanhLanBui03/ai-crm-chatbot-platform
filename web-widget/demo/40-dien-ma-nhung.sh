#!/bin/sh
# [R&D] Điền mã nhúng vào trang "Cửa hàng Demo" lúc container khởi động — tương đương doanh nghiệp
# dán đoạn <script> lấy từ dashboard. Ảnh nginx tự chạy mọi script trong /docker-entrypoint.d/.
#
# Chỉ thay ĐÚNG ba biến của mã nhúng (envsubst có danh sách) — để các ký tự $ khác trong trang không
# bị nuốt mất. Cả ba giá trị nằm trong thuộc tính HTML nên được kiểm trước: giá trị lạ thì DỪNG
# container thay vì sinh ra một trang bị chèn mã.
set -eu

: "${WIDGET_SCRIPT_URL:=http://localhost:5174/widget.js}"
: "${WIDGET_PUBLIC_API_URL:=http://localhost:8080}"
: "${DEMO_WIDGET_KEY:=wk_chua_dat_khoa_demo}"
export WIDGET_SCRIPT_URL WIDGET_PUBLIC_API_URL DEMO_WIDGET_KEY

loi() { echo "$1" >&2; exit 1; }

# Khoá công khai chỉ gồm chữ thường, số, gạch dưới
case "$DEMO_WIDGET_KEY" in
  *[!a-z0-9_]*) loi "DEMO_WIDGET_KEY không hợp lệ: chỉ nhận a-z, 0-9, _" ;;
esac

# Hai địa chỉ: phải là http(s), không chứa ký tự phá thẻ (nháy kép, nháy đơn, < > và khoảng trắng)
for url in "$WIDGET_SCRIPT_URL" "$WIDGET_PUBLIC_API_URL"; do
  case "$url" in
    http://*|https://*) ;;
    *) loi "Địa chỉ phải bắt đầu bằng http:// hoặc https://: $url" ;;
  esac
  for c in '"' "'" '<' '>' ' '; do
    case "$url" in
      *"$c"*) loi "Địa chỉ chứa ký tự không hợp lệ: $url" ;;
    esac
  done
done

envsubst '${WIDGET_SCRIPT_URL} ${WIDGET_PUBLIC_API_URL} ${DEMO_WIDGET_KEY}' \
  < /usr/share/nginx/demo/index.template.html \
  > /usr/share/nginx/demo/index.html
echo "Cửa hàng Demo: widget ${WIDGET_SCRIPT_URL}, API ${WIDGET_PUBLIC_API_URL}, khoá ${DEMO_WIDGET_KEY}"
