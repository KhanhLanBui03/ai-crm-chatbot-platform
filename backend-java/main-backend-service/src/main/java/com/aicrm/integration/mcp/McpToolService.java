package com.aicrm.integration.mcp;

import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class McpToolService {

    /**
     * Lấy danh sách các tools khả dụng (search_products, check_stock, check_price, get_product_detail, create_lead, get_chatbot_settings, save_conversation_summary)
     */
    public List<Object> getAvailableTools() {
        return null;
    }

    /**
     * Thực thi gọi một tool cụ thể với các đối số truyền vào
     */
    public ToolCallResponse callTool(ToolCallRequest request) {
        return null;
    }
}
