from fastapi import APIRouter, Depends, Form
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.database import get_session
from fastapi.responses import JSONResponse
from .service import *
from .dependencies import *
from fastapi_mail import FastMail, MessageSchema
from src.mail import mail_config
from src.utils import *
from sqlalchemy import and_
from sqlalchemy.future import select
from fastapi.encoders import jsonable_encoder
import traceback


logger = logging.getLogger(__name__)

auth_router = APIRouter()
user_service = UserService()
user_validation = Validation()
access_token_bearer = AccessTokenBearer()
REFRESH_TOKEN_EXPIRY = 2


@auth_router.post("/emailvarfication", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def Emailvarfication(user_data: Emailvalidation, session: AsyncSession = Depends(get_session)):

    email = user_data.email.lower()
    user_exists_with_email = await user_service.exist_email(email, session)

    if user_exists_with_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email already exists")

    code = random_code()

    message = MessageSchema(
        subject="Email Verification Code",
        recipients=[email],
        body=(
            f"Hello,\n\n"
            f"Thank you for registering with us!\n\n"
            f"To verify your email address, please use the following One-Time Password (OTP):\n\n"
            f"OTP: {code}\n\n"
            f"This code is valid for the next 2 minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\n"
            f"Your Team"
        ),
        subtype="plain"
    )

    fm = FastMail(mail_config)
    try:
        await fm.send_message(message)
        ist = pytz.timezone("Asia/Kolkata")
        utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        local_time = utc_time.astimezone(ist)
        local_time_naive = local_time.replace(tzinfo=None)

        OTP = OTPVerification(
            email=email,
            otp=str(code),
            created_at=local_time_naive,
            updated_at=local_time_naive
        )

        session.add(OTP)
        await session.commit()
        await session.refresh(OTP)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "OTP has been successfully sent to your registered email address.",
            })

    except Exception as e:
        import logging
        logging.error(f"Error sending email or saving OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")


@auth_router.post("/ResendOTP", status_code=status.HTTP_201_CREATED)
async def Resendotp(user_data: Emailvalidation, session: AsyncSession = Depends(get_session)):
    email = user_data.email.lower()

    result = await session.execute(select(OTPVerification).where(OTPVerification.email == email))
    existing_otp = result.scalars().first()

    if existing_otp is None:
        raise HTTPException(
            status_code=404, detail="Email not registered for verification.")

    code = random_code()

    message = MessageSchema(
        subject="Email Verification Code",
        recipients=[email],
        body=(
            f"Hello,\n\n"
            f"Thank you for registering with us!\n\n"
            f"To verify your email address, please use the following One-Time Password (OTP):\n\n"
            f"OTP: {code}\n\n"
            f"This code is valid for the next 2 minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\n"
            f"Your Team"
        ),
        subtype="plain"
    )

    try:
        fm = FastMail(mail_config)
        await fm.send_message(message)

        ist = pytz.timezone("Asia/Kolkata")
        utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        local_time = utc_time.astimezone(ist).replace(tzinfo=None)

        existing_otp.otp = str(code)
        existing_otp.created_at = local_time
        existing_otp.updated_at = local_time

        await session.commit()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "OTP has been successfully resent to your registered email address.",
                     "email": email}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send email")


@auth_router.post("/OTPverification", status_code=status.HTTP_201_CREATED)
async def OTPverifications(user_data: OTPverification, session: AsyncSession = Depends(get_session)):
    email = user_data.email.lower()
    OTP = user_data.OTP

    is_OTP = await user_validation.validate_otp(OTP, session)
    if not is_OTP:
        raise HTTPException(
            status_code=400, detail="Invalid OTP: must be a 6-digit number.")

    result = await session.execute(
        select(OTPVerification).where(
            and_(
                OTPVerification.email == email,
                OTPVerification.otp == OTP
            )
        )
    )

    existing_otp = result.scalars().first()

    if existing_otp is None:
        raise HTTPException(status_code=404, detail="Invalid email or OTP.")

    ist = pytz.timezone("Asia/Kolkata")
    utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
    now_ist = utc_time.astimezone(ist).replace(tzinfo=None)

    if now_ist - existing_otp.created_at > timedelta(minutes=1):
        raise HTTPException(
            status_code=400, detail="OTP has expired. Please request a new one.")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "OTP has been successfully verified.",
            "email": email
        }
    )


@auth_router.post("/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user_account(user_data: UserCreate, session: AsyncSession = Depends(get_session)):

    email = user_data.email.lower()
    username = user_data.username.lower()

    is_username = await user_validation.validate_text(username, session)
    if not is_username:
        raise HTTPException(
            status_code=400, detail="Invalid username: only letters and spaces are allowed.")

    is_password = await user_validation.validate_password(user_data.password, session)
    if not is_password:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters, contain 1 uppercase, 1 lowercase, 1 digit, and 1 special character.")

    user_exists_with_email = await user_service.exist_email(email, session)
    user_exists_with_username = await user_service.exist_username(username, session)

    if user_exists_with_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email already exists")
    if user_exists_with_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Username already exists")
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    new_user = await user_service.create_user(user_data, session)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Registration successful! Please log in.",
        }
    )


