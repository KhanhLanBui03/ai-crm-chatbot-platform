"""Chuẩn hoá văn bản tiếng Việt — MỘT hàm cho cả lúc nạp lẫn lúc truy vấn. [PRODUCTION]

UC019 chặng 2 (``src/ai/rag/__init__.py``). ``normalize_vi`` là hàm DUY NHẤT được gọi ở hai
đầu: ``ingest/`` gọi trên nội dung tài liệu trước khi chia đoạn, ``tsquery.build_tsquery``
(và sau này node ``retrieve``) gọi trên câu hỏi của khách.

VÌ SAO PHẢI LÀ MỘT HÀM
----------------------
Hai hàm "gần giống nhau" là lỗi thầm lặng: không có exception nào, chỉ có recall tụt. Ví dụ
thật trong ``data/kb_samples/huong-dan-bao-quan-noi-chien.txt``: tài liệu viết ``thuỷ tinh``
ở dạng NFD (chữ ``u`` + dấu hỏi rời thành hai code point). Nếu phía nạp chuẩn hoá NFC mà phía
hỏi quên, câu hỏi ``thủy tinh`` gõ bằng Unikey (NFC, dấu kiểu cũ) và đoạn văn khác nhau từng
byte — vector nhúng lệch, còn làn từ khoá thì không khớp. Không có dòng log nào báo điều đó.

CỐ Ý KHÔNG LÀM Ở ĐÂY
--------------------
- **Không hạ chữ thường, không bỏ dấu.** Kết quả của hàm này còn được lưu làm ``content``, hiển
  thị trong trích dẫn và đưa vào mô hình nhúng — bỏ dấu ở đây là làm hỏng cả ba. Hạ chữ thường
  và bỏ dấu cho làn từ khoá nằm ở SQL: ``knowledge.f_unaccent`` + ``to_tsvector('simple', …)``
  (V210). Hai đầu vì thế cùng đi qua đúng MỘT hàm Python và đúng MỘT hàm SQL.
- **Không sửa chính tả, không đổi i/y** (``quý``/``quí``). Đó là quyết định ngôn ngữ, không
  phải chuẩn hoá mã hoá.
"""

import re
import unicodedata

# Dấu thanh tiếng Việt ở dạng tổ hợp rời (NFD): huyền, sắc, ngã, hỏi, nặng.
_DAU_THANH = "\u0300\u0301\u0303\u0309\u0323"

# Kiểu đặt dấu MỚI (``hoà``, ``khoẻ``, ``thuỷ``) → kiểu CŨ (``hòa``, ``khỏe``, ``thủy``).
# Chọn kiểu cũ vì đó là mặc định của Unikey/bàn phím điện thoại, tức cách khách thực sự gõ.
#
# Chỉ áp cho ``oa``/``oe``/``uy`` ở CUỐI âm tiết (sau dấu thanh không còn chữ cái hay dấu
# phụ nào): ``hoàng``, ``hoặc``, ``khuỷu`` đặt dấu giống nhau ở cả hai kiểu nên không được đụng.
# ``(?![\w\u0300-\u036f])`` chặn cả hai: chữ cái theo sau (``hoàng``) và dấu phụ thứ hai
# (``hoặc`` = a + dấu nặng + dấu trăng). ``(?<![qQ])``: trong ``quý`` chữ ``u`` thuộc phụ âm
# ``qu``, dấu đặt trên ``y`` là đúng ở cả hai kiểu.
_DAU_KIEU_MOI = re.compile(
    rf"(?<![qQ])([oO])([aAeE])([{_DAU_THANH}])(?![\w\u0300-\u036f])"
    rf"|(?<![qQ])([uU])([yY])([{_DAU_THANH}])(?![\w\u0300-\u036f])"
)

# Chữ cái thường lặp từ 3 lần trở lên — kiểu gõ kéo dài trong tin nhắn (``đẹppppp``).
# Tiếng Việt không có từ nào chứa ba chữ giống nhau liền nhau, NHƯNG tài liệu thì có:
# - ``w f j z`` không thuộc bảng chữ cái tiếng Việt, gặp trong ``www``, mã, tên riêng nước ngoài;
# - ``i v x l c d m`` là chữ số La Mã (``(iii)``, ``xxx``) — gộp là đổi nghĩa mục liệt kê.
# Chữ HOA không bị đụng vì cùng lý do (``Chương III``, cỡ ``XXXL``). Chữ số không bao giờ bị
# đụng: ``1.000.000đ`` phải giữ nguyên từng số 0.
#
# Chạy trên dạng NFD để so CHỮ GỐC: ``quáaaa`` ở NFD là ``a`` + dấu sắc + ``aaa`` — cả chuỗi
# là một chữ ``a`` kéo dài, gộp về ``quá``. Chạy trên NFC thì ``á`` và ``a`` là hai ký tự khác
# nhau và kết quả thành ``quáa``.
_CHU_LAP = re.compile(r"([^\W\d_])([\u0300-\u036f]*)\1{2,}")
_KHONG_GOP = frozenset("wfjzivxlcdm")

