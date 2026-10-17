import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "voltsage.db"

# Password hashing configuration (PBKDF2-HMAC-SHA256, 260,000 iterations)
HASH_ALGORITHM = "sha256"
ITERATIONS = 260000
SALT_BYTES = 16
SESSION_DURATION_DAYS = 7


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            );
        """)

        # 3. Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);")

        conn.commit()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS
    )
    return f"pbkdf2:{HASH_ALGORITHM}:{ITERATIONS}${salt}${derived.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        prefix, salt, key_hex = hashed.split("$")
        parts = prefix.split(":")
        algo = parts[1]
        iterations = int(parts[2])
        derived = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return secrets.compare_digest(derived.hex(), key_hex)
    except Exception:
        return False


# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(email: str, full_name: str, password: str) -> Dict[str, Any]:
    email = email.strip().lower()
    full_name = full_name.strip()
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not full_name:
        full_name = email.split("@")[0].capitalize()

    pwd_hash = hash_password(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            raise ValueError("An account with this email address already exists.")

        cursor.execute(
            "INSERT INTO users (email, full_name, password_hash) VALUES (?, ?, ?)",
            (email, full_name, pwd_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid

        return {
            "id": user_id,
            "email": email,
            "full_name": full_name
        }


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    email = email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            return None
        if verify_password(password, row["password_hash"]):
            return {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"]
            }
        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DURATION_DAYS)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat())
        )
        conn.commit()
    return token


def validate_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    now_iso = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.full_name, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now_iso))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"]
            }
    return None


def invalidate_session(token: str):
    if not token:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


# ============================================================
# CONVERSATION & MESSAGE HISTORY
# ============================================================

def create_conversation(user_id: int, title: str = "New Conversation") -> Dict[str, Any]:
    conv_id = secrets.token_hex(12)
    title = (title or "New Conversation")[:80].strip()
    now_iso = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, user_id, title, now_iso, now_iso)
        )
        conn.commit()

    return {
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "created_at": now_iso,
        "updated_at": now_iso
    }


def list_conversations(user_id: int) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as message_count
            FROM conversations c
            WHERE c.user_id = ?
            ORDER BY c.updated_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_conversation(conv_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id)
        )
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute("""
            SELECT id, role, content, sources, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conv_id,))
        messages = [dict(m) for m in cursor.fetchall()]

        conv = dict(row)
        conv["messages"] = messages
        return conv


def rename_conversation(conv_id: str, user_id: int, new_title: str) -> bool:
    new_title = new_title.strip()[:80]
    if not new_title:
        return False
    now_iso = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (new_title, now_iso, conv_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_conversation(conv_id: str, user_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def add_message_to_conversation(conv_id: str, role: str, content: str, sources_json: Optional[str] = None):
    now_iso = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, role, content, sources_json, now_iso)
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now_iso, conv_id)
        )
        conn.commit()


# Initialize database on module import
init_db()
