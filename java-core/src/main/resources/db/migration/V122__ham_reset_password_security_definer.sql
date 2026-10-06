CREATE OR REPLACE FUNCTION platform.reset_password(p_email text, p_password_hash varchar)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $$
DECLARE
    v_user_id uuid;
BEGIN
    SELECT id INTO v_user_id
      FROM platform.users
     WHERE lower(email) = lower(p_email)
       AND deleted_at IS NULL;

    IF v_user_id IS NULL THEN
        RETURN false;
    END IF;

    UPDATE platform.users
       SET password_hash = p_password_hash,
           failed_login_count = 0,
           locked_until = NULL,
           updated_at = NOW()
     WHERE id = v_user_id;

    RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION platform.reset_password(text, varchar) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.reset_password(text, varchar) TO crm_app;

COMMENT ON FUNCTION platform.reset_password(text, varchar) IS
    'SECURITY DEFINER: Đặt lại mật khẩu tài khoản người dùng và mở khóa tài khoản, bỏ qua RLS.';
