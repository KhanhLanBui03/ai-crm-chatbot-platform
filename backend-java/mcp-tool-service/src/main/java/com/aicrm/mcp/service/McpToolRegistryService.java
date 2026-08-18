package com.aicrm.mcp.service;

import com.aicrm.mcp.model.ToolDefinition;
import com.aicrm.mcp.model.ToolParameter;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Service
public class McpToolRegistryService {

    public List<ToolDefinition> getRegisteredTools() {
        List<ToolDefinition> tools = new ArrayList<>();

        tools.add(ToolDefinition.builder()
                .name("SEARCH_PRODUCTS")
                .description("Search products catalog matching a keyword query")
                .parameters(Arrays.asList(
                        new ToolParameter("query", "string", "Keyword to search for", true),
                        new ToolParameter("businessId", "number", "The business ID context", true)
                ))
                .build());

        tools.add(ToolDefinition.builder()
                .name("CHECK_STOCK")
                .description("Check remaining stock quantity of a given product")
                .parameters(Arrays.asList(
                        new ToolParameter("productId", "number", "The product ID", true),
                        new ToolParameter("businessId", "number", "The business ID context", true)
                ))
                .build());

        tools.add(ToolDefinition.builder()
                .name("CHECK_PRICE")
                .description("Get current unit price for a product")
                .parameters(Arrays.asList(
                        new ToolParameter("productId", "number", "The product ID", true),
                        new ToolParameter("businessId", "number", "The business ID context", true)
                ))
                .build());

        tools.add(ToolDefinition.builder()
                .name("CREATE_LEAD")
                .description("Create a new CRM lead from customer info gathered during conversation")
                .parameters(Arrays.asList(
                        new ToolParameter("name", "string", "Customer full name", true),
                        new ToolParameter("email", "string", "Customer email address", false),
                        new ToolParameter("phone", "string", "Customer phone contact number", false),
                        new ToolParameter("notes", "string", "Summarized conversation interest details", false),
                        new ToolParameter("businessId", "number", "The business ID context", true),
                        new ToolParameter("conversationId", "number", "The current active session ID", true)
                ))
                .build());

        return tools;
    }
}
