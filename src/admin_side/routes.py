from fastapi import APIRouter,Depends,Form
from src.db.database import get_session
from fastapi.responses import JSONResponse
from .service import *
from .dependencies import *
from fastapi_mail import FastMail, MessageSchema
from src.mail import mail_config
from src.utils import *
from sqlalchemy import and_
from sqlalchemy.future import select
from src.db.models import *
from sqlalchemy.ext.asyncio import AsyncSession


admin_router = APIRouter()
admin_validation = Validation()
access_token_bearer = AccessTokenBearer()
admin_service = AdminService()
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


@admin_router.get("/user_list", response_model=dict)
async def user_list(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(usertable).where(usertable.delete_status == False )) 
        users = result.scalars().all()

        user_list = []
        for user in users:
            user_list.append({
                "user_id": str(user.user_id),
                "username": user.username,
                "email": user.email,
                "image": user.image,
                "block_status": user.block_status,
                "login_status": user.login_status,
            })

        return JSONResponse(status_code=200, content={"users": user_list})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )


@admin_router.get("/user_profile/{userId}", response_model=list[dict])
async def user_profile(userId: UUID, session: AsyncSession = Depends(get_session), agent_details=Depends(access_token_bearer)):
    result = await session.execute(select(usertable).where(usertable.user_id == userId))
    user = result.scalars().first()

    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found"})

    user_data = {
        "username": user.username,
        "email": user.email,
        "image": user.image,
    }
    return JSONResponse(status_code=200, content={"user": user_data})


@admin_router.put("/profile_create/{userId}", response_model=dict)
async def update_profile(userId: UUID,
                         username: str = Form(...),
                         email: EmailStr = Form(...),
                         image_url: Optional[str] = Form(None),
                         image: Optional[UploadFile] = File(None),
                         session: AsyncSession = Depends(get_session)):

    is_username = await admin_validation.validate_text(username, session)
    if not is_username:
        raise HTTPException(
            status_code=400, detail="Invalid username: only letters and spaces are allowed.")

    is_email = await admin_validation.validate_email(email, session)
    if not is_email:
        raise HTTPException(status_code=400, detail="Invalid email format.")

    is_file = await admin_validation.validate_file_type(image, session)
    if not is_file:
        raise HTTPException(
            status_code=400, detail="Invalid file type: only .jpg, .jpeg, or .png files are allowed.")

    user_exists = await admin_service.exist_user_id(userId, session)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_data = ProfileCreateRequest(
        username=username,
        email=email,
    )

    update_user = await admin_service.profile_update(user_data, userId, image, session)

    return JSONResponse(status_code=200, content={"message": "Profile updated successfully"})

@admin_router.post("/user_create", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def user_create(user_data: UserCreate, session: AsyncSession = Depends(get_session)):

    email = user_data.email.lower()
    username = user_data.username.lower()

    is_username = await admin_validation.validate_text(username, session)
    if not is_username:
        raise HTTPException(
            status_code=400, detail="Invalid username: only letters and spaces are allowed.")

    is_password = await admin_validation.validate_password(user_data.password, session)
    if not is_password:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters, contain 1 uppercase, 1 lowercase, 1 digit, and 1 special character.")

    user_exists_with_email = await admin_service.exist_email(email, session)
    user_exists_with_username = await admin_service.exist_username(username, session)

    if user_exists_with_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email already exists")
    if user_exists_with_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Username already exists")
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    new_user = await admin_service.create_user(user_data, session)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Registration successful! Please log in.",
        }
    )


@admin_router.put("/user_delete/{userId}", response_model=dict)
async def user_delete(userId: UUID,session: AsyncSession = Depends(get_session)):

    user_exists = await admin_service.exist_user_id(userId, session)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_user = await admin_service.user_delete(userId,session)

    return JSONResponse(status_code=200, content={"message": "Profile updated successfully"})



@admin_router.get("/bloge_list", response_model=dict)
async def bloge_list(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(BlogCreate).where(BlogCreate.delete_status == False )) 
        blog = result.scalars().all()

        bloges = []
        for blogs in blog:
            bloges.append({
                "blog_uid": str(blogs.blog_uid),
                "photo": blogs.photo,
                "description": blogs.description,
            })

        return JSONResponse(status_code=200, content={"bloges": bloges})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
    

@admin_router.get("/fetch_blog_details_for_editing/{BlogeID}", response_model=dict)
async def fetch_blog_details_for_editing(BlogeID: UUID, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(
                BlogCreate.blog_uid,
                BlogCreate.photo,
                BlogCreate.description,
            ).where(BlogCreate.blog_uid == BlogeID)
        )

        blog_data = result.first()

        if not blog_data:
            raise HTTPException(status_code=404, detail="Blog not found")

        blog_uid, photo, description = blog_data

        bloges = [{
            "blog_uid": str(blog_uid),
            "photo": photo,
            "description": description
        }]

        return JSONResponse(status_code=200, content={"bloges": bloges})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching blog details: {str(e)}"
        )


@admin_router.put("/Bloge_updation/{BlogeID}", response_model=dict)
async def Bloge_updation(
    BlogeID: UUID,
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    is_description = await admin_validation.description(description, session)
    if not is_description:
        raise HTTPException(
            status_code=400,
            detail="Invalid description. Only letters and spaces are allowed."
        )

    if image:
        is_photo = await admin_validation.validate_file_type(image, session)
        if not is_photo:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload a .jpg, .jpeg, or .png image."
            )

    result = await session.execute(select(BlogCreate).where(BlogCreate.blog_uid == BlogeID))
    blog_data = result.scalars().first()

    if not blog_data:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog_update_data = BlogecreateRequest(
        description = description
    )

    created_blog = await admin_service.bloge_updation(BlogeID, blog_update_data, image, session)

    return JSONResponse(status_code=200, content={"message": "Blog updated successfully"})


@admin_router.put("/bloge_delete/{BlogeID}", response_model=dict)
async def bloge_delete(BlogeID: UUID,session: AsyncSession = Depends(get_session)):
    update_user = await admin_service.bloge_delete(BlogeID,session)

    return JSONResponse(status_code=200, content={"message": "Profile updated successfully"})
