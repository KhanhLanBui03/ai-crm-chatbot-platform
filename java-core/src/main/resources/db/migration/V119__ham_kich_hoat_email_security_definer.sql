-- V119 - Ham kich hoat tai khoan / xac thuc email (SECURITY DEFINER, bypass RLS)
CREATE OR REPLACE FUNCTION platform.verify_email(p_user_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $sql_body$
BEGIN
    UPDATE platform.users
       SET status = 'ACTIVE',
           email_verified_at = COALESCE(email_verified_at, now()),
           updated_at = now()
     WHERE id = p_user_id;
    RETURN FOUND;
END $sql_body$;

REVOKE ALL ON FUNCTION platform.verify_email(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.verify_email(uuid) TO crm_app;

COMMENT ON FUNCTION platform.verify_email(uuid) IS
    'Kich hoat tai khoan khi xac thuc email.';