@auth_router.post('/login')
async def login_user(login_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    email = login_data.email
    password = login_data.password

    if email == "admin@gmail.com" and password == "admin":
        admin_access_token = create_access_token(
            user_data={
                'admin_username': 'Admin',
                'admin_role': 'admin'
            }
        )
        admin_refresh_token = create_access_token(
            user_data={
                'admin_username': 'Admin',
                'admin_role': 'admin'
            },
            refresh=True,
            expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
        )

        if isinstance(admin_access_token, bytes):
            admin_access_token = admin_access_token.decode("utf-8")
        if isinstance(admin_refresh_token, bytes):
            admin_refresh_token = admin_refresh_token.decode("utf-8")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Login successful",
                "admin_access_token": admin_access_token,
                "admin_refresh_token": admin_refresh_token,
                "admin_username": 'Admin',
                'admin_role': 'admin'
            }
        )

    user = await user_service.get_user_by_email(email, session)
    if user is not None:
        password_valid = verify_password(password, user.password)

        if password_valid:
            user.login_status = True
            session.add(user)
            await session.commit()
            await session.refresh(user)

            user_access_token = create_access_token(
                user_data={
                    'email': user.email,
                    'user_id': str(user.user_id),
                    'user_role': str(user.role)
                }
            )

            user_refresh_token = create_access_token(
                user_data={
                    'user_email': user.email,
                    'user_id': str(user.user_id),
                    'user_role': str(user.role)
                },
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
            )

            if isinstance(user_access_token, bytes):
                user_access_token = user_access_token.decode("utf-8")
            if isinstance(user_refresh_token, bytes):
                user_refresh_token = user_refresh_token.decode("utf-8")

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Login successful",
                    "user_access_token": user_access_token,
                    "user_refresh_token": user_refresh_token,
                    "user_id": str(user.user_id),
                    "user_name": str(user.username),
                    'user_role': str(user.role)
                }
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid Email or Password"
    )


@auth_router.put("/user_logout/{user_id}")
async def logout_agent(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_details: dict = Depends(access_token_bearer),
):

    result = await session.execute(select(usertable).where(usertable.user_id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.login_status = False
    session.add(user)
    await session.commit()

    return JSONResponse(status_code=200, content={"message": "User logged out successfully."})


@auth_router.post("/user_refresh_token")
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data=token_details['user']
        )

        if isinstance(new_access_token, bytes):
            new_access_token = new_access_token.decode('utf-8')

        return JSONResponse(content={"access_token": new_access_token})
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid or expired token")


@auth_router.post("/blogcreate/{user_id}", response_model=dict)
async def create_blog(
    user_id: UUID,
    description: str = Form(...),
    photo: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
    user_details=Depends(access_token_bearer)
):
    try:
        is_description = await user_validation.description(description, session)
        if not is_description:
            raise HTTPException(
                status_code=400,
                detail="Invalid description. Only letters and spaces are allowed."
            )
        is_photo = await user_validation.validate_file_type(photo, session)
        if not is_photo:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload a .jpg, .jpeg, or .png image."
            )

        blog_data = {
            "description": description,
        }

        created_blog = await user_service.create_bloge(user_id, blog_data, photo, session)

        logger.info("Blog created successfully.")
        return JSONResponse(
            status_code=201,
            content={"message": "Your blog has been published successfully."}
        )

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error in create_blog: {str(e)}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error. Please try again later."
        )




@auth_router.get("/bloge_list_profile", response_model=dict)
async def bloge_list_profile(session: AsyncSession = Depends(get_session)):
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
    

@auth_router.get("/bloge_list", response_model=dict)
async def bloge_list(session: AsyncSession = Depends(get_session)):
    try:

        result = await session.execute(
            select(
                BlogCreate.blog_uid,
                BlogCreate.photo,
                BlogCreate.comments,       
                BlogCreate.description,
                BlogCreate.user_id,
                BlogCreate.likes,
                BlogCreate.dislikes,
                usertable.username,
                usertable.image
            ).join(usertable, BlogCreate.user_id == usertable.user_id)
            .where(BlogCreate.delete_status == False)
        )

        blog_data = result.all()

        bloges = []
        for row in blog_data:
            (
                blog_uid,
                photo,
                comments,
                description,
                user_id,
                likes,
                dislikes,
                username,
                user_image
            ) = row

            bloges.append({
                "blog_uid": str(blog_uid),
                "photo": photo,
                "description": description,
                "user_id": str(user_id),
                "username": username,
                "user_image": user_image,
                "total_likes": len(likes) if likes else 0,
                "total_dislikes": len(dislikes) if dislikes else 0,
                "likes": [str(uid) for uid in likes] if likes else [],
                "dislikes": [str(uid) for uid in dislikes] if dislikes else [],
                "comments": comments if comments else []
            })

        return JSONResponse(status_code=200, content={"bloges": bloges})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching bloges details: {str(e)}"
        )


