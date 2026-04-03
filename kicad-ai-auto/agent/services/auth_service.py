"""
JWT Authentication Service

Provides:
- User registration with bcrypt password hashing
- JWT access + refresh token generation
- Token refresh with rotation
- Role-based access control (admin, editor, viewer)
- User management (CRUD)

Requires: PyJWT, bcrypt
Falls back to HMAC-based tokens if PyJWT unavailable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---- Configuration ----

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ---- Try importing PyJWT ----

try:
    import jwt as pyjwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    logger.info("PyJWT not installed, using HMAC-based tokens")

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    logger.info("bcrypt not installed, using SHA256 hash fallback")


# ---- Data Models ----

@dataclass
class User:
    id: str
    username: str
    email: str
    password_hash: str
    role: str = "editor"  # admin, editor, viewer
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    projects: List[str] = field(default_factory=list)  # project IDs


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


@dataclass
class TokenPayload:
    user_id: str
    username: str
    role: str
    exp: float
    iat: float
    type: str  # "access" or "refresh"
    jti: str = ""  # JWT ID for refresh token rotation


# ---- Password Hashing ----

def hash_password(password: str) -> str:
    if HAS_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashlib.sha256(password.encode() + JWT_SECRET.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False
    expected = hashlib.sha256(password.encode() + JWT_SECRET.encode()).hexdigest()
    return hmac.compare_digest(expected, password_hash)


# ---- Token Management ----

def _encode_token(payload: Dict[str, Any]) -> str:
    if HAS_JWT:
        return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # Fallback: HMAC-SHA256 with JSON payload
    header = json.dumps({"alg": "HS256", "typ": "JWT"})
    body = json.dumps(payload)
    header_b64 = _b64url_encode(header.encode())
    body_b64 = _b64url_encode(body.encode())
    signing_input = f"{header_b64}.{body_b64}"
    sig = hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).hexdigest()
    return f"{signing_input}.{sig}"


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    if HAS_JWT:
        try:
            return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except Exception:
            return None
    # Fallback: verify HMAC
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input = f"{parts[0]}.{parts[1]}"
    expected_sig = hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, parts[2]):
        return None
    try:
        body = _b64url_decode(parts[1])
        return json.loads(body)
    except Exception:
        return None


def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ---- Auth Service ----

class AuthService:
    """
    JWT-based authentication service.

    Supports both SQLite (preferred) and JSON file persistence.
    For production, use SQLite by setting use_database=True.
    """

    def __init__(self, data_file: Optional[str] = None, use_database: bool = True):
        self._users: Dict[str, User] = {}  # user_id -> User (in-memory cache)
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._refresh_tokens: Dict[str, str] = {}  # jti -> user_id
        self._data_file = data_file
        self._use_database = use_database
        self._db = None

        if use_database:
            try:
                from services.database import db
                self._db = db
                logger.info("AuthService using SQLite database")
            except ImportError:
                logger.warning("Database service not available, falling back to JSON")
                self._use_database = False

        self._load_users()

    def _load_users(self):
        """Load users from database or JSON file."""
        if self._use_database and self._db:
            # Load from SQLite - users are queried on demand, but we cache them
            users = self._db.list_users(limit=1000)
            for udata in users:
                user = User(
                    id=udata['id'],
                    username=udata['username'],
                    email=udata['email'],
                    password_hash=udata['password_hash'],
                    role=udata.get('role', 'editor'),
                    is_active=bool(udata.get('is_active', 1)),
                    created_at=udata.get('created_at', time.time()),
                    last_login=udata.get('last_login'),
                    projects=udata.get('projects', [])
                )
                self._users[user.id] = user
                self._username_index[user.username] = user.id
            logger.info(f"Loaded {len(self._users)} users from database")
            return

        # Fallback to JSON file
        if not self._data_file or not os.path.exists(self._data_file):
            return
        try:
            with open(self._data_file, "r") as f:
                data = json.load(f)
            for udata in data.get("users", []):
                user = User(**udata)
                self._users[user.id] = user
                self._username_index[user.username] = user.id
            logger.info(f"Loaded {len(self._users)} users from {self._data_file}")
        except Exception as e:
            logger.warning(f"Failed to load users: {e}")

    def _save_users(self):
        """Save users to database or JSON file."""
        if self._use_database and self._db:
            # Database saves on each operation, no bulk save needed
            return

        # Fallback to JSON file
        if not self._data_file:
            return
        try:
            data = {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "password_hash": u.password_hash,
                        "role": u.role,
                        "is_active": u.is_active,
                        "created_at": u.created_at,
                        "last_login": u.last_login,
                        "projects": u.projects,
                    }
                    for u in self._users.values()
                ]
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save users: {e}")

    # ---- Registration ----

    def register(self, username: str, email: str, password: str, role: str = "editor") -> Dict[str, Any]:
        if username in self._username_index:
            return {"error": "Username already exists"}

        if len(password) < 6:
            return {"error": "Password must be at least 6 characters"}

        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )

        # Save to database if available
        if self._use_database and self._db:
            if not self._db.create_user(user_id, username, email, password_hash, role):
                return {"error": "Failed to create user in database"}

        # Update in-memory cache
        self._users[user_id] = user
        self._username_index[username] = user_id
        self._save_users()  # For JSON fallback

        logger.info(f"User registered: {username} ({role})")
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role,
        }

    # ---- Login ----

    def login(self, username: str, password: str) -> Dict[str, Any]:
        user_id = self._username_index.get(username)
        if not user_id:
            return {"error": "Invalid credentials"}

        user = self._users.get(user_id)
        if not user or not user.is_active:
            return {"error": "Invalid credentials"}

        if not verify_password(password, user.password_hash):
            return {"error": "Invalid credentials"}

        # Update last login
        user.last_login = time.time()
        self._save_users()

        # Generate token pair
        tokens = self._generate_tokens(user)
        logger.info(f"User logged in: {username}")
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
            **tokens.__dict__,
        }

    # ---- Token Management ----

    def _generate_tokens(self, user: User) -> TokenPair:
        now = time.time()

        # Access token
        access_payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "iat": now,
            "type": "access",
        }
        access_token = _encode_token(access_payload)

        # Refresh token with JTI
        jti = secrets.token_hex(16)
        refresh_payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            "iat": now,
            "type": "refresh",
            "jti": jti,
        }
        refresh_token = _encode_token(refresh_payload)

        # Store refresh token JTI
        self._refresh_tokens[jti] = user.id

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh_token(self, refresh_token_str: str) -> Dict[str, Any]:
        payload = _decode_token(refresh_token_str)
        if not payload:
            return {"error": "Invalid refresh token"}

        if payload.get("type") != "refresh":
            return {"error": "Not a refresh token"}

        jti = payload.get("jti", "")
        if jti not in self._refresh_tokens:
            return {"error": "Refresh token revoked or expired"}

        user_id = payload.get("user_id")
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return {"error": "User not found or inactive"}

        # Rotate: revoke old refresh token
        del self._refresh_tokens[jti]

        # Generate new token pair
        tokens = self._generate_tokens(user)
        return tokens.__dict__

    def revoke_refresh_token(self, jti: str) -> bool:
        return self._refresh_tokens.pop(jti, None) is not None

    # ---- Token Verification ----

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        payload = _decode_token(token)
        if not payload:
            return None
        if payload.get("type") != "access":
            return None
        if payload.get("exp", 0) < time.time():
            return None
        return payload

    # ---- User Management ----

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = self._users.get(user_id)
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "projects": user.projects,
        }

    def list_users(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in self._users.values()
        ]

    def update_user(self, user_id: str, **updates) -> Dict[str, Any]:
        user = self._users.get(user_id)
        if not user:
            return {"error": "User not found"}

        allowed = {"email", "role", "is_active"}
        for key, value in updates.items():
            if key in allowed:
                setattr(user, key, value)

        self._save_users()
        return {"status": "ok", "user_id": user_id}

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        user = self._users.get(user_id)
        if not user:
            return {"error": "User not found"}

        if not verify_password(old_password, user.password_hash):
            return {"error": "Invalid old password"}

        if len(new_password) < 6:
            return {"error": "Password must be at least 6 characters"}

        user.password_hash = hash_password(new_password)
        self._save_users()
        return {"status": "ok"}

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        user = self._users.get(user_id)
        if not user:
            return {"error": "User not found"}

        del self._users[user_id]
        self._username_index.pop(user.username, None)
        self._save_users()
        return {"status": "ok"}

    # ---- Role-Based Access ----

    def has_permission(self, user_id: str, required_role: str) -> bool:
        role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}
        user = self._users.get(user_id)
        if not user:
            return False
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 99)
        return user_level >= required_level

    def get_user_count(self) -> int:
        return len(self._users)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        data_file = os.path.join(data_dir, "users.json")
        _auth_service = AuthService(data_file)
    return _auth_service
