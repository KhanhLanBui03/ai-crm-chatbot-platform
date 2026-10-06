package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.UserRole;
import com.thesis.crm.platform.entity.UserRoleId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserRoleRepository extends JpaRepository<UserRole, UserRoleId> {
}
