package com.thesis.crm.platform.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.platform.dto.RoleDto;
import com.thesis.crm.platform.entity.Role;
import com.thesis.crm.platform.repository.RoleRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
public class RoleService {

    private static final Logger log = LoggerFactory.getLogger(RoleService.class);

    private final RoleRepository roleRepository;
    private final ObjectMapper objectMapper;

    public RoleService(RoleRepository roleRepository, ObjectMapper objectMapper) {
        this.roleRepository = roleRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public List<RoleDto> layDanhSachVaiTro(UUID tenantId) {
        List<Role> roles = roleRepository.findAllByTenantIdOrSystem(tenantId);
        List<RoleDto> dtos = new ArrayList<>();

        for (Role role : roles) {
            // Loại bỏ vai trò PLATFORM_ADMIN khỏi màn hình phân quyền của Tenant
            if ("PLATFORM_ADMIN".equalsIgnoreCase(role.getCode())) {
                continue;
            }

            Map<String, String> permissionsMap = normalizePermissions(role.getCode(), role.getPermissions());
            long userCount = roleRepository.countUsersByRoleAndTenant(role.getId(), tenantId);

            dtos.add(new RoleDto(
                    role.getCode(),
                    role.getName(),
                    role.getDescription(),
                    permissionsMap,
                    userCount
            ));
        }

        return dtos;
    }

    private Map<String, String> normalizePermissions(String roleCode, String permissionsJson) {
        Map<String, String> map = new LinkedHashMap<>();

        if ("TENANT_ADMIN".equalsIgnoreCase(roleCode)) {
            map.put("conversations", "FULL");
            map.put("contacts", "FULL");
            map.put("knowledge", "FULL");
            map.put("sales", "FULL");
            map.put("analytics", "FULL");
            map.put("settings", "FULL");
            map.put("audit", "FULL");
            map.put("billing", "FULL");
            return map;
        }

        if ("AGENT".equalsIgnoreCase(roleCode)) {
            map.put("conversations", "READ_WRITE");
            map.put("contacts", "READ_WRITE");
            map.put("knowledge", "READ");
            map.put("sales", "READ_WRITE");
            map.put("analytics", "READ");
            map.put("settings", "NONE");
            map.put("audit", "NONE");
            map.put("billing", "NONE");
            return map;
        }

        // Với các vai trò tuỳ biến trong tương lai
        try {
            if (permissionsJson != null && permissionsJson.trim().startsWith("{")) {
                return objectMapper.readValue(permissionsJson, new TypeReference<Map<String, String>>() {});
            }
        } catch (Exception e) {
            log.warn("Không thể parse permissions JSON cho role {}: {}", roleCode, permissionsJson, e);
        }

        map.put("conversations", "READ");
        map.put("contacts", "READ");
        map.put("knowledge", "READ");
        map.put("sales", "NONE");
        map.put("analytics", "NONE");
        map.put("settings", "NONE");
        map.put("audit", "NONE");
        map.put("billing", "NONE");
        return map;
    }
}