_DAU_CAU_LAP = re.compile(r"([!?])\1+")

# Khoảng trắng ngang (mọi Zs: NBSP, en space, …, và tab) — KHÔNG gồm xuống dòng.
_KHOANG_TRANG_NGANG = re.compile(r"[^\S\n]+")
_NHIEU_DONG_TRONG = re.compile(r"\n{3,}")


def _chuyen_dau_ve_kieu_cu(khop: re.Match[str]) -> str:
    if khop.group(1):
        return khop.group(1) + khop.group(3) + khop.group(2)
    return khop.group(4) + khop.group(6) + khop.group(5)


def _gop_chu_lap(khop: re.Match[str]) -> str:
    chu = khop.group(1)
    if chu.islower() and chu not in _KHONG_GOP:
        return chu + khop.group(2)
    return khop.group(0)


def _bo_ky_tu_vo_hinh(van_ban: str) -> str:
    """Bỏ ký tự định dạng vô hình (Cf) và ký tự điều khiển (Cc), trừ ``\\n`` và ``\\t``.

    Cf gồm dấu cách rộng bằng không U+200B, U+200C/200D, U+2060, BOM U+FEFF, gạch nối mềm
    U+00AD, ký tự đảo chiều U+202A–202E. Chúng không hiện ra nhưng tách đôi một từ thành hai
    chuỗi khác nhau — ``NỒI\\u200b`` và ``NỒI`` không bao giờ khớp nhau.
    """
    return "".join(c for c in van_ban if c in "\n\t" or unicodedata.category(c) not in ("Cf", "Cc"))


def normalize_vi(van_ban: str) -> str:
    """Chuẩn hoá mã hoá và hình thức của văn bản tiếng Việt. Luỹ đẳng: ``f(f(x)) == f(x)``.

    Bốn bước, THỨ TỰ CÓ Ý NGHĨA:

    1. Xuống dòng ``\\r\\n``/``\\r`` → ``\\n``; bỏ ký tự vô hình và ký tự điều khiển. Làm TRƯỚC
       NFC: một U+200B chen giữa chữ cái và dấu rời sẽ chặn NFC ghép chúng lại.
    2. NFD → gộp chữ lặp → đưa dấu ``oa``/``oe``/``uy`` về kiểu cũ → NFC. Cả hai việc giữa cần
       dấu ở dạng RỜI: gộp chữ lặp so chữ gốc, dời dấu thì dời một code point. Xong mới ghép
       lại thành NFC — dạng Unikey và trình duyệt gửi lên.
    3. ``!!``/``??`` → một dấu.
    4. Khoảng trắng: mọi khoảng trắng ngang (NBSP, tab, …) thành một dấu cách, bỏ khoảng trắng
       đầu/cuối dòng, tối đa MỘT dòng trống liên tiếp. GIỮ ``\\n`` — bước chia đoạn cần ranh
       giới dòng và đoạn văn.
    """
    van_ban = van_ban.replace("\r\n", "\n").replace("\r", "\n")
    van_ban = _bo_ky_tu_vo_hinh(van_ban)

    van_ban = unicodedata.normalize("NFD", van_ban)
    van_ban = _CHU_LAP.sub(_gop_chu_lap, van_ban)
    van_ban = _DAU_KIEU_MOI.sub(_chuyen_dau_ve_kieu_cu, van_ban)
    van_ban = unicodedata.normalize("NFC", van_ban)

    van_ban = _DAU_CAU_LAP.sub(r"\1", van_ban)
    van_ban = _KHOANG_TRANG_NGANG.sub(" ", van_ban)
    van_ban = "\n".join(dong.strip() for dong in van_ban.split("\n"))
    van_ban = _NHIEU_DONG_TRONG.sub("\n\n", van_ban)

    return van_ban.strip()
