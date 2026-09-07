# Project-Scoped Rules: AI CRM Chatbot Platform

## 1. Java Package Structure
- All Java packages must use the root package namespace `com.aicrm` (e.g., `com.aicrm.crm`, `com.aicrm.gateway`, `com.aicrm.mcp`, `com.aicrm.discovery`).
- Never use placeholder namespaces like `com.yourname` or `com.yourname.aicrm`.

## 2. Git Workflow
- Active development must take place on the `develop` branch.
- Do not commit directly to `main` unless performing production releases/merges.

## 3. Routing and API Gateway
- The API Gateway operates on port `8080` (`http://localhost:8080`).
- Route mappings:
  - `/api/auth/**`, `/api/business/**`, `/api/businesses/**`, `/api/chatbots/**`, `/api/documents/**`, `/api/customers/**`, `/api/conversations/**`, `/api/messages/**`, `/api/leads/**`, `/api/products/**`, `/api/dashboard/**`, `/api/public/chat/**` route to `main-backend-service`.
  - `/api/mcp/**` routes to `mcp-tool-service`.

## 4. Key Workflows & Communication Flows

### A. Public Chat Workflow (Widget to AI to CRM)
1. **Widget Request**: Widget sends user message payload (`PublicChatRequest`) to Gateway `POST /api/public/chat/message`.
2. **Java Entrypoint**: Gateway routes it to `main-backend-service` -> `PublicChatController` -> `PublicChatService`.
3. **AI Call**: Java backend calls Python AI Service `POST /api/chat/message` (using `AiServiceClient` client) passing chatbot context and conversation history.
4. **CRM Sync**: Java backend stores the user request, AI response, and updates the conversation session in database repositories (`ConversationRepository`, `MessageRepository`).
5. **Response**: Returns final answer payload (`PublicChatResponse`) back to the widget.

### B. Document Processing & RAG Workflow
1. **Upload**: User uploads files (txt, pdf, docx) to Java backend.
2. **AI Processing**: Java backend forwards the content to Python AI service `POST /api/document/process`.
3. **Chunking & Vectorizing**: Python service cleans text, splits it into chunks, calculates embedding vectors, and saves them in **Qdrant Vector Database** (under the `document_chunks` collection).
4. **RAG Retrieval**: During public chat execution, the LangGraph workflow searches Qdrant to retrieve relevant chunks using the `Retriever` to augment the LLM context.

### C. MCP Tool Call Workflow
1. **Agent Tool Trigger**: When the Python AI Agent needs real-world data or actions, it triggers an MCP tool call request.
2. **Routing to Java MCP**: The tool request is sent to `mcp-tool-service` via Gateway path `/api/mcp/tools/call`.
3. **Integration & Execution**: `mcp-tool-service` routes requests to the main database or CRM APIs in `main-backend-service`.
4. **Available Tools**:
   - `search_products`: Search CRM products.
   - `check_stock` / `check_price` / `get_product_detail`: Query product inventory details.
   - `create_lead`: Capture user info as a new CRM Lead.
   - `get_chatbot_settings`: Read specific chatbot configs.
   - `save_conversation_summary`: Store conversation summaries.
