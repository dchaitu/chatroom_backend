from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Request

from constants import UPLOAD_DIR

# from constants import get_current_user

print("Starting", flush=True)
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import boto3
import time


print("External Imports", flush=True)
from routers import room_routes, user_routes, admin_routes, reply_routes, reaction_routes, request_routes, message_routes
print("Internal Imports", flush=True)
dynamodb = boto3.client('dynamodb')

print("List Dynamodb Tables", flush=True)
app = FastAPI()
os.makedirs(UPLOAD_DIR, exist_ok=True)
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://n1yahnot4c.execute-api.us-east-1.amazonaws.com/dev",
]


# Include routers
app.include_router(room_routes.router)
app.include_router(user_routes.router)
app.include_router(admin_routes.router)
app.include_router(reply_routes.router)
app.include_router(reaction_routes.router)
app.include_router(request_routes.router)
app.include_router(message_routes.router)

# Consider this as static files storing uploaded files
app.mount("/uploads",StaticFiles(directory="uploads"),name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post('/upload')
async def upload_file_with_message(file: UploadFile = File(...)):
    content = await file.read()
    print(content)


# async def create_message_with_file(
#     content: Optional[str] = Form(None),
#     file: Optional[UploadFile] = File(None),
#     username: str = Depends(get_current_user)  # if you have auth
# ):
#     file_url = None
#     if file:
#         file_ext = os.path.splitext(file.filename)[1]
#         print("File Details ",os.path.splitext(file.filename))
#         saved_filename = f"{uuid.uuid4()}{file_ext}"
#         file_path = os.path.join(UPLOAD_DIR, saved_filename)
#
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#
#         file_url = f"/{UPLOAD_DIR}/{saved_filename}"  # return path or S3 URL if uploading to cloud
#
#     # Save the message in DB (DynamoDB, PynamoDB, etc.)
#     message = {
#         "message_id": str(uuid.uuid4()),
#         "username": username,
#         "content": content,
#         "file_url": file_url,
#     }
#
#     print("Saved message:", message)
#     return message

@app.get("/hello")
def hello():
    return {"message":"Hello World"}

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def check_header(request: Request, callback):
    header = request.headers.get("X-User-Type")
    if header is None:
        return JSONResponse(status_code=401, content={"detail": "Missing X-User-Type header"})
    if header != "cool":
        return JSONResponse(status_code=401, content={"detail": "Not cool enough"})
    return await callback(request)


def handler(event, context):
    print("Lambda handler started")
    asgi_handler = Mangum(app)
    return asgi_handler(event, context)


print("Loaded Main Handler", flush=True)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rest_api:app", host="localhost", port=8080, reload=True)
