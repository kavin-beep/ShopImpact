"""Account-isolated durable storage. SQLite locally; PostgreSQL when hosted."""
import hashlib
import json
import re
import secrets
import time
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import create_engine, text
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(24))
DEFAULT_SETTINGS = {"budget": 10000.0, "carbon_goal": 100, "contrast": False}


class AccountError(ValueError):
    pass


class ConflictError(AccountError):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def username_key(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", name.strip()):
        raise AccountError("Use 3–40 letters, numbers, dots, underscores or hyphens for your username.")
    return name.strip().lower()


def check_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise AccountError("Choose a password containing 12–128 characters.")


def email_key(email):
    if not isinstance(email, str):
        raise AccountError("Enter a valid email address.")
    email = email.strip().lower()
    pattern = r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+"
    if len(email) > 254 or not re.fullmatch(pattern, email):
        raise AccountError("Enter a valid email address, such as name@example.com.")
    local = email.split("@", 1)[0]
    if len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local:
        raise AccountError("Enter a valid email address.")
    return email


class Accounts:
    def __init__(self, url=None, public=False, require_verified_email=False):
        self.require_verified_email = require_verified_email
        if public and (not url or not url.startswith("postgresql")):
            raise AccountError("Public hosting requires a persistent PostgreSQL database.")
        if not url:
            target = Path(__file__).resolve().parent / "personal_data/shopimpact.db"
            target.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{target.as_posix()}"
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        args = {"check_same_thread": False, "timeout": 15} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=args, pool_pre_ping=True)
        with self.engine.begin() as db:
            if self.engine.dialect.name == "sqlite":
                # Serialize startup migrations for existing local databases.
                db.execute(text("BEGIN IMMEDIATE"))
            db.execute(text("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                email TEXT,
                email_verified INTEGER NOT NULL DEFAULT 0,
                password_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL,
                purchases TEXT NOT NULL, settings TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0)"""))
            if self.engine.dialect.name == "postgresql":
                db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT"))
            elif "email" not in {column["name"] for column in inspect(db).get_columns("users")}:
                db.execute(text("ALTER TABLE users ADD COLUMN email TEXT"))
            if self.engine.dialect.name == "postgresql":
                db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified INTEGER NOT NULL DEFAULT 0"))
            elif "email_verified" not in {column["name"] for column in inspect(db).get_columns("users")}:
                db.execute(text("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0"))
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users(email)"))
            db.execute(text("""CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL)"""))
            db.execute(text("""CREATE TABLE IF NOT EXISTS attempts (
                name TEXT PRIMARY KEY, failures INTEGER NOT NULL,
                blocked_until DOUBLE PRECISION NOT NULL)"""))
            db.execute(text("""CREATE TABLE IF NOT EXISTS email_actions (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                purpose TEXT NOT NULL, email TEXT NOT NULL, password_snapshot TEXT NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL)"""))
            db.execute(text("""CREATE TABLE IF NOT EXISTS email_requests (
                address_hash TEXT PRIMARY KEY, next_allowed DOUBLE PRECISION NOT NULL)"""))

    def register(self, username, password, email=None):
        username = username_key(username)
        email = email_key(email) if email is not None else None
        check_password(password)
        recovery = secrets.token_urlsafe(32)
        values = {"id": secrets.token_hex(16), "name": username, "email": email,
                  "password": HASHER.hash(password), "recovery": digest(recovery),
                  "settings": json.dumps(DEFAULT_SETTINGS)}
        try:
            with self.engine.begin() as db:
                db.execute(text("""INSERT INTO users
                    (id, username, email, password_hash, recovery_hash, purchases, settings, revision)
                    VALUES (:id, :name, :email, :password, :recovery, '[]', :settings, 0)"""), values)
        except IntegrityError:
            raise AccountError("That username or email is unavailable. Use different account details.") from None
        return recovery

    def _identity(self, identifier):
        field = "email" if isinstance(identifier, str) and "@" in identifier else "username"
        name = email_key(identifier) if field == "email" else username_key(identifier)
        with self.engine.connect() as db:
            row = db.execute(text(f"SELECT id,username,email,email_verified,password_hash,recovery_hash FROM users WHERE {field}=:name"),
                             {"name": name}).mappings().first()
        # Both login aliases share the same failure counter for an existing account.
        return (row["username"] if row else name), row

    def _blocked(self, name):
        with self.engine.connect() as db:
            row = db.execute(text("SELECT blocked_until FROM attempts WHERE name=:name"), {"name": name}).first()
        if row and row[0] > time.time():
            raise AccountError("Too many attempts. Please wait 15 minutes before trying again.")

    def _failure(self, name):
        with self.engine.begin() as db:
            # Atomic increment prevents parallel attempts from losing counter updates.
            db.execute(text("""INSERT INTO attempts(name, failures, blocked_until) VALUES (:name, 0, 0)
                ON CONFLICT(name) DO NOTHING"""), {"name": name})
            db.execute(text("""UPDATE attempts SET failures=CASE
                WHEN blocked_until > 0 AND blocked_until <= :now THEN 1 ELSE failures+1 END,
                blocked_until=CASE WHEN blocked_until > 0 AND blocked_until <= :now THEN 0 ELSE blocked_until END
                WHERE name=:name"""), {"name": name, "now": time.time()})
            db.execute(text("UPDATE attempts SET blocked_until=:until WHERE name=:name AND failures>=5"),
                       {"name": name, "until": time.time() + 900})

    def login(self, username, password):
        name, row = self._identity(username)
        self._blocked(name)
        valid = False
        try:
            valid = HASHER.verify(row["password_hash"] if row else DUMMY_HASH, password[:129])
        except VerificationError:
            pass
        if not row or not valid or len(password) > 128:
            self._failure(name)
            raise AccountError("Email, username or password is incorrect.")
        if self.require_verified_email and row["email"] and not row["email_verified"]:
            raise AccountError("Verify your email before signing in. Use Send verification email below.")
        token = secrets.token_urlsafe(32)
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM attempts WHERE name=:name"), {"name": name})
            db.execute(text("DELETE FROM sessions WHERE expires_at<=:now"), {"now": time.time()})
            # A concurrent password reset must not create a session from old credentials.
            issued = db.execute(text("""INSERT INTO sessions(token_hash,user_id,expires_at)
                SELECT :token,id,:expires FROM users WHERE id=:id AND password_hash=:verified
                AND (:require_email=0 OR email IS NULL OR email_verified=1)"""),
                {"token": digest(token), "id": row["id"], "expires": time.time() + 43200,
                 "verified": row["password_hash"], "require_email": int(self.require_verified_email)})
            if issued.rowcount != 1:
                raise AccountError("Your credentials changed. Please sign in again.")
        return token

    def _user(self, db, token):
        user = db.execute(text("""SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id
            WHERE s.token_hash=:token AND s.expires_at>:now"""),
            {"token": digest(token), "now": time.time()}).mappings().first()
        if not user:
            raise AccountError("Please sign in again.")
        return user

    def load(self, token):
        with self.engine.connect() as db:
            user = self._user(db, token)
            return {"username": user["username"], "email": user["email"], "email_verified": bool(user["email_verified"]), "purchases": json.loads(user["purchases"]),
                    "settings": json.loads(user["settings"]), "revision": user["revision"]}

    def save(self, token, purchases, settings, revision):
        if len(purchases) > 1000:
            raise AccountError("An account supports up to 1,000 purchases.")
        with self.engine.begin() as db:
            user = self._user(db, token)
            result = db.execute(text("""UPDATE users SET purchases=:purchases, settings=:settings,
                revision=revision+1 WHERE id=:id AND revision=:revision"""),
                {"purchases": json.dumps(purchases), "settings": json.dumps(settings),
                 "id": user["id"], "revision": revision})
            if result.rowcount != 1:
                raise ConflictError("Your account changed in another tab. Reload your saved data before trying again.")
        return revision + 1

    def logout(self, token):
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM sessions WHERE token_hash=:token"), {"token": digest(token)})

    def reset_password(self, username, recovery, new_password):
        name, row = self._identity(username)
        check_password(new_password)
        self._blocked("recovery:" + name)
        if not row or not secrets.compare_digest(row["recovery_hash"], digest(recovery.strip())):
            self._failure("recovery:" + name)
            raise AccountError("Email, username or recovery code is incorrect.")
        replacement = secrets.token_urlsafe(32)
        with self.engine.begin() as db:
            updated = db.execute(text("UPDATE users SET password_hash=:password,recovery_hash=:recovery WHERE id=:id AND recovery_hash=:old"),
                       {"password": HASHER.hash(new_password), "recovery": digest(replacement), "id": row["id"], "old": row["recovery_hash"]})
            if updated.rowcount != 1:
                raise AccountError("Recovery code has already been used.")
            db.execute(text("DELETE FROM sessions WHERE user_id=:id"), {"id": row["id"]})
            db.execute(text("DELETE FROM email_actions WHERE user_id=:id"), {"id": row["id"]})
            db.execute(text("DELETE FROM attempts WHERE name=:name OR name=:recovery"), {"name": name, "recovery": "recovery:" + name})
        return replacement

    def set_email(self, token, email, password):
        email = email_key(email)
        try:
            with self.engine.begin() as db:
                user = self._user(db, token)
                try:
                    HASHER.verify(user["password_hash"], password)
                except VerificationError:
                    raise AccountError("Password is incorrect.") from None
                if user["email"] != email:
                    db.execute(text("UPDATE users SET email=:email,email_verified=0 WHERE id=:id"), {"email": email, "id": user["id"]})
                    db.execute(text("DELETE FROM email_actions WHERE user_id=:id"), {"id": user["id"]})
        except IntegrityError:
            raise AccountError("That email is unavailable. Use a different address.") from None
        return email

    def request_email_action(self, email, purpose):
        """Internal delivery payload only; never return this to a browser."""
        if purpose not in {"verify", "reset"}:
            raise AccountError("Invalid email action.")
        email = email_key(email)
        now = time.time()
        token = secrets.token_urlsafe(32)
        with self.engine.begin() as db:
            admitted = db.execute(text("""INSERT INTO email_requests(address_hash,next_allowed)
                VALUES (:address,:until) ON CONFLICT(address_hash) DO UPDATE
                SET next_allowed=:until WHERE email_requests.next_allowed<=:now"""),
                {"address": digest(email), "until": now + 60, "now": now})
            if admitted.rowcount != 1:
                return None
            row = db.execute(text("SELECT * FROM users WHERE email=:email"), {"email": email}).mappings().first()
            if not row or (purpose == "reset" and not row["email_verified"]) or (purpose == "verify" and row["email_verified"]):
                return None
            db.execute(text("DELETE FROM email_actions WHERE expires_at<=:now OR (user_id=:id AND purpose=:purpose)"),
                       {"now": now, "id": row["id"], "purpose": purpose})
            db.execute(text("""INSERT INTO email_actions
                (token_hash,user_id,purpose,email,password_snapshot,expires_at)
                VALUES (:hash,:id,:purpose,:email,:password,:expires)"""),
                {"hash": digest(token), "id": row["id"], "purpose": purpose, "email": email,
                 "password": row["password_hash"], "expires": now + (86400 if purpose == "verify" else 1800)})
        return email, token

    def consume_email_action(self, token, purpose, new_password=None):
        if purpose not in {"verify", "reset"} or not isinstance(token, str) or not 20 <= len(token) <= 100:
            raise AccountError("This link is invalid or expired. Request a new email.")
        password_hash = None
        recovery = None
        if purpose == "reset":
            check_password(new_password)
            password_hash = HASHER.hash(new_password)
            recovery = secrets.token_urlsafe(32)
        with self.engine.begin() as db:
            # DELETE RETURNING atomically claims a single-use token, even across processes.
            row = db.execute(text("""DELETE FROM email_actions WHERE token_hash=:hash
                AND purpose=:purpose AND expires_at>:now
                RETURNING user_id,email,password_snapshot"""),
                {"hash": digest(token), "purpose": purpose, "now": time.time()}).mappings().first()
            if not row:
                raise AccountError("This link is invalid or expired. Request a new email.")
            values = {"id": row["user_id"], "email": row["email"], "snapshot": row["password_snapshot"]}
            if purpose == "verify":
                changed = db.execute(text("""UPDATE users SET email_verified=1
                    WHERE id=:id AND email=:email AND password_hash=:snapshot"""), values)
            else:
                values.update(password=password_hash, recovery=digest(recovery))
                changed = db.execute(text("""UPDATE users SET password_hash=:password,recovery_hash=:recovery
                    WHERE id=:id AND email=:email AND email_verified=1 AND password_hash=:snapshot"""), values)
            if changed.rowcount != 1:
                raise AccountError("This link is invalid or expired. Request a new email.")
            db.execute(text("DELETE FROM email_actions WHERE user_id=:id"), {"id": row["user_id"]})
            if purpose == "reset":
                db.execute(text("DELETE FROM sessions WHERE user_id=:id"), {"id": row["user_id"]})
                db.execute(text("""DELETE FROM attempts WHERE name IN
                    (SELECT username FROM users WHERE id=:id)
                    OR name IN (SELECT 'recovery:' || username FROM users WHERE id=:id)"""), {"id": row["user_id"]})
        return {"email": row["email"], "recovery_code": recovery}

    def delete_account(self, token, password):
        with self.engine.begin() as db:
            user = self._user(db, token)
            try:
                HASHER.verify(user["password_hash"], password)
            except VerificationError:
                raise AccountError("Password is incorrect.") from None
            db.execute(text("DELETE FROM sessions WHERE user_id=:id"), {"id": user["id"]})
            db.execute(text("DELETE FROM email_actions WHERE user_id=:id"), {"id": user["id"]})
            db.execute(text("DELETE FROM users WHERE id=:id"), {"id": user["id"]})
