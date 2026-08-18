package com.aicrm.mcp.dto.response;

import com.aicrm.mcp.model.ToolResult;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ToolCallResponse {
    private String tool;
    private ToolResult result;
}
