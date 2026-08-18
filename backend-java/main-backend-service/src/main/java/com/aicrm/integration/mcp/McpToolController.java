package com.aicrm.integration.mcp;

import com.aicrm.common.response.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/mcp/tools")
public class McpToolController {

    @Autowired
    private McpToolService mcpToolService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<Object>>> getAvailableTools() {
        List<Object> tools = mcpToolService.getAvailableTools();
        return ResponseEntity.ok(ApiResponse.success(tools));
    }

    @PostMapping("/call")
    public ResponseEntity<ApiResponse<ToolCallResponse>> callTool(@RequestBody ToolCallRequest request) {
        ToolCallResponse response = mcpToolService.callTool(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
