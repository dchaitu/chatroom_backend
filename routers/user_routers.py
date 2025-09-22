from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status

from constants import get_current_user, hash_password, create_access_token
from models import User
from schemas import UserCreate, UserLogin, UserSchema, UpdateUserDTO

router = APIRouter(tags=['User'])

@router.post("/register/", status_code=201)
def register_user(user_info: UserCreate):
    print(f"Received registration request: {user_info}", flush=True)

    # Skip reCAPTCHA for testing - add back later
    # is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
    # if not is_valid_captcha:
    #     raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

    try:
        existing_user = User.get(user_info.username)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )
    except User.DoesNotExist:
        pass

    hashed_password = hash_password(user_info.password)
    user = User(
        username=user_info.username,
        password=hashed_password,
        fullname=user_info.fullname,
        email=user_info.email,
        rooms=[],
        avatar=user_info.avatar,
        pic_url=user_info.pic_url
    )
    user.save()

    return {
        "message": f"User created successfully: {user_info.username}",
        "status_code": status.HTTP_201_CREATED,
    }


@router.post("/login/", status_code=200)
def login(user_info: UserLogin):

    try:
        user = User.get(user_info.username)
    except User.DoesNotExist:
        raise HTTPException(detail="Invalid username", status_code=401)

    if user.password != hash_password(user_info.password):
        raise HTTPException(detail="Invalid password", status_code=401)

    access_token = create_access_token(user_info.username)
    refresh_token = create_access_token(user_info.username, timedelta(days=30))
    print("access_token ", access_token)
    print("refresh_token ", refresh_token)
    return {
        "message": f"User logged in successfully: {user_info.username}",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.get("/user/", response_model=UserSchema)
async def get_user_profile(username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
        print("get user_data", user)
        return user
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

@router.put("/user/",response_model=UserSchema)
async def update_user_profile(update_user: UpdateUserDTO, username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
        if update_user.avatar:
            user.avatar = update_user.avatar
        if update_user.email:
            user.email = update_user.email
        if update_user.fullname:
            user.fullname = update_user.fullname
        if update_user.pic_url:

            user.pic_url = update_user.pic_url

        user.save()
        print("user_data", user)
        print("user_pic_url ", user.pic_url)
        return user
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/user-details/{username}", response_model=UserSchema)
async def get_user_profile(username: str):
    try:
        user = User.get(username)

        # print("user_data", user_data)
        return user
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")