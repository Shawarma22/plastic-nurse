from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.db.models import User
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

class UserMeResponse(BaseModel):
    username: str
    role: str

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
) -> TokenResponse:
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username
    )

@router.get("/me", response_model=UserMeResponse)
def read_current_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        username=str(current_user.get("sub", "")),
        role=str(current_user.get("role", "operator"))
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
    admin: Dict[str, Any] = Depends(require_admin)
) -> UserResponse:
    existing = session.exec(select(User).where(User.username == payload.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed = get_password_hash(payload.password)
    new_user = User(username=payload.username, hashed_password=hashed, role=payload.role)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return UserResponse(
        id=new_user.id or 0,
        username=new_user.username,
        role=new_user.role,
        is_active=new_user.is_active
    )
