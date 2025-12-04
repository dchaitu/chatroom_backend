import time
from rest_api import app
from fastapi.responses import JSONResponse, Response
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"Request: {request.method} {request.url} - completed in {process_time:.4f} seconds")
    print(f"Response: {response}")
    return response

@app.middleware("http")
async def check_header(request: Request, callback):
    header = request.headers.get("X-User-Type")
    if header is None:
        return JSONResponse(status_code=401, content={"detail": "Missing X-User-Type header"})
    if header != "cool":
        return JSONResponse(status_code=401, content={"detail": "Not cool enough"})
    return await callback(request)

class CheckUserTypeHeader(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint)-> Response:
        header = request.headers.get("X-User-Type")
        if header is None:
            return JSONResponse(status_code=401, content={"detail": "Missing X-User-Type header"})
        if header != "cool":
            return JSONResponse(status_code=401, content={"detail": "Not cool enough"})
        return await call_next(request)

class CountRequests(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint)-> Response:
        print("Requests: ", request)
        response =  await call_next(request)
        print("Responses: ", response)
        return response