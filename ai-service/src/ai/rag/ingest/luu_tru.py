"""Cô lập tenant ở TẦNG KHO LƯU TRỮ — UC018. [PRODUCTION]

java-core ghi tệp vào bucket S3 dưới key ``{tenant_id}/…`` rồi gửi URI sang đây (ADR-0019).
RLS chỉ bảo vệ các dòng trong CSDL — nó không biết gì về kho S3. Nếu ai-service tải bất cứ
object nào được gửi tới, thì một URI trỏ sang key của tenant khác sẽ được đọc, cắt đoạn, nhúng
vector rồi ghi vào kho tri thức của tenant đang gọi — đúng kiểu rò rỉ chéo tenant mà chỉ số
"rò rỉ = 0" (§1.6) phải chặn.

ai-service có quyền ĐỌC toàn bucket (một bucket chung cho mọi tenant), nên kho S3 sẽ không tự
từ chối giúp. Hàm dưới đây là chốt chặn duy nhất.
"""


def kiem_uri_thuoc_tenant(file_uri: str, tenant_id: str, bucket: str) -> str:
    """🖐 TỰ GÕ — Ngày 3, mục B. AI không viết thân hàm này.

    Hợp đồng:
        Vào:
            ``file_uri``  chuỗi java-core gửi (``KbDocumentCreate.file_uri``) — KHÔNG tin.
                          Dạng hợp lệ: ``s3://{bucket}/{tenant_id}/{…}/{ten-tep}``
            ``tenant_id`` tenant đã xác thực, từ header ``X-Tenant-Id``
            ``bucket``    ``Settings.s3_bucket``
        Ra:
            ``key`` của object (phần sau tên bucket, KHÔNG có ``s3://`` và tên bucket), chắc
            chắn bắt đầu bằng đúng thư mục của tenant. ``object_storage`` dùng key này để đọc.
        Ném:
            ``ForbiddenFileUriError`` (``src/ai/exceptions.py``) cho MỌI ca dưới đây.

    Các ca phải chặn — test tích hợp Ngày 3 sẽ kiểm từng ca:
        1. Scheme không phải ``s3`` (``http://…``, ``file:///…``, đường dẫn trần ``/data/…``)
        2. Bucket khác bucket đã cấu hình
        3. Phân đoạn đầu của key là tenant KHÁC
        4. Phân đoạn đầu chỉ TRÙNG TIỀN TỐ chuỗi với tenant (``…/1111…1111-evil/bao-gia.pdf``)
        5. Key bất thường: có phân đoạn ``..`` hoặc ``.``, phân đoạn rỗng (``//``), dấu ``\\``,
           ký tự điều khiển, hoặc không có tên tệp sau thư mục tenant (``s3://kb/{tenant}/``)

    Vì sao ca 5 vẫn cần dù S3 không có khái niệm thư mục cha: ``..`` vô nghĩa với S3 nhưng
    không vô nghĩa với mọi thứ đứng giữa (proxy chuẩn hoá đường dẫn, worker ghi tệp tạm theo
    tên key). Chặn ngay ở cửa rẻ hơn đi rà mọi chỗ dùng key về sau.

    Câu hội đồng sẽ hỏi: truy vấn đã lọc ``tenant_id`` rồi, vì sao còn cần hàm này?
    """
    raise NotImplementedError("🖐 Ngày 3 — tự gõ theo docstring")
