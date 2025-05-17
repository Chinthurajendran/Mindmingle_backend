from fastapi import APIRouter,Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.database import get_session
from fastapi.responses import JSONResponse
from .service import *
from .dependencies import *
from fastapi_mail import FastMail, MessageSchema
from src.mail import mail_config
from src.utils import *
from sqlalchemy import and_

admin_router = APIRouter()
# admin_validation = Validation()
access_token_bearer = AccessTokenBearer()
# admin_service = AdminService()
REFRESH_TOKEN_EXPIRY = 2



@admin_router.put("/admin_logout")
async def logout_agent(
    session: AsyncSession = Depends(get_session),
    user_details : dict=Depends(access_token_bearer),
):
    return JSONResponse(status_code=200, content={"message": "Admin logged out successfully."})

@admin_router.post("/admin_refresh_token")
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data=token_details['user']
        )
        if isinstance(new_access_token, bytes):
            new_access_token = new_access_token.decode('utf-8')
        return JSONResponse(content={"admin_access_token": new_access_token})
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid or expired token")