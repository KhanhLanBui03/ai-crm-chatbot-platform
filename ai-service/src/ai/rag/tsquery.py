"""Dựng truy vấn cho làn từ khoá — UC023 chặng 7 (BM25). [PRODUCTION]

``build_tsquery`` biến câu hỏi của khách thành chuỗi cú pháp ``tsquery``. Nơi dùng::

    WHERE content_segmented @@ to_tsquery('simple', knowledge.f_unaccent(:q))

``content_segmented`` là cột GENERATED ``to_tsvector('simple', knowledge.f_unaccent(content))``
(V210). Hai đầu của làn từ khoá vì thế đi qua CÙNG ``normalize_vi`` (Python), CÙNG
``knowledge.f_unaccent`` (SQL) và CÙNG bộ phân tích từ của Postgres — không bước nào có hai
bản cài đặt.

HAI QUYẾT ĐỊNH
--------------
**1. ``<->`` bên trong một từ ghép.** Chỉ mục lưu theo ÂM TIẾT: ``Chính sách`` thành
``'chinh':1 'sach':2``. Tìm ``chinh & sach`` thì một đoạn có "sách" ở đầu trang và "chính" ở
cuối trang cũng khớp. ``chinh <-> sach`` đòi hai âm tiết LIỀN NHAU, đúng thứ tự — tức đúng là
từ "chính sách". ``pyvi`` cho biết âm tiết nào ghép thành từ (``Chính_sách``).

**2. ``|`` (OR) giữa các từ, không phải ``&`` (AND).** Khách gõ "chính sách đổi trả laptop"
trong khi kho không có chữ "laptop": AND trả về RỖNG vì một từ thừa, OR vẫn trả các đoạn về
chính sách đổi trả — đoạn khớp nhiều từ hơn xếp cao hơn. Làn này là một trong hai nguồn của RRF
(ADR-0006), nên việc của nó là KHÔNG BỎ SÓT; lọc nhiễu đã có làn vector và RRF lo.

GIỚI HẠN ĐÃ BIẾT — ghi vào báo cáo, không phải lỗi
--------------------------------------------------
- Câu KHÔNG DẤU mất lợi thế của ``<->``: pyvi không nhận ra "chinh sach" là một từ, nên câu đó
  thành ``chinh | sach`` — vẫn tìm được, nhưng kém chính xác hơn câu có dấu.
- ``ts_rank`` KHÔNG có IDF: từ phổ biến ("và", "có") đóng góp ngang từ hiếm. Chấp nhận được vì
  RRF chỉ dùng thứ hạng; đo lại ở Ngày 6 khi dựng hybrid search.
"""

import functools
import re

from src.ai.rag.chuan_hoa import normalize_vi

# Mã sản phẩm, số có dấu phân cách, ngày tháng: ``NH-TL256I``, ``6.790.000``, ``1.500.000đ``,
# ``10/2026``. pyvi cắt chúng vụn (``NH-TL256I`` → ``NH - TL256I``), mất dấu liên kết giữa
# các phần. Tách chúng ra TRƯỚC pyvi và đưa nguyên cho Postgres: bộ phân tích của Postgres
# chính là bộ đã tách ``content`` lúc ghi, nên hai đầu tách giống nhau (``'nh-tl256i'``,
# ``'6.790.000'``) mà Python không phải bắt chước quy tắc của nó.
#
# Chỉ gồm ``\w`` và ``- . /`` — không ký tự nào trong đó là toán tử tsquery.
_MA_VA_SO = re.compile(r"\w+(?:[-./]\w+)+")

_AM_TIET = re.compile(r"\w+")


@functools.cache
def _tach_tu():
    """Nạp pyvi đúng một lần, lúc CẦN.

    Không import ở đầu module: đo trên máy dev, lần đầu nạp (sklearn + mô hình CRF) mất ~21 s
    khi bộ đệm đĩa còn lạnh, các lần sau ~1,6 s. Import ở đầu module thì mọi thứ import
    ``tsquery`` (kể cả test không cần tách từ) đều chịu chi phí đó. Ngày 8: gọi hàm này một
    lần trong ``lifespan`` để lượt chat đầu tiên không phải chờ.
    """
    from pyvi import ViTokenizer

    return ViTokenizer.tokenize


def _toan_hang_tu_doan_chu(doan: str) -> list[str]:
    """Toán hạng tsquery từ một đoạn chữ thường (không có mã/số): mỗi từ của pyvi một toán hạng."""
    toan_hang = []
    for tu in _tach_tu()(doan).split():
        # ``_`` nối âm tiết của từ ghép. ``\w+`` vừa tách âm tiết vừa LỌC SẠCH mọi ký tự có
        # nghĩa trong cú pháp tsquery (& | ! ( ) : * < > ') — câu hỏi của khách là dữ liệu
        # không đáng tin, không được lọt vào làm toán tử.
        am_tiet = _AM_TIET.findall(tu.replace("_", " "))
        if not am_tiet:
            continue  # dấu câu đứng riêng
        if len(am_tiet) == 1:
            toan_hang.append(am_tiet[0])
        else:
            toan_hang.append("(" + " <-> ".join(am_tiet) + ")")
    return toan_hang


def build_tsquery(cau_hoi: str) -> str | None:
    """Chuỗi tsquery cho ``to_tsquery('simple', knowledge.f_unaccent(:q))``, hoặc ``None``.

    ``None`` khi câu hỏi không còn âm tiết nào (rỗng, chỉ dấu câu) — nơi gọi bỏ qua làn từ
    khoá thay vì gửi một tsquery rỗng.

    Ví dụ::

        "Chính sách đổi trả laptop?"  →  "(chính <-> sách) | đổi | trả | laptop"
        "chinh sach doi tra"          →  "chinh | sach | doi | tra"
        "NH-TL256I giá bao nhiêu"     →  "nh-tl256i | giá | (bao <-> nhiêu)"

    Chữ thường hoá ở đây chỉ để bỏ trùng (``Giá`` và ``giá`` là một toán hạng); Postgres cũng
    hạ chữ thường khi phân tích, nên kết quả khớp không đổi. KHÔNG bỏ dấu ở đây — việc đó của
    ``knowledge.f_unaccent`` trong SQL, cùng hàm với phía ghi.
    """
    cau_hoi = normalize_vi(cau_hoi).lower()

    toan_hang: list[str] = []
    vi_tri = 0
    for ma in _MA_VA_SO.finditer(cau_hoi):
        toan_hang += _toan_hang_tu_doan_chu(cau_hoi[vi_tri : ma.start()])
        toan_hang.append(ma.group(0))
        vi_tri = ma.end()
    toan_hang += _toan_hang_tu_doan_chu(cau_hoi[vi_tri:])

    # Bỏ trùng, giữ thứ tự xuất hiện — chuỗi ổn định thì test và log đọc được.
    duy_nhat = list(dict.fromkeys(toan_hang))
    return " | ".join(duy_nhat) if duy_nhat else None
