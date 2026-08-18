package com.aicrm.mcp.dto.response;

import com.aicrm.mcp.model.ToolDefinition;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ToolDefinitionResponse {
    private List<ToolDefinition> tools;
}
