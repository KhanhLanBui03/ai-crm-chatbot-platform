package com.aicrm.mcp.controller;

import com.aicrm.mcp.common.response.ApiResponse;
import com.aicrm.mcp.dto.request.ToolCallRequest;
import com.aicrm.mcp.dto.response.ToolCallResponse;
import com.aicrm.mcp.dto.response.ToolDefinitionResponse;
import com.aicrm.mcp.service.McpToolRegistryService;
import com.aicrm.mcp.service.ToolExecutionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/mcp")
public class McpToolController {

    private final McpToolRegistryService registryService;
    private final ToolExecutionService executionService;

    public McpToolController(McpToolRegistryService registryService, ToolExecutionService executionService) {
        this.registryService = registryService;
        this.executionService = executionService;
    }

    @GetMapping("/tools")
    public ResponseEntity<ApiResponse<ToolDefinitionResponse>> listTools() {
        ToolDefinitionResponse response = ToolDefinitionResponse.builder()
                .tools(registryService.getRegisteredTools())
                .build();
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/tools/call")
    public Mono<ResponseEntity<ApiResponse<ToolCallResponse>>> callTool(@RequestBody ToolCallRequest request) {
        return executionService.execute(request)
                .map(result -> ToolCallResponse.builder()
                        .tool(request.getName())
                        .result(result)
                        .build())
                .map(response -> ResponseEntity.ok(ApiResponse.success(response)))
                .onErrorResume(ex -> Mono.just(ResponseEntity.badRequest()
                        .body(ApiResponse.error(ex.getMessage()))));
    }
}
