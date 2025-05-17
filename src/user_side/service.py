from src.db.models import *
from .schemas import *
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime
from src.utils import generate_passwd_hash, UPLOAD_DIR, random_code
from fastapi import UploadFile, File, HTTPException, status, WebSocket, WebSocketDisconnect
import logging
from uuid import UUID
import traceback
from dotenv import load_dotenv
import os
import boto3
import pytz
import hmac
import hashlib
from fastapi import Query
import re
from typing import Optional
from botocore.exceptions import ClientError
import mimetypes
import asyncio

load_dotenv()

BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


class Validation:
    async def validate_text(self, text: str, session: AsyncSession) -> bool:
        if not text:
            return False
        return bool(re.match(r"^[A-Za-z\s]+$", text))

    async def validate_email(self, email: str, session: AsyncSession) -> bool:
        return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$", email))
    
    async def description(self, text: str, session: AsyncSession) -> bool:
        if not text:
            return False
        if not re.match(r"^[A-Za-z0-9\s.,'’\-]+$", text):
            return False
        if len(text.strip().split()) < 50:  # Requires at least 50 words
            return False
        return True


    async def validate_file_type(self, image: UploadFile, session: AsyncSession) -> bool:
        if image is None:
            return True
        return image.filename.lower().endswith((".jpg", ".jpeg", ".png"))

    async def validate_password(self, password: str, session: AsyncSession) -> bool:
        return bool(re.match(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$/%^&+=!]).{8,}$",
            password))

    async def validate_otp(self, otp: str, session: AsyncSession) -> bool:
        if not otp:
            return False
        return bool(re.match(r"^\d{6}$", otp))


class UserService:
    async def get_user_by_id(self, user_id: str, session: AsyncSession):
        statement = select(usertable).where(usertable.user_id == user_id)
        result = await session.exec(statement)

        user = result.first()

        return user

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(usertable).where(usertable.email == email)
        result = await session.exec(statement)

        user = result.first()

        return user
    
    async def get_user_by_username(self, username: str, session: AsyncSession):
        statement = select(usertable).where(usertable.username == username)

        result = await session.exec(statement)
        user = result.first()
        return user

    async def exist_email(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)

        return True if user is not None else False

    async def exist_username(self, username: str, session: AsyncSession):
        user = await self.get_user_by_username(username, session)

        return True if user is not None else False

        return True if user is not None else False

    async def exist_user_id(self, user_id: str, session: AsyncSession):
        user = await self.get_user_by_id(user_id, session)

        return True if user is not None else False

    async def create_user(self, user_details: UserCreate, session: AsyncSession):

        user_data_dict = user_details.model_dump()

        ist = pytz.timezone("Asia/Kolkata")
        utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        local_time = utc_time.astimezone(ist)
        local_time_naive = local_time.replace(tzinfo=None)

        create_at = local_time_naive
        update_at = local_time_naive

        new_user = usertable(
            **user_data_dict,
            create_at=create_at,
            update_at=update_at
        )
        new_user.password = generate_passwd_hash(user_data_dict['password'])

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        return new_user
    

    async def upload_to_s3_bucket(self, file: UploadFile, folder_name: str) -> str:
        try:
            file_path = f"{folder_name}/{file.filename}"
            content_type, _ = mimetypes.guess_type(file.filename)  
            content_type = content_type or "application/octet-stream" 

            def upload():
                s3_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=file_path,
                    Body=file.file,
                    ContentType=content_type
                )

            await asyncio.to_thread(upload) 
            file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_path}"
            return file_url

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file '{file.filename}' to S3: {e.response['Error']['Message']}"
            )
        
    async def create_bloge(
        self,
        user_id: UUID,  
        policy_info: BlogecreateRequest,
        photo: Optional[UploadFile],
        session: AsyncSession
    ):
        try:
            folder_name = f"User/bloge"

            photo_url = await self.upload_to_s3_bucket(photo, folder_name) if photo else None

            ist = pytz.timezone("Asia/Kolkata")
            utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(ist)
            local_time_naive = local_time.replace(tzinfo=None)

            new_bloge = BlogCreate(
                photo=photo_url, 
                description=policy_info['description'],
                user_id=user_id,
                create_at=local_time_naive,
                update_at=local_time_naive
            )

            session.add(new_bloge)
            await session.commit()

            return new_bloge
        except Exception as e:
            await session.rollback()
            raise Exception(f"Error creating policy info: {str(e)}")
