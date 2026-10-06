-- V121 — Các hàm hỗ trợ cập nhật đăng nhập (SECURITY DEFINER, bypass RLS)

CREATE OR REPLACE FUNCTION platform.reset_failed_login(p_user_id uuid, p_last_login timestamptz)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $sql_body$
BEGIN
    UPDATE platform.users
       SET failed_login_count = 0,
           locked_until = NULL,
           last_login_at = p_last_login,
           updated_at = now()
     WHERE id = p_user_id;
    RETURN FOUND;
END $sql_body$;

CREATE OR REPLACE FUNCTION platform.update_failed_login(p_user_id uuid, p_count smallint, p_locked_until timestamptz)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $sql_body$
BEGIN
    UPDATE platform.users
       SET failed_login_count = p_count,
           locked_until = p_locked_until,
           updated_at = now()
     WHERE id = p_user_id;
    RETURN FOUND;
END $sql_body$;

CREATE OR REPLACE FUNCTION platform.activate_user(p_user_id uuid, p_verified_at timestamptz)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $sql_body$
BEGIN
    UPDATE platform.users
       SET status = 'ACTIVE',
           email_verified_at = COALESCE(email_verified_at, p_verified_at),
           updated_at = now()
     WHERE id = p_user_id;
    RETURN FOUND;
END $sql_body$;

REVOKE ALL ON FUNCTION platform.reset_failed_login(uuid, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.reset_failed_login(uuid, timestamptz) TO crm_app;

REVOKE ALL ON FUNCTION platform.update_failed_login(uuid, smallint, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.update_failed_login(uuid, smallint, timestamptz) TO crm_app;

REVOKE ALL ON FUNCTION platform.activate_user(uuid, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.activate_user(uuid, timestamptz) TO crm_app;
