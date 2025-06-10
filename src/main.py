
from fastapi import FastAPI,WebSocket,Depends,WebSocketDisconnect,Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.db.database import init_db
from src.admin_side.routes import admin_router
from src.user_side.routes import auth_router
from fastapi.responses import Response

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting...")
    await init_db()
    yield
    print("Server is stopping...")


app = FastAPI(lifespan=lifespan)

# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# app.include_router(admin_router, prefix="/admin_auth", tags=["Admin Authentication"])


origins = [
    "http://localhost:5173",        
    "https://www.mindmingle.fun", 
    "https://api.mindmingle.fun",
    "https://mindmingle-backend.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add explicit preflight handler for OPTIONS requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    origin = request.headers.get("origin")
    request_headers = request.headers.get("access-control-request-headers", "*")
    headers = {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": request_headers,
        "Access-Control-Allow-Credentials": "true",
    }
    return Response(status_code=204, headers=headers)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/admin_auth", tags=["Admin Authentication"])