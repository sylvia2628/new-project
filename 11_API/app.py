#!/usr/bin/env python3
"""Small dependency-free MUSE AI OS API scaffold.

This is a portable development backend for local/NAS prototyping. It is not a
replacement for a production identity provider; put it behind Cloudflare
Access/VPN and replace the development token mapping before real data is used.
"""

import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MUSE_DB_PATH", os.path.join(BASE_DIR, "data", "muse.db"))
MAX_BODY_BYTES = 1024 * 1024
DEFAULT_CORS_ORIGIN = os.environ.get("MUSE_CORS_ORIGIN", "http://localhost:8080")
DB_LOCK = threading.Lock()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT DEFAULT '', email TEXT DEFAULT '', area TEXT DEFAULT '',
  source TEXT DEFAULT '', type TEXT DEFAULT '', size_range TEXT DEFAULT '',
  budget_range TEXT DEFAULT '', style TEXT DEFAULT '', needs_summary TEXT DEFAULT '',
  owner_id INTEGER, status TEXT NOT NULL DEFAULT 'new',
  last_contact_at TEXT DEFAULT '', next_follow_up_at TEXT DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, customer_id INTEGER, designer_id INTEGER,
  site_manager_id INTEGER, address TEXT DEFAULT '', stage TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0, budget_range TEXT DEFAULT '',
  next_action TEXT DEFAULT '', due_at TEXT DEFAULT '', risk_status TEXT DEFAULT 'normal',
  notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL, case_id INTEGER, assignee_id INTEGER,
  priority TEXT NOT NULL DEFAULT 'medium', status TEXT NOT NULL DEFAULT 'todo',
  due_at TEXT DEFAULT '', next_action TEXT DEFAULT '', created_by INTEGER,
  created_at TEXT NOT NULL, completed_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS portfolios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, case_id INTEGER, category TEXT DEFAULT '', style TEXT DEFAULT '',
  size TEXT DEFAULT '', area TEXT DEFAULT '', year TEXT DEFAULT '',
  design_idea TEXT DEFAULT '', public_status TEXT NOT NULL DEFAULT 'pending',
  publish_status TEXT NOT NULL DEFAULT 'draft', created_by INTEGER,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL, channel TEXT NOT NULL, source_type TEXT DEFAULT '',
  source_id INTEGER, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
  created_by_ai INTEGER NOT NULL DEFAULT 0, reviewed_by INTEGER,
  reviewed_at TEXT DEFAULT '', published_at TEXT DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER, action TEXT NOT NULL, resource_type TEXT NOT NULL,
  resource_id INTEGER, before_json TEXT DEFAULT '', after_json TEXT DEFAULT '',
  created_at TEXT NOT NULL
);
"""


ROLE_PERMISSIONS = {
    "manager": {"*"},
    "designer": {"assistant.read", "customers.read", "cases.read", "cases.write", "tasks.read", "tasks.write", "portfolios.read", "portfolios.write", "drafts.read", "drafts.write"},
    "assistant": {"assistant.read", "customers.read", "customers.write", "cases.read", "tasks.read", "tasks.write", "portfolios.read", "drafts.read", "drafts.write"},
    "site_manager": {"assistant.read", "cases.read", "cases.write", "tasks.read", "tasks.write"},
    "finance": {"assistant.read", "customers.read", "cases.read"},
    "admin": {"assistant.read", "customers.read", "customers.write", "cases.read", "tasks.read", "tasks.write", "portfolios.read", "drafts.read", "drafts.write"},
    "worker": {"tasks.read", "tasks.write"},
}

RESOURCE_FIELDS = {
    "customers": {"name", "phone", "email", "area", "source", "type", "size_range", "budget_range", "style", "needs_summary", "owner_id", "status", "last_contact_at", "next_follow_up_at"},
    "cases": {"name", "customer_id", "designer_id", "site_manager_id", "address", "stage", "progress", "budget_range", "next_action", "due_at", "risk_status", "notes"},
    "tasks": {"title", "case_id", "assignee_id", "priority", "status", "due_at", "next_action", "completed_at"},
    "portfolios": {"name", "case_id", "category", "style", "size", "area", "year", "design_idea", "public_status", "publish_status"},
    "drafts": {"kind", "channel", "source_type", "source_id", "content", "status", "created_by_ai", "published_at"},
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def db_connection():
    directory = os.path.dirname(DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with DB_LOCK, db_connection() as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def row_json(row):
    return dict(row) if row else None


def env_tokens():
    """Read token=user|role mappings without putting credentials in source control.

    Format: MUSE_DEV_TOKENS="token-a:manager@example.com|manager,token-b:staff@example.com|assistant"
    A local token is intentionally opt-in and must be replaced by real SSO.
    """
    mapping = {}
    raw = os.environ.get("MUSE_DEV_TOKENS", "")
    for item in raw.split(","):
        if ":" in item:
            token, identity = item.split(":", 1)
            if "|" in identity:
                email, role = identity.split("|", 1)
            else:
                email, role = identity, "assistant"
            if token and email and role in ROLE_PERMISSIONS:
                mapping[token] = {"email": email, "role": role}
    return mapping


def ensure_user(email, role="assistant"):
    with DB_LOCK, db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            if row["role"] != role:
                connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, row["id"]))
                connection.commit()
                row = connection.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
            return row_json(row)
        created = now_iso()
        cursor = connection.execute(
            "INSERT INTO users(email, display_name, role, created_at) VALUES (?, ?, ?, ?)",
            (email, email.split("@")[0], role, created),
        )
        connection.commit()
        return row_json(connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())


def has_permission(user, permission):
    permissions = ROLE_PERMISSIONS.get(user["role"], set())
    return "*" in permissions or permission in permissions


def audit(user, action, resource_type, resource_id, before=None, after=None):
    with DB_LOCK, db_connection() as connection:
        connection.execute(
            "INSERT INTO audit_logs(actor_id, action, resource_type, resource_id, before_json, after_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], action, resource_type, resource_id, json.dumps(before or {}, ensure_ascii=False), json.dumps(after or {}, ensure_ascii=False), now_iso()),
        )
        connection.commit()


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "MUSE-AI-OS/0.1"

    def log_message(self, format_string, *args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", DEFAULT_CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def authenticate(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            self.send_json(401, {"error": "authentication_required"})
            return None
        token = header[7:].strip()
        identity = env_tokens().get(token)
        if not identity:
            self.send_json(401, {"error": "invalid_token"})
            return None
        return ensure_user(identity["email"], identity["role"])

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "request_too_large"})
            return None
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            self.send_json(400, {"error": "invalid_json"})
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok", "service": "muse-ai-os-api"})
            return
        user = self.authenticate()
        if not user:
            return
        if parsed.path == "/api/me":
            self.send_json(200, {"user": user, "permissions": sorted(ROLE_PERMISSIONS.get(user["role"], set()))})
            return
        if parsed.path == "/api/assistant/today":
            if not has_permission(user, "assistant.read"):
                self.send_json(403, {"error": "forbidden", "required": "assistant.read"})
                return
            self.send_json(200, self.assistant_summary(7))
            return
        if parsed.path == "/api/assistant/weekly":
            if not has_permission(user, "assistant.read"):
                self.send_json(403, {"error": "forbidden", "required": "assistant.read"})
                return
            self.send_json(200, self.assistant_summary(7))
            return
        if parsed.path.startswith("/api/"):
            resource = parsed.path[5:].strip("/")
            self.list_resource(user, resource)
            return
        self.send_json(404, {"error": "not_found"})

    def assistant_summary(self, horizon_days):
        today = datetime.now(timezone.utc).date()
        horizon = today.fromordinal(today.toordinal() + horizon_days)
        today_text = today.isoformat()
        horizon_text = horizon.isoformat()
        with DB_LOCK, db_connection() as connection:
            open_tasks = connection.execute("SELECT * FROM tasks WHERE status NOT IN ('done', 'completed') ORDER BY due_at ASC, id DESC").fetchall()
            overdue = [row_json(row) for row in open_tasks if row["due_at"] and row["due_at"] < today_text]
            due_soon = [row_json(row) for row in open_tasks if row["due_at"] and today_text <= row["due_at"] <= horizon_text]
            followups = connection.execute("SELECT * FROM customers WHERE next_follow_up_at != '' AND next_follow_up_at <= ? ORDER BY next_follow_up_at ASC", (today_text,)).fetchall()
            risky_cases = connection.execute("SELECT * FROM cases WHERE risk_status != 'normal' OR (due_at != '' AND due_at <= ?) ORDER BY due_at ASC", (horizon_text,)).fetchall()
            pending_portfolios = connection.execute("SELECT * FROM portfolios WHERE public_status IN ('pending', '可公開') AND publish_status != 'published' ORDER BY id DESC").fetchall()
        return {
            "generated_at": now_iso(),
            "horizon_days": horizon_days,
            "counts": {
                "open_tasks": len(open_tasks),
                "overdue_tasks": len(overdue),
                "due_soon_tasks": len(due_soon),
                "followups_due": len(followups),
                "risky_cases": len(risky_cases),
                "pending_portfolios": len(pending_portfolios)
            },
            "overdue_tasks": overdue[:20],
            "due_soon_tasks": due_soon[:20],
            "followups_due": [row_json(row) for row in followups[:20]],
            "risky_cases": [row_json(row) for row in risky_cases[:20]],
            "pending_portfolios": [row_json(row) for row in pending_portfolios[:20]]
        }

    def do_POST(self):
        user = self.authenticate()
        if not user:
            return
        resource = urlparse(self.path).path[5:].strip("/")
        if resource == "drafts/generate":
            if not has_permission(user, "drafts.write"):
                self.send_json(403, {"error": "forbidden", "required": "drafts.write"})
                return
            payload = self.body_json()
            if payload is None:
                return
            self.generate_draft(user, payload)
            return
        if resource == "drafts":
            permission = "drafts.write"
            table = "drafts"
        else:
            permission = resource + ".write"
            table = resource
        if not has_permission(user, permission):
            self.send_json(403, {"error": "forbidden", "required": permission})
            return
        payload = self.body_json()
        if payload is None:
            return
        self.create_resource(user, table, payload)

    def generate_draft(self, user, payload):
        kind = str(payload.get("kind", "")).strip()
        channel = str(payload.get("channel", "")).strip()
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        if kind not in {"portfolio", "customer_reply", "case_summary", "social_post"} or not channel:
            self.send_json(400, {"error": "invalid_draft_request", "required": ["kind", "channel"]})
            return
        name = str(source.get("name", "慕舍設計案件"))
        style = str(source.get("style", "貼近生活需求的設計語彙"))
        area = str(source.get("area", source.get("size", "高雄")))
        idea = str(source.get("idea", source.get("needs_summary", "依屋況與使用者需求調整採光、收納與空間比例。")))
        if kind == "portfolio":
            content = "【%s】\n\n慕舍設計以%s，為%s重新整理空間機能與生活動線。\n\n設計重點：%s\n\n完整內容將由管理者確認後，再依頻道調整發布。" % (name, style, area, idea)
        elif kind == "customer_reply":
            content = "您好，感謝您聯繫慕舍設計。為了協助初步評估，請提供案件地點、坪數、屋況、預算區間、預計裝修時間，以及平面圖或現況照片。收到資料後，我們會由專人確認下一步。"
        elif kind == "case_summary":
            content = "案件：%s\n目前摘要：%s\n請確認目前階段、完成百分比、下一步工作與截止日。" % (name, idea)
        else:
            content = "慕舍設計｜%s\n\n%s\n\n發布前請確認作品公開狀態、客戶同意與圖片授權。" % (name, idea)
        timestamp = now_iso()
        fields = {
            "kind": kind, "channel": channel, "source_type": str(payload.get("source_type", "")),
            "source_id": payload.get("source_id"), "content": content, "status": "draft",
            "created_by_ai": 1, "created_at": timestamp, "updated_at": timestamp
        }
        with DB_LOCK, db_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO drafts(kind, channel, source_type, source_id, content, status, created_by_ai, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(fields[key] for key in ["kind", "channel", "source_type", "source_id", "content", "status", "created_by_ai", "created_at", "updated_at"]),
            )
            row = connection.execute("SELECT * FROM drafts WHERE id = ?", (cursor.lastrowid,)).fetchone()
            connection.commit()
        result = row_json(row)
        audit(user, "generate", "drafts", result["id"], after=result)
        self.send_json(201, result)

    def do_PATCH(self):
        user = self.authenticate()
        if not user:
            return
        path = urlparse(self.path).path[5:].strip("/").split("/")
        if len(path) != 2 or not path[1].isdigit():
            self.send_json(404, {"error": "resource_id_required"})
            return
        resource, resource_id = path[0], int(path[1])
        permission = resource + ".write"
        if not has_permission(user, permission):
            self.send_json(403, {"error": "forbidden", "required": permission})
            return
        payload = self.body_json()
        if payload is None:
            return
        self.update_resource(user, resource, resource_id, payload)

    def do_DELETE(self):
        user = self.authenticate()
        if not user:
            return
        path = urlparse(self.path).path[5:].strip("/").split("/")
        if len(path) != 2 or not path[1].isdigit():
            self.send_json(404, {"error": "resource_id_required"})
            return
        resource, resource_id = path[0], int(path[1])
        permission = resource + ".delete"
        if not has_permission(user, permission):
            self.send_json(403, {"error": "forbidden", "required": permission})
            return
        self.delete_resource(user, resource, resource_id)

    def list_resource(self, user, resource):
        permission = resource + ".read"
        if not has_permission(user, permission):
            self.send_json(403, {"error": "forbidden", "required": permission})
            return
        allowed = {"customers", "cases", "tasks", "portfolios", "drafts", "audit_logs"}
        if resource not in allowed:
            self.send_json(404, {"error": "unknown_resource"})
            return
        with DB_LOCK, db_connection() as connection:
            rows = connection.execute("SELECT * FROM " + resource + " ORDER BY id DESC").fetchall()
        self.send_json(200, {"items": [row_json(row) for row in rows]})

    def create_resource(self, user, table, payload):
        allowed = {"customers", "cases", "tasks", "portfolios", "drafts"}
        if table not in allowed:
            self.send_json(404, {"error": "unknown_resource"})
            return
        required = {"customers": ["name"], "cases": ["name", "stage"], "tasks": ["title"], "portfolios": ["name"], "drafts": ["kind", "channel", "content"]}[table]
        missing = [key for key in required if not payload.get(key)]
        if missing:
            self.send_json(400, {"error": "missing_fields", "fields": missing})
            return
        timestamp = now_iso()
        fields = {key: value for key, value in payload.items() if key in RESOURCE_FIELDS[table]}
        if table == "customers":
            fields.update({"created_at": timestamp, "updated_at": timestamp, "status": fields.get("status", "new")})
        elif table == "cases":
            fields.update({"created_at": timestamp, "updated_at": timestamp, "progress": max(0, min(100, int(fields.get("progress", 0)))), "risk_status": fields.get("risk_status", "normal")})
        elif table == "tasks":
            fields.update({"created_at": timestamp, "status": fields.get("status", "todo"), "priority": fields.get("priority", "medium"), "created_by": user["id"]})
        elif table == "portfolios":
            fields.update({"created_at": timestamp, "updated_at": timestamp, "created_by": user["id"], "publish_status": fields.get("publish_status", "draft")})
        elif table == "drafts":
            fields.update({"created_at": timestamp, "updated_at": timestamp, "created_by_ai": int(bool(fields.get("created_by_ai", False)))})
        columns = list(fields.keys())
        placeholders = ",".join("?" for _ in columns)
        values = [fields[column] for column in columns]
        with DB_LOCK, db_connection() as connection:
            cursor = connection.execute("INSERT INTO " + table + " (" + ",".join(columns) + ") VALUES (" + placeholders + ")", values)
            row = connection.execute("SELECT * FROM " + table + " WHERE id = ?", (cursor.lastrowid,)).fetchone()
            connection.commit()
        result = row_json(row)
        audit(user, "create", table, result["id"], after=result)
        self.send_json(201, result)

    def update_resource(self, user, table, resource_id, payload):
        allowed = {"customers", "cases", "tasks", "portfolios", "drafts"}
        if table not in allowed:
            self.send_json(404, {"error": "unknown_resource"})
            return
        with DB_LOCK, db_connection() as connection:
            before_row = connection.execute("SELECT * FROM " + table + " WHERE id = ?", (resource_id,)).fetchone()
            if not before_row:
                self.send_json(404, {"error": "not_found"})
                return
            fields = {key: value for key, value in payload.items() if key in RESOURCE_FIELDS[table] and key not in {"id", "created_at", "created_by"}}
            if table == "cases" and "progress" in fields:
                fields["progress"] = max(0, min(100, int(fields["progress"])))
            if table in {"customers", "cases", "portfolios", "drafts"}:
                fields["updated_at"] = now_iso()
            if table == "drafts" and fields.get("status") == "approved":
                fields["reviewed_by"] = user["id"]
                fields["reviewed_at"] = now_iso()
            if not fields:
                self.send_json(400, {"error": "no_update_fields"})
                return
            updates = ",".join(key + " = ?" for key in fields)
            connection.execute("UPDATE " + table + " SET " + updates + " WHERE id = ?", list(fields.values()) + [resource_id])
            after_row = connection.execute("SELECT * FROM " + table + " WHERE id = ?", (resource_id,)).fetchone()
            connection.commit()
        before = row_json(before_row)
        after = row_json(after_row)
        audit(user, "update", table, resource_id, before=before, after=after)
        self.send_json(200, after)

    def delete_resource(self, user, table, resource_id):
        allowed = {"customers", "cases", "tasks", "portfolios", "drafts"}
        if table not in allowed:
            self.send_json(404, {"error": "unknown_resource"})
            return
        with DB_LOCK, db_connection() as connection:
            before_row = connection.execute("SELECT * FROM " + table + " WHERE id = ?", (resource_id,)).fetchone()
            if not before_row:
                self.send_json(404, {"error": "not_found"})
                return
            connection.execute("DELETE FROM " + table + " WHERE id = ?", (resource_id,))
            connection.commit()
        audit(user, "delete", table, resource_id, before=row_json(before_row))
        self.send_json(200, {"deleted": True, "resource": table, "id": resource_id})


def run_server(host="127.0.0.1", port=8787):
    init_db()
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print("MUSE AI OS API listening on http://%s:%d" % (host, port))
    server.serve_forever()


if __name__ == "__main__":
    run_server(os.environ.get("MUSE_HOST", "127.0.0.1"), int(os.environ.get("MUSE_PORT", "8787")))
