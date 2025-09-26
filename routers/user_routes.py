from fastapi import APIRouter, Depends
from dependencies import storage

router = APIRouter(tags=['User'])

from constants import get_current_user
from schemas import UserCreate, UserLogin, UserSchema, UpdateUserDTO

@router.post("/register/", status_code=201)
async def register_user(user_info: UserCreate):
    await storage.register_user(user_info)


@router.post("/login/", status_code=200)
async def login(user_info: UserLogin):
    return await storage.login(user_info)


@router.get("/user/", response_model=UserSchema)
async def get_user_profile(username: str = Depends(get_current_user)):
    print("printing username", username)
    return await storage.get_user_profile(username)

@router.put("/user/",response_model=UserSchema)
async def update_user_profile(update_user: UpdateUserDTO, username: str = Depends(get_current_user)):
    return await storage.update_user_profile(update_user, username)


@router.get("/user-details/", response_model=list[UserSchema])
async def get_all_users():
    return await storage.get_all_users()