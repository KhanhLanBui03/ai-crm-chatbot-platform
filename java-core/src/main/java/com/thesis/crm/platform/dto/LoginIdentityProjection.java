package com.thesis.crm.platform.dto;

import java.time.Instant;
import java.util.UUID;

public interface LoginIdentityProjection {
    UUID getUser_id();
    UUID getTenant_id();
    String getTenant_slug();
    String getTenant_status();
    String getPassword_hash();
    String getScope();
    String getStatus();
    Instant getEmail_verified_at();
    Short getFailed_login_count();
    Instant getLocked_until();
}
