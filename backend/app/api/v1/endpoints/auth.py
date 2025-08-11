"""
Authentication endpoints
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.security import create_access_token, get_current_active_user
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(
    db: AsyncSession = Depends(get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user_service = UserService(db)
    user = await user_service.authenticate(
        email=form_data.username, 
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        # Decode refresh token
        payload = jwt.decode(
            refresh_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if refresh token is blacklisted
        from app.core.redis_client import redis_client
        if await redis_client.is_blacklisted(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user_service = UserService(db)
        user = await user_service.get(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Logout user and blacklist tokens
    """
    from app.core.redis_client import redis_client
    
    # Add current token to blacklist
    # Note: This requires the token to be passed in the request
    # You might want to modify the middleware to extract the token
    
    return {"message": "Successfully logged out"}


@router.post("/register", response_model=UserResponse)
async def register(
    *,
    db: AsyncSession = Depends(get_async_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user account
    """
    user_service = UserService(db)
    
    # Check if user already exists
    user = await user_service.get_by_email(email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    user = await user_service.create(obj_in=user_in.dict())
    return user


@router.post("/test-token", response_model=UserResponse)
async def test_token(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Test access token
    """
    return current_user
