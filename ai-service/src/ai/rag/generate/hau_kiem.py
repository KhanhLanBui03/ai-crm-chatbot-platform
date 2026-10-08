"""[PRODUCTION] Hậu kiểm câu trả lời đã sinh (postguard) — UC023 chặng 11, kế hoạch Ngày 9.

Thuần Python, KHÔNG gọi LLM: chạy trên 100% lượt có sinh câu trả lời, và một lượt gọi LLM thứ
hai để chấm lượt thứ nhất là nhân đôi chi phí lẫn độ trễ (KPI ≥ 55% lượt không gọi LLM).

BA VIỆC, THEO THỨ TỰ
-------------------
1. **Lọc trích dẫn.** Mọi ``[n]`` phải trỏ vào một đoạn đã truy hồi (1 ≤ n ≤ số đoạn). Số ngoài
   khoảng bị bỏ khỏi câu trả lời — mô hình không bịa được nguồn, kể cả khi bị tiêm chỉ thị.
2. **Đo độ bám nguồn** trên văn bản đã lọc (định nghĩa bên dưới).
3. **Che PII lạ.** PII trong câu trả lời mà KHÔNG có trong các đoạn đã lấy về thì che: đó là thứ
   mô hình bịa ra hoặc chép từ câu hỏi. PII có sẵn trong tài liệu doanh nghiệp (hotline, email
   chăm sóc khách hàng) thì giữ — che nó là phá đúng câu trả lời khách cần.

HAI ĐẠI LƯỢNG KHÁC NHAU — nhầm là hỏng cả chương đánh giá
--------------------------------------------------------
``retrieval_top_score`` (tính ở ``answerer.py``) = cosine cao nhất giữa câu hỏi và các đoạn: đo
*đoạn có giống câu hỏi không*. Có trước khi gọi LLM.

``groundedness_score`` (tệp này) đo *câu trả lời có thật sự dựa vào đoạn không*. Chỉ có sau khi
sinh. Truy hồi tốt mà mô hình vẫn bịa là trường hợp CÓ THẬT: đoạn đúng về bảo hành máy lạnh
(cosine 0,8) nhưng mô hình ghi "bảo hành 36 tháng" trong khi đoạn ghi 24 — retrieval cao,
groundedness thấp ở đúng câu đó.

ĐỊNH NGHĨA — chép nguyên vào chương 5
-------------------------------------
Tách câu trả lời thành câu. Câu dưới ``SO_AM_TIET_TOI_THIEU`` âm tiết là câu xã giao ("Dạ.",
"Cảm ơn anh/chị ạ!"), không tính. Với mỗi câu còn lại:

    bám nguồn  ⇔  câu có ≥ 1 trích dẫn hợp lệ
                  VÀ có MỘT đoạn được trích chứa ≥ NGUONG_PHU số âm tiết (đã bỏ dấu) của câu

    groundedness_score = số câu bám nguồn / số câu có nội dung

So với đoạn TỐT NHẤT trong số đoạn được trích, không gộp từ vựng của mọi đoạn: câu "tài liệu chưa
có thông tin về thu cũ đổi mới [1][2][3][4][5]" gộp 5 đoạn thì từ phổ thông nào cũng khớp, ra 0,5
dù không dựa vào đoạn nào; so từng đoạn thì ra 0 (đo 08/10, câu G004). Câu đúng trên 10 câu thử
không đổi điểm giữa hai cách.

Giới hạn đã biết (ghi vào báo cáo): đây là phép đo TỪ VỰNG. Mô hình diễn đạt lại bằng từ khác thì
điểm thấp oan — rõ nhất là dịch từ tài liệu tiếng Anh sang câu trả lời tiếng Việt (G061: đúng,
trích đúng, điểm 0). Chép đúng từ nhưng đảo nghĩa ("không được đổi" ↔ "được đổi") thì điểm cao
oan. Đổi lại: tất định, 0 đồng, dưới 1 ms, chạy lại ra cùng con số.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from src.ai.guardrails import mask_pii, tim_pii

SO_AM_TIET_TOI_THIEU = 4
NGUONG_PHU = 0.5

_TRICH_DAN = re.compile(r"\[\s*(\d{1,3}(?:\s*[,;]\s*\d{1,3})*)\s*\]")
_DAU_TRICH_DAN = re.compile(r"^(?:\s*\[[\d\s,;]+\])+")
# Ranh giới câu: sau . ! ? … có khoảng trắng, hoặc xuống dòng. "4.290.000đ" không bị cắt vì
# dấu chấm giữa hai chữ số không có khoảng trắng theo sau.
_TACH_CAU = re.compile(r"(?<=[.!?…])\s+|\n+")
_AM_TIET = re.compile(r"\w+")


@dataclass(frozen=True, slots=True)
class KetQuaHauKiem:
    # ``[k]`` trong câu trả lời đã đánh số lại 1..m, trỏ vào phần tử thứ k của ``trich_dan``.
    cau_tra_loi: str
    # Chỉ số đoạn GỐC (1-based, theo lời nhắc) theo thứ tự xuất hiện lần đầu, không trùng.
    trich_dan: list[int]
    so_trich_dan_bi_loai: int
    groundedness_score: float
    so_cau_noi_dung: int
    so_pii_da_che: int


def _so_trong(nhom: str) -> list[int]:
    return [int(x) for x in re.split(r"[,;]", nhom)]


def _am_tiet(van_ban: str) -> list[str]:
    """Âm tiết ĐÃ BỎ DẤU, viết thường.

    Bỏ dấu vì kho có tài liệu viết không dấu (FAQ gõ vội — chuyện thường ở SME, kho đo cố ý có
    một tệp như vậy): mô hình đọc "huy don truoc khi xuat kho" rồi trả lời "hủy đơn trước khi xuất
    kho". So nguyên dạng thì câu chép đúng tài liệu đó ra độ phủ 0,14 (đo 08/10, câu G047). Cùng
    lý do làn từ khoá so qua ``f_unaccent``. Giá phải trả: "bán"/"bàn" thành một — chấp nhận được
    cho một phép đo độ phủ, không phải phép so nghĩa.
    """
    tach = unicodedata.normalize("NFD", van_ban.lower())
    bo_dau = "".join(c for c in tach if unicodedata.category(c) != "Mn").replace("đ", "d")
    return _AM_TIET.findall(bo_dau)


def loc_trich_dan(van_ban: str, so_doan: int) -> tuple[str, int]:
    """Bỏ số ngoài ``[1, so_doan]``; chuẩn ``[1, 2]`` thành ``[1][2]``. Trả (văn bản, số bị bỏ)."""
    bi_loai = 0

    def thay(m: re.Match[str]) -> str:
        nonlocal bi_loai
        cac_so = _so_trong(m.group(1))
        hop_le = [n for n in dict.fromkeys(cac_so) if 1 <= n <= so_doan]
        bi_loai += len(cac_so) - len([n for n in cac_so if 1 <= n <= so_doan])
        return "".join(f"[{n}]" for n in hop_le)

    da_loc = _TRICH_DAN.sub(thay, van_ban)
    # Trích dẫn bị bỏ để lại khoảng trắng thừa trước dấu câu: "… 24 tháng ." → "… 24 tháng."
    da_loc = re.sub(r"[ \t]+([.,!?;:])", r"\1", da_loc)
    da_loc = re.sub(r"[ \t]{2,}", " ", da_loc)
    return da_loc.strip(), bi_loai


def _tach_cau(van_ban: str) -> list[str]:
    """Tách câu; trích dẫn đặt SAU dấu chấm ("… 24 tháng. [1]") được trả về câu đứng trước nó."""
    cac_cau: list[str] = []
    for manh in _TACH_CAU.split(van_ban):
        manh = manh.strip()
        if not manh:
            continue
        dau = _DAU_TRICH_DAN.match(manh)
        if dau and cac_cau:
            cac_cau[-1] += " " + dau.group(0).strip()
            manh = manh[dau.end() :].strip()
            if not manh:
                continue
        cac_cau.append(manh)
    return cac_cau


def do_bam_nguon(van_ban: str, cac_doan: Sequence[str]) -> tuple[float, int]:
    """(groundedness_score, số câu có nội dung) — xem định nghĩa ở đầu tệp."""
    so_cau_noi_dung = 0
    so_cau_bam = 0
    for cau in _tach_cau(van_ban):
        am_tiet = _am_tiet(_TRICH_DAN.sub(" ", cau))
        if len(am_tiet) < SO_AM_TIET_TOI_THIEU:
            continue
        so_cau_noi_dung += 1
        trich = {n for m in _TRICH_DAN.finditer(cau) for n in _so_trong(m.group(1))}
        trich = {n for n in trich if 1 <= n <= len(cac_doan)}
        if not trich:
            continue
        do_phu = max(
            sum(t in tu_vung for t in am_tiet) / len(am_tiet)
            for tu_vung in (set(_am_tiet(cac_doan[n - 1])) for n in trich)
        )
        if do_phu >= NGUONG_PHU:
            so_cau_bam += 1
    if so_cau_noi_dung == 0:
        return 0.0, 0
    return so_cau_bam / so_cau_noi_dung, so_cau_noi_dung


def _khoa_pii(gia_tri: str) -> str:
    """So PII theo dạng chuẩn: email viết thường; số thì chỉ giữ chữ số, +84 → 0."""
    if "@" in gia_tri:
        return gia_tri.lower()
    chu_so = re.sub(r"\D", "", gia_tri)
    if chu_so.startswith("84") and len(chu_so) == 11:
        chu_so = "0" + chu_so[2:]
    return chu_so


def che_pii_la(van_ban: str, cac_doan: Sequence[str]) -> tuple[str, int]:
    """Che PII của câu trả lời không có trong ``cac_doan``. Trả (văn bản, số giá trị đã che)."""
    trong_cau = tim_pii(van_ban)
    if not trong_cau:
        return van_ban, 0
    co_san = {_khoa_pii(v) for doan in cac_doan for v in tim_pii(doan)}
    da_che = 0
    for gia_tri in dict.fromkeys(trong_cau):
        if _khoa_pii(gia_tri) in co_san:
            continue
        nhan, _ = mask_pii(gia_tri)
        if nhan == gia_tri:
            # CMND 9 số chỉ khớp khi có chữ "CMND" phía trước — tách riêng ra thì không còn khớp.
            nhan = "[REDACTED_CMND]"
        van_ban = van_ban.replace(gia_tri, nhan)
        da_che += 1
    return van_ban, da_che


def danh_so_lai(van_ban: str) -> tuple[str, list[int]]:
    """Đổi ``[n]`` (số đoạn trong lời nhắc) thành ``[k]`` (vị trí trong mảng ``citations``).

    Mô hình trích ``[4]`` khi chỉ dùng mỗi đoạn 4 thì response có MỘT trích dẫn — để nguyên ``[4]``
    là giao diện không biết nó trỏ vào đâu. Đánh số theo thứ tự xuất hiện lần đầu.
    """
    thu_tu = list(
        dict.fromkeys(n for m in _TRICH_DAN.finditer(van_ban) for n in _so_trong(m.group(1)))
    )
    so_moi = {cu: moi for moi, cu in enumerate(thu_tu, start=1)}

    def thay(m: re.Match[str]) -> str:
        return "".join(f"[{so_moi[n]}]" for n in _so_trong(m.group(1)))

    return _TRICH_DAN.sub(thay, van_ban), thu_tu


def hau_kiem(cau_tra_loi: str, cac_doan: Sequence[str]) -> KetQuaHauKiem:
    """``cac_doan[i]`` là nội dung đoạn mang số ``[i+1]`` trong lời nhắc."""
    da_loc, bi_loai = loc_trich_dan(cau_tra_loi, len(cac_doan))
    diem, so_cau = do_bam_nguon(da_loc, cac_doan)
    da_che, so_pii = che_pii_la(da_loc, cac_doan)
    da_danh_so, trich_dan = danh_so_lai(da_che)
    return KetQuaHauKiem(
        cau_tra_loi=da_danh_so,
        trich_dan=trich_dan,
        so_trich_dan_bi_loai=bi_loai,
        groundedness_score=round(diem, 3),
        so_cau_noi_dung=so_cau,
        so_pii_da_che=so_pii,
    )
