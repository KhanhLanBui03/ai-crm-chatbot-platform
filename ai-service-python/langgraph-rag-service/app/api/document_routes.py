from fastapi import APIRouter

router = APIRouter()

@router.post("/process")
def process_document():
    pass
