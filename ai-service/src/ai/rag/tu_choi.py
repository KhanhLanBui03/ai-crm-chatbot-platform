"""[PRODUCTION] Từ chối khi không đủ căn cứ — UC025, kế hoạch Ngày 10 (``search_or_abstain``).

Bốn lý do (CHECK ``refusal_reason`` của V204), mỗi lý do sinh ra ở ĐÚNG MỘT chỗ trong đường ống —
đặc tả UC025 yêu cầu phân biệt ngay tại chỗ sinh, vì mỗi lý do dẫn tới một hành động khác hẳn
nhau phía doanh nghiệp::

    câu hỏi ─► [SAFETY_PROBE] ─► [OUT_OF_SCOPE_DATA] ─► truy hồi ─► [NOT_COVERED] ─► LLM ─┐
               luật, 0 ms         luật, 0 ms                       sàn cosine            │
    KHONG_DU_CAN_CU / 0 trích dẫn / chỉ nói "chưa có thông tin" ─► [NOT_COVERED] ◄───────┤
                     có trích dẫn nhưng bám nguồn < ngưỡng ─────► [LOW_CONFIDENCE] ◄─────┘

Lý do · sinh ở đâu · nghĩa với doanh nghiệp:

- ``SAFETY_PROBE`` · luật, trước truy hồi · có người dò dữ liệu — xem cờ an toàn, KHÔNG phải
  khoảng trống tri thức.
- ``OUT_OF_SCOPE_DATA`` · luật, trước truy hồi · cần dữ liệu nghiệp vụ thời gian thực — thêm tài
  liệu không giúp được, phải nối công cụ (MCP, đã hoãn).
- ``NOT_COVERED`` · sau truy hồi, hoặc LLM đọc đoạn · kho THIẾU tài liệu — bổ sung (UC018).
- ``LOW_CONFIDENCE`` · sau sinh, hậu kiểm · kho CÓ tài liệu liên quan nhưng câu trả lời không bám
  được — xem lại tài liệu có mơ hồ không.

PHÂN BIỆT (1) NOT_COVERED VÀ (3) LOW_CONFIDENCE — câu hội đồng sẽ hỏi
--------------------------------------------------------------------
Cả hai đều "không trả lời được". Khác ở BẰNG CHỨNG: NOT_COVERED là bằng chứng VẮNG MẶT (không đoạn
nào đủ gần; mô hình đọc đoạn rồi nói không đoạn nào liên quan; hoặc câu trả lời không trích đoạn
nào — mô hình không dựa vào tài liệu); LOW_CONFIDENCE là THẤT BẠI KIỂM CHỨNG — mô hình CÓ trích
đoạn, nhưng hậu kiểm không xác nhận được câu đó nằm trong đoạn. Có trích dẫn hay không là ranh giới
máy kiểm được.

Đặc tả UC023 ghi "LOW_RELEVANCE → độ tin cậy thấp", còn UC025 ghi "không đoạn nào vượt sàn → chưa
có trong tài liệu". Theo UC025 (UC sở hữu quyết định từ chối) và kế hoạch Ngày 10 — độ lệch ghi ở
ADR-0029.

HAI BỘ LUẬT NGHIÊNG VỀ BỎ SÓT
----------------------------
Bắt nhầm là từ chối một câu kho trả lời được. Bỏ sót thì câu hỏi đi tiếp vào RAG — và kho đo có
sẵn chỉ dẫn ("tình trạng còn hàng xem trên website", "theo dõi đơn ở mục Đơn hàng của tôi"), nên
câu bị bỏ sót vẫn nhận một câu trả lời đúng. Vì vậy luật chỉ bắt câu hỏi về MỘT đơn/phiếu/tài
khoản CỤ THỂ (có mã số, có "của em … giao tới đâu", có "kiểm tra giúp em"), không bắt câu hỏi
cách làm ("kiểm tra đơn hàng ở đâu", "điểm tích lũy hết hạn khi nào"). Đo báo nhầm trên 100 câu
có đáp án của bộ vàng và 200 câu người thật của UC022: xem báo cáo Ngày 10.

Luật dò tìm tenant khác DÙNG LẠI nhóm ``DATA_PROBING`` của ``guardrails/injection.py`` (Dev B), chỉ
thêm phần ngoài phạm vi của nó: dữ liệu khách khác và dữ liệu nội bộ cửa hàng.

So khớp trên bản đã bỏ dấu, viết thường — 20% lượt chat là tiếng Việt không dấu.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from src.ai.guardrails import detect_injection
from src.ai.rag.retrieve.hybrid import DoanTimDuoc

NOT_COVERED = "NOT_COVERED"
OUT_OF_SCOPE_DATA = "OUT_OF_SCOPE_DATA"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
SAFETY_PROBE = "SAFETY_PROBE"

# Cờ an toàn của V208 cho hai loại dò tìm.
CROSS_TENANT_PROBE = "CROSS_TENANT_PROBE"
INTERNAL_DATA_PROBE = "INTERNAL_DATA_PROBE"

# Mẫu câu theo lý do — đặc tả UC025 bước 3. Câu an toàn KHÔNG giải thích vì sao: nói rõ câu nào bị
# chặn là cấp thông tin cho người đang dò.
CAU_TU_CHOI: dict[str, str] = {
    NOT_COVERED: (
        "Dạ hiện em chưa tìm thấy thông tin phù hợp trong tài liệu của cửa hàng cho câu hỏi này. "
        "Anh/chị có muốn em chuyển cho nhân viên tư vấn không ạ?"
    ),
    LOW_CONFIDENCE: (
        "Dạ em chưa đủ chắc chắn để trả lời chính xác câu này từ tài liệu của cửa hàng, và em "
        "không muốn trả lời sai cho anh/chị. Anh/chị có muốn em chuyển cho nhân viên tư vấn "
        "không ạ?"
    ),
    OUT_OF_SCOPE_DATA: (
        "Dạ câu này cần tra cứu thông tin cụ thể (đơn hàng, tài khoản, bảo hành hoặc tồn kho) "
        "mà em chưa xem được. Em chuyển anh/chị sang nhân viên hỗ trợ ngay ạ."
    ),
    SAFETY_PROBE: "Dạ em không thể hỗ trợ yêu cầu này ạ.",
}
CAU_CHUYEN_GIAO_LAP_LAI = (
    "Dạ em xin lỗi vì chưa giúp được anh/chị. Em chuyển anh/chị sang nhân viên tư vấn ngay ạ."
)

# Lý do mà lặp lại trong cùng hội thoại thì chuyển nhân viên (UC025 luồng phụ 3.3). SAFETY_PROBE
# không thuộc nhóm này: chuyển kẻ dò tìm cho nhân viên không giúp ai.
LY_DO_TINH_LAP_LAI = frozenset({NOT_COVERED, LOW_CONFIDENCE})


def _bo_dau(van_ban: str) -> str:
    tach = unicodedata.normalize("NFD", van_ban.lower())
    s = "".join(c for c in tach if unicodedata.category(c) != "Mn").replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


_NGUOI_HOI = r"(?:toi|em|minh|tao|tui)"
_MA_SO = r"#?[a-z]{0,4}\d{4,}"

# ── OUT_OF_SCOPE_DATA — một đơn / phiếu / tài khoản / lịch hẹn CỤ THỂ ──────────
_DU_LIEU_NGHIEP_VU = [
    re.compile(p)
    for p in (
        # có mã số: "đơn hàng DH2026…", "đơn 0091234", "phiếu bảo hành số BH778812", "mã vận đơn …"
        rf"\bdon(?:\s+hang)?\s+(?:so\s+|ma\s+)?{_MA_SO}\b",
        rf"\bphieu(?:\s+bao\s+hanh|\s+sua(?:\s+chua)?|\s+giao\s+hang)?\s+(?:so\s+)?{_MA_SO}\b",
        rf"\bma\s+(?:van\s+)?don(?:\s+hang)?\s+(?:la\s+)?{_MA_SO}\b",
        # đơn CỦA NGƯỜI HỎI + hỏi trạng thái: "đơn của em giao tới đâu rồi"
        rf"\bdon(?:\s+hang)?\s+(?:cua\s+)?{_NGUOI_HOI}\b.{{0,40}}\b(?:toi\s+dau|den\s+dau|o\s+dau"
        r"|giao\s+chua|xuat\s+kho|da\s+giao|dang\s+(?:o|giao)|bao\s+gio\s+(?:giao|toi|den)"
        r"|khi\s+nao\s+(?:giao|toi|den))\b",
        # nhờ bot tự tra: "kiểm tra GIÚP em đơn hàng…" — khác "kiểm tra đơn hàng ở đâu" (câu hỏi
        # cách làm, kho trả lời được)
        r"\b(?:kiem\s+tra|tra\s+cuu|check|xem)\s+(?:giup|dum|ho)\s+(?:\w+\s+){0,2}"
        r"(?:don|phieu|bao\s+hanh|diem|tai\s+khoan)\b",
        # điểm/hạng CỦA NGƯỜI HỎI + hỏi con số: "điểm tích lũy của tôi còn bao nhiêu"
        rf"\bdiem(?:\s+tich\s+luy|\s+thuong|\s+thanh\s+vien)?\s+(?:cua\s+)?{_NGUOI_HOI}\b.{{0,30}}"
        r"\b(?:con\s+bao\s+nhieu|duoc\s+bao\s+nhieu|la\s+bao\s+nhieu|con\s+khong|hien\s+(?:tai|co))\b",
        # tài khoản/thành viên kèm số điện thoại cụ thể
        r"\b(?:tai\s+khoan|tk|thanh\s+vien)\b.{0,40}\b(?:\+?84|0)\d{8,10}\b",
        # sửa/bảo hành/lắp xong chưa — hỏi tiến độ một ca cụ thể
        r"\b(?:sua|bao\s+hanh|lap(?:\s+dat)?)\b.{0,40}\bxong\s+chua\b",
        # lịch hẹn tới nhà người hỏi
        r"\b(?:khi\s+nao|bao\s+gio|may\s+gio|ngay\s+nao)\b.{0,40}\b(?:lap|giao|sua|toi|den|qua)\b"
        rf".{{0,30}}\bnha\s+{_NGUOI_HOI}\b",
        # tồn kho một mã sản phẩm / một chi nhánh: "còn tivi NH-TV55 không", "còn hàng ở chi nhánh"
        r"\b(?:con|het)\s+(?:\w+\s+){0,2}[a-z]{2}-[a-z0-9]{2,}\b",
        r"\b(?:con|het)\s+hang\s+(?:o|tai)\s+(?:chi\s+nhanh|cua\s+hang)\b",
        r"\bton\s+kho\b",
    )
]

# ── SAFETY_PROBE — dữ liệu của khách khác, của doanh nghiệp khác, nội bộ cửa hàng ─
_DO_TIM_TENANT_KHAC = [
    re.compile(
        r"\b(?:du\s+lieu|thong\s+tin|tai\s+lieu|khach\s+hang|hoi\s+thoai)\b.{0,40}"
        r"\b(?:cua\s+hang|doanh\s+nghiep|cong\s+ty|shop|tenant|don\s+vi)\s+khac\b"
    ),
]
_DO_TIM_NOI_BO = [
    re.compile(p)
    for p in (
        # ĐÒI liệt kê khách: "cho mình xin danh sách khách hàng đã mua…". Phải có động từ đòi —
        # "cách import danh sách khách hàng từ excel" là câu hỏi cách làm (báo nhầm ở lần đo đầu,
        # câu 32 của tập 200 câu người thật — báo cáo Ngày 10).
        r"\b(?:(?:xin|cho\s+(?:\w+\s+)?xem|gui|cung\s+cap|lay|dua)\s+(?:\w+\s+){0,2}danh\s+sach"
        r"|liet\s+ke|thong\s+ke|xuat)\s+(?:cac\s+|nhung\s+)?(?:thong\s+tin\s+)?"
        r"(?:khach(?:\s+hang)?|nguoi\s+mua)\b",
        # liên lạc của NGƯỜI KHÁC: số nhiều, hoặc "người … khác/trước"
        r"\b(?:so\s+dien\s+thoai|sdt|email|dia\s+chi|thong\s+tin\s+lien\s+he)\s+"
        r"(?:va\s+(?:\w+\s+){1,2})?(?:cua\s+)?(?:(?:nhung|cac)\s+(?:nguoi|khach)"
        r"|(?:nguoi|khach(?:\s+hang)?)\s+(?:\w+\s+){0,3}(?:khac|truoc))\b",
        # số liệu kinh doanh nội bộ
        r"\b(?:doanh\s+thu|loi\s+nhuan|gia\s+nhap|gia\s+von|luong\s+(?:cua\s+)?(?:nhan\s+vien|ky\s+thuat"
        r"|tho|thu\s+ngan))\b",
        # thông tin đăng nhập quản trị
        r"\b(?:mat\s+khau|password|api\s*key|token)\s+(?:\w+\s+){0,2}"
        r"(?:quan\s+tri|admin|he\s+thong|nhan\s+vien|cua\s+(?:shop|cua\s+hang))\b",
    )
]


def phat_hien_do_tim(cau_hoi: str, cau_da_chuan_hoa: str | None = None) -> str | None:
    """Cờ an toàn V208 nếu câu hỏi dò dữ liệu không thuộc về người hỏi, ngược lại ``None``.

    ``cau_da_chuan_hoa`` là câu ``run_turn`` đã đưa qua ``detect_injection`` — truyền vào để nhóm
    ``DATA_PROBING`` của Dev B chạy trên ĐÚNG đầu vào như ở bước 3, không lệch nhau.
    """
    tiem = detect_injection(cau_da_chuan_hoa if cau_da_chuan_hoa is not None else cau_hoi)
    if tiem.matched_category == "DATA_PROBING":
        return CROSS_TENANT_PROBE
    gap = _bo_dau(cau_hoi)
    if any(r.search(gap) for r in _DO_TIM_TENANT_KHAC):
        return CROSS_TENANT_PROBE
    if any(r.search(gap) for r in _DO_TIM_NOI_BO):
        return INTERNAL_DATA_PROBE
    return None


def can_du_lieu_nghiep_vu(cau_hoi: str) -> bool:
    """Câu hỏi về một đơn/phiếu/tài khoản/lịch hẹn cụ thể — tài liệu không trả lời được."""
    gap = _bo_dau(cau_hoi)
    return any(r.search(gap) for r in _DU_LIEU_NGHIEP_VU)


@dataclass(frozen=True, slots=True)
class TuChoiSom:
    """Quyết định từ chối TRƯỚC truy hồi — 0 lượt nhúng, 0 lượt LLM."""

    ly_do: str
    safety_flag: str | None
    chuyen_giao: bool


def kiem_truoc_truy_hoi(cau_hoi: str, cau_da_chuan_hoa: str | None = None) -> TuChoiSom | None:
    """Dò tìm xét TRƯỚC dữ liệu nghiệp vụ: "số điện thoại của khách mua trước tôi" mang cả hai
    dấu hiệu, và đó là dò tìm chứ không phải câu hỏi về đơn của chính mình."""
    co = phat_hien_do_tim(cau_hoi, cau_da_chuan_hoa)
    if co is not None:
        return TuChoiSom(SAFETY_PROBE, co, chuyen_giao=False)
    if can_du_lieu_nghiep_vu(cau_hoi):
        # Đặc tả UC025: lý do thuộc nhóm thiếu dữ liệu nghiệp vụ ⇒ đề xuất chuyển nhân viên.
        return TuChoiSom(OUT_OF_SCOPE_DATA, None, chuyen_giao=True)
    return None


@dataclass(frozen=True, slots=True)
class KetQuaSang:
    giu_lai: list[DoanTimDuoc]
    diem_cao_nhat: float | None
    ly_do: str | None  # NOT_COVERED khi phải từ chối, None khi đi tiếp sang LLM


def search_or_abstain(
    cac_doan: Sequence[DoanTimDuoc], *, san_toan_tap: float, san_tung_doan: float
) -> KetQuaSang:
    """Sàng kết quả truy hồi: giữ đoạn đủ gần, hoặc kết luận ``NOT_COVERED`` mà KHÔNG gọi LLM.

    Hai sàn trên cosine (không phải RRF — thang RRF chỉ 0,016–0,033, xem ``rerank/quyet_dinh.py``):

    - **sàn toàn tập** — đoạn gần nhất vẫn dưới sàn ⇒ kho không có đáp án. Gửi LLM lúc này chỉ để
      nhận lại ``KHONG_DU_CAN_CU`` sau ~1,5 s và tốn một lượt.
    - **sàn từng đoạn** — đoạn quá xa không vào lời nhắc: nó chỉ là nhiễu để mô hình bám nhầm.

    ``diem_cao_nhat`` được trả về KỂ CẢ khi dưới sàn: đặc tả UC025 bắt ghi nó vào bản ghi lượt —
    đây là số liệu gốc để hiệu chỉnh lại sàn về sau.
    """
    diem_cao_nhat = max(
        (d.do_tuong_dong for d in cac_doan if d.do_tuong_dong is not None), default=None
    )
    giu_lai = [
        d for d in cac_doan
        if d.do_tuong_dong is not None and d.do_tuong_dong >= san_tung_doan
    ]
    if not giu_lai or diem_cao_nhat is None or diem_cao_nhat < san_toan_tap:
        return KetQuaSang([], diem_cao_nhat, NOT_COVERED)
    return KetQuaSang(giu_lai, diem_cao_nhat, None)


def khong_bam_nguon(groundedness_score: float, nguong: float) -> bool:
    """Cổng sau sinh: điểm bám nguồn dưới ngưỡng ⇒ HUỶ câu trả lời đã sinh, từ chối LOW_CONFIDENCE.

    Sinh xong rồi vứt nghe lãng phí (đã trả tiền một lượt LLM), nhưng trả một câu không xác nhận
    được là dựa vào tài liệu thì tệ hơn nhiều: khách tin, làm theo, và cửa hàng chịu hậu quả.
    ``nguong = 0`` tắt cổng (điểm không bao giờ âm) — đó là baseline "không ngưỡng" khi hiệu chỉnh.
    """
    return groundedness_score < nguong
