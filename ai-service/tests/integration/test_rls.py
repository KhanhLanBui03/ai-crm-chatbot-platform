import psycopg
import pytest

# Import hằng số từ conftest như đề bài yêu cầu
from tests.conftest import CHUNK_A, CHUNK_B

# Bảng thật của Track B. RLS bật ENABLE + FORCE ở V207, policy tenant_isolation
# lọc bằng ai.current_tenant().
BANG_DOAN = "knowledge.knowledge_chunks"


# ---------------------------------------------------------
# Ca (a) - Policy có chạy không (Cô lập Tenant)
# ---------------------------------------------------------
async def test_policy_isolation(ai_conn, tenant_a):
    # Trap 2: Mọi thứ phải nằm trong transaction
    async with ai_conn.transaction():

        # Trap 1: Phải dùng set_config thay vì SET LOCAL trực tiếp
        # Tham số 'true' ở cuối chính là biến cài đặt thành LOCAL
        await ai_conn.execute(
            "SELECT set_config('app.tenant_id', %s, true)",
            (str(tenant_a),)
        )

        # ĐỐI CHỨNG: chính tenant A phải ĐỌC ĐƯỢC đoạn của mình.
        # Thiếu dòng này thì khẳng định "rỗng" ở dưới vô nghĩa: bảng rỗng, seed hỏng,
        # hay query nhầm id đều cho ra rỗng y hệt. Có cả hai mới phân biệt được
        # "policy chặn" với "không có dữ liệu".
        cur = await ai_conn.execute(
            f"SELECT id FROM {BANG_DOAN} WHERE id = %s", (CHUNK_A,)
        )
        assert len(await cur.fetchall()) == 1, "Tenant A khong doc duoc doan cua chinh no"

        # Cố tình query lấy dữ liệu của Tenant B (sử dụng CHUNK_B)
        cur = await ai_conn.execute(
            f"SELECT id FROM {BANG_DOAN} WHERE id = %s", (CHUNK_B,)
        )
        rows = await cur.fetchall()

        # Khẳng định kết quả rỗng (Policy đã chặn đứng dữ liệu của tenant B)
        assert len(rows) == 0


# ---------------------------------------------------------
# Ca (b) - Quên set quyền thì sao (Đóng mặc định)
# ---------------------------------------------------------
async def test_forgot_tenant_raises_error(ai_conn):
    # Trap 3: ca (b) đứng RIÊNG. Fixture ai_conn là function-scope nên mỗi test một
    # kết nối mới, và conn đang autocommit=True nên câu SELECT trần vẫn nổ 42501 —
    # không cần bọc transaction. Bọc vào thì sau khi lỗi, transaction ở trạng thái
    # hỏng mà khối vẫn gửi COMMIT lúc thoát; đúng là do PostgreSQL âm thầm đổi thành
    # ROLLBACK chứ không do mình thiết kế.
    with pytest.raises(psycopg.Error) as e:
        # Cố tình KHÔNG set app.tenant_id và thử SELECT
        await ai_conn.execute(f"SELECT id FROM {BANG_DOAN}")

    # Khẳng định ném ĐÚNG mã 42501. Dừng ở pytest.raises(psycopg.Error) là ăn may:
    # gõ sai tên bảng cũng ném psycopg.Error (42P01) và test vẫn xanh trong khi
    # chưa hề chạm tới RLS.
    assert e.value.sqlstate == "42501"


# ---------------------------------------------------------
# Ca (c) - Có đang đo đúng thứ không (Đúng User)
# ---------------------------------------------------------
async def test_correct_db_user(ai_conn):
    # Không cần transaction vì chỉ SELECT current_user
    cur = await ai_conn.execute("SELECT current_user")
    row = await cur.fetchone()

    # Khẳng định user đang nối DB chính xác là 'ai_app'.
    # crm_owner có rolbypassrls = t -> nối nhầm bằng nó thì (a) và (b) xanh giả.
    assert row[0] == "ai_app"