@auth_router.post("/like/{user_id}/{blog_uid}", response_model=dict)
async def like_blog(
    user_id: UUID,
    blog_uid: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await session.execute(
            select(BlogCreate).where(BlogCreate.blog_uid == blog_uid)
        )
        blog_row = result.first()
        if not blog_row:
            raise HTTPException(status_code=404, detail="Blog not found")

        blog: BlogCreate = blog_row[0]

        if user_id in blog.likes:
            return JSONResponse(
                status_code=200,
                content={"message": "User already liked this blog"}
            )
        likes = blog.likes.copy()
        likes.append(user_id)
        blog.likes = likes

        if user_id in blog.dislikes:
            dislikes = blog.dislikes.copy()
            dislikes.remove(user_id)
            blog.dislikes = dislikes

        session.add(blog)
        await session.commit()
        await session.refresh(blog)

        return JSONResponse(
            status_code=201,
            content={"message": "Blog liked successfully"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@auth_router.post("/dislike/{user_id}/{blog_uid}", response_model=dict)
async def dislike_blog(
    user_id: UUID,
    blog_uid: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await session.execute(
            select(BlogCreate).where(BlogCreate.blog_uid == blog_uid)
        )
        blog_row = result.first()
        if not blog_row:
            raise HTTPException(status_code=404, detail="Blog not found")

        blog: BlogCreate = blog_row[0]

        if user_id in blog.dislikes:
            return JSONResponse(
                status_code=200,
                content={"message": "User already disliked this blog"}
            )

        dislikes = blog.dislikes.copy()
        dislikes.append(user_id)
        blog.dislikes = dislikes

        if user_id in blog.likes:
            likes = blog.likes.copy()
            likes.remove(user_id)
            blog.likes = likes

        await session.commit()
        await session.refresh(blog)

        return JSONResponse(
            status_code=201,
            content={"message": "Blog disliked successfully"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@auth_router.post("/comment/{user_id}/{blog_uid}", response_model=dict)
async def add_comment(
    user_id: UUID,
    blog_uid: UUID,
    comment_data: commentRequest,
    session: AsyncSession = Depends(get_session)
):
    try:

        result = await session.execute(select(usertable).where(usertable.user_id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        blog_result = await session.execute(select(BlogCreate).where(BlogCreate.blog_uid == blog_uid))
        blog_row = blog_result.first()
        if not blog_row:
            raise HTTPException(status_code=404, detail="Blog not found")

        ist = pytz.timezone("Asia/Kolkata")
        utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        local_time = utc_time.astimezone(ist)
        local_time_naive = local_time.replace(tzinfo=None)

        blog: BlogCreate = blog_row[0]

        new_comment = Comment(
            comment_uid=uuid.uuid4(),
            user_id=user_id,
            username=user.username,
            user_photo=user.image,
            comment=comment_data.comments,
            timestamp=local_time_naive
        )

        new_comment_dict = jsonable_encoder(new_comment)

        comments = blog.comments.copy()
        comments.append(new_comment_dict)
        blog.comments = comments

        session.add(blog)
        await session.commit()
        await session.refresh(blog)

        return JSONResponse(
            status_code=201,
            content={"message": "Comment added successfully"}
        )

    except Exception as e:
        tb_str = traceback.format_exc()
        print("Exception traceback:", tb_str)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@auth_router.get("/user_profile/{userId}", response_model=list[dict])
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


@auth_router.put("/profile_create/{userId}", response_model=dict)
async def update_profile(userId: UUID,
                         username: str = Form(...),
                         email: EmailStr = Form(...),
                         image_url: Optional[str] = Form(None),
                         image: Optional[UploadFile] = File(None),
                         session: AsyncSession = Depends(get_session)):

    is_username = await user_validation.validate_text(username, session)
    if not is_username:
        raise HTTPException(
            status_code=400, detail="Invalid username: only letters and spaces are allowed.")

    is_email = await user_validation.validate_email(email, session)
    if not is_email:
        raise HTTPException(status_code=400, detail="Invalid email format.")

    is_file = await user_validation.validate_file_type(image, session)
    if not is_file:
        raise HTTPException(
            status_code=400, detail="Invalid file type: only .jpg, .jpeg, or .png files are allowed.")

    user_exists = await user_service.exist_user_id(userId, session)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_data = ProfileCreateRequest(
        username=username,
        email=email,
    )

    update_user = await user_service.profile_update(user_data, userId, image, session)

    return JSONResponse(status_code=200, content={"message": "Profile updated successfully"})


@auth_router.get("/fetch_blog_details_for_editing/{BlogeID}", response_model=dict)
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


@auth_router.put("/Bloge_updation/{BlogeID}", response_model=dict)
async def Bloge_updation(
    BlogeID: UUID,
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    is_description = await user_validation.description(description, session)
    if not is_description:
        raise HTTPException(
            status_code=400,
            detail="Invalid description. Only letters and spaces are allowed."
        )

    if image:
        is_photo = await user_validation.validate_file_type(image, session)
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

    created_blog = await user_service.bloge_updation(BlogeID, blog_update_data, image, session)

    return JSONResponse(status_code=200, content={"message": "Blog updated successfully"})
