package com.aicrm.integration.mcp;

import lombok.Data;
import java.util.Map;

@Data
public class ToolCallRequest {
    private String toolName;
    private Map<String, Object> arguments;
}
