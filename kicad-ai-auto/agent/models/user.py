"""
用户认证与 Token 管理数据库模型
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

DB_PATH = "data/users.db"


def get_db():
    """获取数据库连接"""
    import os
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            username TEXT,
            token_balance INTEGER DEFAULT 1000,
            is_test_mode BOOLEAN DEFAULT FALSE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Token 消耗记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            model_used TEXT,
            is_test BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 充值记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_method TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 管理员配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 初始化默认管理员配置
    default_configs = [
        ("virtual_model_name", "DeepEDA大模型"),
        ("default_model", "deepseek"),
        ("token_ai_generate", "800"),
        ("token_ai_chat", "500"),
        ("token_schematic_analyze", "600"),
        ("model_deepseek_cost", "800"),
        ("model_kimi_cost", "1000"),
    ]
    for key, value in default_configs:
        cursor.execute(
            "INSERT OR IGNORE INTO admin_config (config_key, config_value) VALUES (?, ?)",
            (key, value)
        )

    # 不再创建默认管理员账号 - 首次启动时由用户注册
    # 如果需要管理员权限，用户注册后可在数据库中手动设置 is_admin=1
    pass

    conn.commit()
    conn.close()
    logger.info("User database initialized")


def _try_bcrypt_check(password: str, password_hash: str) -> bool:
    """使用 bcrypt 验证密码"""
    import bcrypt
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _do_bcrypt_hash(password: str) -> str:
    """使用 bcrypt 生成密码哈希"""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def hash_password(password: str) -> str:
    """密码哈希 - 使用 bcrypt（安全的专用密码哈希算法）"""
    return _do_bcrypt_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码 - 支持 bcrypt 和旧格式迁移"""
    # bcrypt 格式：以 $2` 开头
    if password_hash.startswith("$2"):
        return _try_bcrypt_check(password, password_hash)

    # 新格式（salt:hash）- SHA-256 带盐值（较少见）
    if ":" in password_hash:
        try:
            salt, stored_hash = password_hash.split(":", 1)
            import secrets
            salted = f"{salt}{password}".encode()
            return hashlib.sha256(salted).hexdigest() == stored_hash
        except (ValueError, AttributeError):
            return False

    # 旧格式（无盐值纯 SHA-256）
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def create_user(email: str, password: str, username: Optional[str] = None) -> Dict[str, Any]:
    """创建新用户"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        cursor.execute(
            """INSERT INTO users (email, password_hash, username, token_balance)
               VALUES (?, ?, ?, 1000)""",
            (email, password_hash, username or email.split('@')[0])
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"id": user_id, "email": email, "username": username or email.split('@')[0]}
    except sqlite3.IntegrityError:
        raise ValueError("邮箱已被注册")
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """通过邮箱获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """通过ID获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, username, token_balance, is_test_mode, is_admin, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def verify_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """验证用户登录"""
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        # 如果是旧格式密码（不以 $2 开头），升级为 bcrypt
        if not user["password_hash"].startswith("$2"):
            conn = get_db()
            cursor = conn.cursor()
            new_hash = hash_password(password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
            conn.commit()
            conn.close()
            logger.info(f"Migrated password hash for user {email} to bcrypt")
        return user
    return None


def get_token_balance(user_id: int) -> int:
    """获取用户Token余额"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT token_balance FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    return row["token_balance"] if row else 0


def deduct_token(user_id: int, action_type: str, token_count: int, model_used: str, is_test: bool = False) -> bool:
    """扣除Token并记录日志"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 检查余额
        cursor.execute("SELECT token_balance, is_test_mode FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False

        # 测试模式不真实扣费
        is_test_mode = row["is_test_mode"]

        if not is_test_mode and row["token_balance"] < token_count:
            return False

        # 扣除Token（非测试模式）
        if not is_test_mode:
            cursor.execute(
                "UPDATE users SET token_balance = token_balance - ? WHERE id = ?",
                (token_count, user_id)
            )

        # 记录日志
        cursor.execute(
            """INSERT INTO token_logs (user_id, action_type, token_count, model_used, is_test)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, action_type, token_count, model_used, is_test_mode)
        )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to deduct token: {e}")
        return False
    finally:
        conn.close()


def get_token_logs(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """获取用户的Token消耗记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM token_logs WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def add_topup(user_id: int, amount: int, payment_method: str = "pending") -> int:
    """添加充值记录"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO topups (user_id, amount, payment_method, status)
           VALUES (?, ?, ?, 'completed')""",
        (user_id, amount, payment_method)
    )

    # 更新用户余额
    cursor.execute(
        "UPDATE users SET token_balance = token_balance + ? WHERE id = ?",
        (amount, user_id)
    )

    conn.commit()
    topup_id = cursor.lastrowid
    conn.close()

    return topup_id


def get_admin_config(key: str) -> Optional[str]:
    """获取管理员配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_value FROM admin_config WHERE config_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()

    return row["config_value"] if row else None


def set_admin_config(key: str, value: str):
    """设置管理员配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO admin_config (config_key, config_value, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(config_key) DO UPDATE SET config_value = ?, updated_at = CURRENT_TIMESTAMP""",
        (key, value, value)
    )
    conn.commit()
    conn.close()


def get_all_admin_configs() -> Dict[str, str]:
    """获取所有管理员配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_key, config_value FROM admin_config")
    rows = cursor.fetchall()
    conn.close()

    return {row["config_key"]: row["config_value"] for row in rows}


def update_user_test_mode(user_id: int, is_test_mode: bool):
    """更新用户测试模式"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_test_mode = ? WHERE id = ?",
        (is_test_mode, user_id)
    )
    conn.commit()
    conn.close()
