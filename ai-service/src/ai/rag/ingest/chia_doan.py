"""Chia ``Khoi`` thành đoạn để nhúng và truy hồi — UC019 chặng 3. [PRODUCTION]

Mỗi đoạn mang theo ĐƯỜNG DẪN HEADING (``"Bảng giá sản phẩm 2026 > 3. Máy lạnh"``) và SỐ TRANG
của nó. Đó là nguyên liệu trích dẫn của UC023: câu trả lời "máy lạnh 1 HP giá 6.490.000đ" phải
chỉ được về "Bảng giá sản phẩm 2026 > 3. Máy lạnh, trang 2" — không có hai thứ này thì chỉ số
độ phủ trích dẫn ≥ 0,80 (§1.6) không có gì để đo.

BA LUẬT CHIA
------------
1. **Ranh giới heading là ranh giới đoạn.** Gặp heading mới thì đóng đoạn đang gom, kể cả khi
   đoạn còn ngắn. Gộp hai mục khác nhau vào một đoạn thì đoạn đó không còn MỘT heading đúng để
   trích dẫn, và vector của nó là trung bình của hai chủ đề — không gần câu hỏi nào.
2. **Trần ~500 token ước lượng, không phải đích.** Mục ngắn cho đoạn ngắn. Mục dài vượt trần
   thì tách theo CÂU (không cắt giữa câu); một câu đơn lẻ dài quá trần mới tách theo từ.
3. **Bảng tách theo DÒNG và lặp lại dòng tiêu đề cột.** Đoạn thứ hai của bảng giá mà thiếu dòng
   "Mã sản phẩm | Mô tả | Giá niêm yết" thì "NH-ML12I | … | 8.490.000đ" chỉ là một dãy số —
   cả mô hình nhúng lẫn mô hình sinh đều không biết số nào là giá.

TOKEN ƯỚC LƯỢNG
---------------
ai-service không được nạp ``tokenizers`` (``.claude/rules/ai-service.md``), nên không đếm được
token thật của bge-m3. Ở đây đếm "từ hoặc dấu câu" (``\\w+|[^\\w\\s]``) — với tiếng Việt, một
âm tiết thường là 1–2 token của bge-m3, nên 500 đơn vị ở đây nằm xa dưới trần 8 192 token của
mô hình. Ngày 5 có ``ai-embed`` thì đo tỉ lệ thật và ghi vào báo cáo.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from src.ai.rag.ingest.phan_tich import Khoi

# Cột ``knowledge_chunks.heading`` là varchar(255) (V203).
_HEADING_TOI_DA = 255
_NOI_HEADING = " > "

_DON_VI_TOKEN = re.compile(r"\w+|[^\w\s]")
# Ranh giới câu: sau . ! ? … (có thể kèm ngoặc/nháy đóng) rồi khoảng trắng; hoặc xuống dòng.
_RANH_GIOI_CAU = re.compile(r"(?<=[.!?…])[\"”’)\]]*\s+|\n+")


@dataclass(frozen=True, slots=True)
class Doan:
    """Một dòng tương lai của ``knowledge.knowledge_chunks`` (chưa có vector — Ngày 5)."""

    chunk_index: int
    content: str
    heading: str | None
    page_number: int | None
    token_count: int


def dem_token(van_ban: str) -> int:
    """Số token ƯỚC LƯỢNG: số từ + số dấu câu."""
    return len(_DON_VI_TOKEN.findall(van_ban))


def duong_dan_heading(cac_heading: Iterable[str]) -> str | None:
    """Nối heading từ gốc tới lá bằng ``" > "``, vừa trong 255 ký tự.

    Quá dài thì bỏ heading ở GỐC trước, giữ phần gần đoạn nhất: "… > 6.1. Máy lọc nước" còn
    trích dẫn được, "Bảng giá sản phẩm 2026 > …" thì không. Một heading lá tự nó dài quá 255
    thì cắt đuôi.
    """
    cac_heading = [h for h in cac_heading if h]
    if not cac_heading:
        return None
    while len(cac_heading) > 1 and len(_NOI_HEADING.join(cac_heading)) > _HEADING_TOI_DA:
        cac_heading = cac_heading[1:]
    ket_qua = _NOI_HEADING.join(cac_heading)
    if len(ket_qua) > _HEADING_TOI_DA:
        ket_qua = ket_qua[: _HEADING_TOI_DA - 1] + "…"
    return ket_qua


def _tach_cau(van_ban: str, tran: int) -> list[str]:
    """Tách văn bản dài thành các mẩu ≤ ``tran`` token, cắt ở ranh giới câu."""
    cac_cau = [c.strip() for c in _RANH_GIOI_CAU.split(van_ban) if c and c.strip()]
    manh: list[str] = []
    for cau in cac_cau:
        if dem_token(cau) <= tran:
            manh.append(cau)
            continue
        # Một câu dài quá trần (bảng liệt kê không dấu chấm, văn bản dán liền): tách theo từ.
        tu = cau.split(" ")
        hien_tai: list[str] = []
        for t in tu:
            if hien_tai and dem_token(" ".join([*hien_tai, t])) > tran:
                manh.append(" ".join(hien_tai))
                hien_tai = []
            hien_tai.append(t)
        if hien_tai:
            manh.append(" ".join(hien_tai))
    return manh


class _BoGom:
    """Gom mẩu văn bản thành đoạn ≤ ``tran`` token, nhớ trang đầu và heading lúc mở đoạn."""

    def __init__(self, tran: int) -> None:
        self.tran = tran
        self.ket_qua: list[Doan] = []
        self._manh: list[str] = []
        self._token = 0
        self._trang: int | None = None
        self._heading: str | None = None

    @property
    def rong(self) -> bool:
        return not self._manh

    def dong(self) -> None:
        if not self._manh:
            return
        noi_dung = "\n\n".join(self._manh)
        self.ket_qua.append(
            Doan(
                chunk_index=len(self.ket_qua),
                content=noi_dung,
                heading=self._heading,
                page_number=self._trang,
                token_count=dem_token(noi_dung),
            )
        )
        self._manh, self._token, self._trang = [], 0, None

    def them(self, manh: str, trang: int | None, heading: str | None) -> None:
        """Thêm một mẩu; đóng đoạn trước nếu mẩu này làm vượt trần."""
        so_token = dem_token(manh)
        if self._manh and self._token + so_token > self.tran:
            self.dong()
        if not self._manh:
            self._trang, self._heading = trang, heading
        self._manh.append(manh)
        self._token += so_token

    def them_bang(self, bang: str, trang: int | None, heading: str | None) -> None:
        """Thêm bảng; bảng không vừa thì tách theo dòng, mỗi đoạn mở đầu bằng dòng tiêu đề."""
        if self._token + dem_token(bang) <= self.tran or dem_token(bang) <= self.tran:
            self.them(bang, trang, heading)
            return
        tieu_de, *cac_dong = bang.split("\n")
        self.dong()
        phan: list[str] = [tieu_de]
        for dong in cac_dong:
            if len(phan) > 1 and dem_token("\n".join([*phan, dong])) > self.tran:
                self.them("\n".join(phan), trang, heading)
                self.dong()
                phan = [tieu_de]
            phan.append(dong)
        if len(phan) > 1:
            self.them("\n".join(phan), trang, heading)


def chia_doan(cac_khoi: Iterable[Khoi], tran_token: int = 500) -> list[Doan]:
    """Chia ``cac_khoi`` (đã qua ``normalize_vi``) thành các ``Doan`` theo ba luật ở đầu module.

    ``chunk_index`` liên tục từ 0 — khớp ``uq_chunk_index (document_id, chunk_index)`` của V203.
    """
    bo_gom = _BoGom(tran_token)
    # Ngăn xếp (cấp, chữ) từ gốc tới heading hiện tại.
    ngan_xep: list[tuple[int, str]] = []

    for khoi in cac_khoi:
        chu = khoi.text.strip()
        if not chu:
            continue

        if khoi.loai == "heading":
            bo_gom.dong()
            # Heading cấp c thay mọi heading cùng cấp hoặc sâu hơn đang mở.
            while ngan_xep and ngan_xep[-1][0] >= khoi.cap:
                ngan_xep.pop()
            ngan_xep.append((khoi.cap, chu))
            continue

        heading = duong_dan_heading(h for _, h in ngan_xep)
        if khoi.loai == "bang":
            bo_gom.them_bang(chu, khoi.trang, heading)
        elif dem_token(chu) <= tran_token:
            bo_gom.them(chu, khoi.trang, heading)
        else:
            for manh in _tach_cau(chu, tran_token):
                bo_gom.them(manh, khoi.trang, heading)

    bo_gom.dong()
    return bo_gom.ket_qua
