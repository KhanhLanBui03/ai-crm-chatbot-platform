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
