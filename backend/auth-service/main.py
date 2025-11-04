"""Auth Service (FastAPI)

Provides minimal user registration and JWT based authentication.
Uses Argon2 for password hashing and python‑jose for token handling.
In a production setting this would be backed by a persistent DB and
integrated with Keycloak, but for the initial scaffold we keep an
in‑memory store so the UI can obtain a token for subsequent calls.
"""

from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
import argon2

# ---------------------------------------------------------------------------
# Configuration (would normally come from env vars)
# ---------------------------------------------------------------------------
SECRET_KEY = "change_this_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

app = FastAPI(title="GPUBROKER Auth Service")

# Simple in‑memory user store: username -> {hashed_password, role}
_users_db: Dict[str, Dict[str, str]] = {}

pwd_hasher = argon2.PasswordHasher()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _create_refresh_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": username, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except argon2.exceptions.VerifyMismatchError:
        return False


def _get_user(username: str):
    return _users_db.get(username)


def authenticate_user(username: str, password: str):
    user = _get_user(username)
    if not user:
        return False
    if not _verify_password(password, user["hashed_password"]):
        return False
    return True


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(username: str, password: str, role: str = "user"):
    if username in _users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    _users_db[username] = {
        "hashed_password": pwd_hasher.hash(password),
        "role": role,
    }
    return {"msg": "User created"}


@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = _create_access_token({"sub": form_data.username})
    refresh_token = _create_refresh_token(form_data.username)
    return {"access_token": access_token, "refresh_token": refresh_token}


def get_current_user(token: str = Depends(OAuth2PasswordRequestForm)):
    # Placeholder for dependency injection; real implementation would decode token.
    raise NotImplementedError()


"""
⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
We do NOT mock, bypass, or invent data.
We use ONLY real servers, real APIs, and real data.
This codebase follows principles of truth, simplicity, and elegance.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from typing import Optional
import uuid
import asyncio
import asyncpg
import os

app = FastAPI(
    title="GPUBROKER Auth Service",
    description="Authentication, authorization, and user management service",
    version="1.0.0",
    docs_url="/docs",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security setup
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-secret-key-here"
)  # Use Vault in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost/gpubroker"
)


# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    organization: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class User(BaseModel):
    id: str
    email: str
    full_name: str
    organization: Optional[str]
    is_active: bool
    created_at: datetime


# Database connection pool
db_pool = None


@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        print("✅ Connected to PostgreSQL database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool"""
    if db_pool:
        await db_pool.close()


# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Extract and validate JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        async with db_pool.acquire() as conn:
            user_record = await conn.fetchrow(
                "SELECT id, email, full_name, organization, is_active, created_at FROM users WHERE email = $1",
                email,
            )
            if not user_record:
                raise HTTPException(status_code=401, detail="User not found")

            return User(**dict(user_record))
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "GPUBROKER Auth Service",
        "status": "running",
        "version": "1.0.0",
    }


@app.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)

    try:
        async with db_pool.acquire() as conn:
            # Check if user already exists
            existing_user = await conn.fetchrow(
                "SELECT email FROM users WHERE email = $1", user_data.email
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")

            # Create new user
            user_record = await conn.fetchrow(
                """
                INSERT INTO users (id, email, password_hash, full_name, organization, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, email, full_name, organization, is_active, created_at
            """,
                user_id,
                user_data.email,
                hashed_password,
                user_data.full_name,
                user_data.organization,
                True,
                datetime.utcnow(),
            )

            return User(**dict(user_record))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/login", response_model=Token)
async def login_user(login_data: UserLogin):
    """Authenticate user and return JWT tokens"""
    try:
        async with db_pool.acquire() as conn:
            user_record = await conn.fetchrow(
                "SELECT email, password_hash, is_active FROM users WHERE email = $1",
                login_data.email,
            )

            if not user_record or not verify_password(
                login_data.password, user_record["password_hash"]
            ):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            if not user_record["is_active"]:
                raise HTTPException(status_code=401, detail="Account disabled")

            # Create access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_record["email"]}, expires_delta=access_token_expires
            )

            # Create refresh token (longer expiry)
            refresh_token_expires = timedelta(days=7)
            refresh_token = create_access_token(
                data={"sub": user_record["email"], "type": "refresh"},
                expires_delta=refresh_token_expires,
            )

            return Token(access_token=access_token, refresh_token=refresh_token)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        async with db_pool.acquire() as conn:
            await conn.fetchrow("SELECT 1")

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
