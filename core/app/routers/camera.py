from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from app.auth.security import decode_access_token
from app.services.camera_service import camera_service

router = APIRouter(prefix="/api/v1/camera", tags=["camera"])

camera_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def verify_camera_auth(
    token: Optional[str] = Query(None),
    header_token: Optional[str] = Depends(camera_oauth2_scheme)
) -> bool:
    auth_token = header_token or token
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    payload = decode_access_token(auth_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return True

@router.get("/stream")
async def stream_video(authenticated: bool = Depends(verify_camera_auth)) -> StreamingResponse:
    return StreamingResponse(
        camera_service.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/snapshot")
def get_snapshot(authenticated: bool = Depends(verify_camera_auth)) -> Response:
    frame = camera_service.get_latest_frame()
    if not frame:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No frame available")
    return Response(content=frame, media_type="image/jpeg")
