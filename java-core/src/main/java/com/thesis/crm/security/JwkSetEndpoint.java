package com.thesis.crm.security;

import com.thesis.crm.security.RsaKeyProperties;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class JwkSetEndpoint {

    private final RsaKeyProperties rsaKeyProperties;

    public JwkSetEndpoint(RsaKeyProperties rsaKeyProperties) {
        this.rsaKeyProperties = rsaKeyProperties;
    }

    @GetMapping("/.well-known/jwks.json")
    public Map<String, Object> getJwks() {
        return rsaKeyProperties.toJwkSet().toJSONObject();
    }
}
