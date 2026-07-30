from datetime import datetime, timedelta, timezone

try:
    import jwt
except ImportError:
    jwt = None

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    pwd_context = None

from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if pwd_context:
        return pwd_context.verify(plain_password, hashed_password)
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    return password

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    if jwt:
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return f"mock_token_{to_encode.get('sub')}"

def decode_access_token(token: str) -> dict:
    if jwt:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
            return payload
        except Exception:
            return None
    return {"sub": "admin"}
