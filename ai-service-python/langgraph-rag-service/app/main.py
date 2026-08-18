from fastapi import FastAPI
from app.api import chat_routes, document_routes, rag_routes, health_routes

app = FastAPI(title="LangGraph RAG Service", version="1.0.0")

app.include_router(health_routes.router, tags=["Health"])
app.include_router(chat_routes.router, prefix="/api/chat", tags=["Chat"])
app.include_router(document_routes.router, prefix="/api/document", tags=["Document"])
app.include_router(rag_routes.router, prefix="/api/rag", tags=["RAG"])
