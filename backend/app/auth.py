import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import tx

SECRET = os.environ["JWT_SECRET"]
bearer = HTTPBearer()


def make_token(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": str(user["id"]), "exp": exp}, SECRET, algorithm="HS256")


def check_login(email: str, password: str) -> dict:
    with tx() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
        user = cur.fetchone()
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Wrong email or password")
    return user


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        payload = jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Please log in again")

    with tx() as cur:
        cur.execute("SELECT id, name, email, role FROM users WHERE id = %s", (uid,))
        user = cur.fetchone()
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


def manager_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "manager":
        raise HTTPException(403, "Managers only")
    return user