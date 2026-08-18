from fastapi import APIRouter

router = APIRouter()

@router.post("/message")
def send_message():
    pass
