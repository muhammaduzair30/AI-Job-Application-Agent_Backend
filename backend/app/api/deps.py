from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.session import get_db  # re-export
from app.models.user import User

__all__ = ["get_db", "get_current_active_user"]


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user's account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user
