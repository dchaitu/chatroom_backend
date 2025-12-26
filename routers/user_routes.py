from fastapi import APIRouter, Depends
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface

router = APIRouter(tags=['User'])

from constants import get_current_user
from schemas import UserCreate, UserLogin, UserSchema, UpdateUserDTO

@router.post("/register", status_code=201)
async def register_user(user_info: UserCreate, storage: StorageInterface = Depends(get_storage)):
    await storage.register_user(user_info)


@router.post("/login", status_code=200)
async def login(user_info: UserLogin, storage: StorageInterface = Depends(get_storage)):
    return await storage.login(user_info)


@router.get("/user/", response_model=UserSchema)
async def get_user_profile(username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    print("printing username", username)
    return await storage.get_user_profile(username)

@router.put("/user/",response_model=UserSchema)
async def update_user_profile(update_user: UpdateUserDTO, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.update_user_profile(update_user, username)


@router.get("/user-details/", response_model=list[UserSchema])
async def get_all_users(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_users()