import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BACKEND_SERVICE_URL: str = os.getenv("BACKEND_SERVICE_URL", "http://localhost:8080")

settings = Settings()
