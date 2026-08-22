from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, Response
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.services.camera_service import camera_service
from app.auth.security import decode_access_token

router = APIRouter(prefix="/api/v1/camera", tags=["camera"])

# auto_error=False so a missing Authorization header falls through to the
# ?token= query param below, instead of the shared oauth2_scheme's default
# auto_error=True 401'ing before that fallback ever runs. <img>/<video> tags
# can't set an Authorization header, so the query param is the only way
# they can authenticate against this endpoint.
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
