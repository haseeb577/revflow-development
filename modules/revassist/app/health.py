from fastapi import APIRouter, Response

router = APIRouter()

@router.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return Response(content='{"status": "ok"}', media_type="application/json")
