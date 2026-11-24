import os
import json
import hmac
import hashlib
import sqlite3
import time
import random
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="GemUp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
DB = "gemup.db"

CASES = {
    "basic": {"price": 100, "items": [50, 100, 200, 500]},
    "rare": {"price": 500, "items": [200, 500, 1000, 2500]},
    "legend": {"price": 1500, "items": [500, 1500, 3000, 7500]},
}


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 500,
                last_daily INTEGER DEFAULT 0
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                value INTEGER,
                listed INTEGER DEFAULT 0
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                amount INTEGER,
                created INTEGER
            )
        """)


init_db()


def verify_user(init_data):
    if DEV_MODE:
        return 123456789, "GemUpUser"

    if not BOT_TOKEN or not init_data:
        raise HTTPException(401, "Telegram authorization required")

    data = dict(parse_qsl(init_data))
    received_hash = data.pop("hash", None)

    if not received_hash:
        raise HTTPException(401, "Invalid Telegram data")

    check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items())
    )

    secret = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    calculated = hmac.new(
        secret,
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Authorization failed")

    if time.time() - int(data.get("auth_date", 0)) > 86400:
        raise HTTPException(401, "Authorization expired")

    user = json.loads(data["user"])
    return int(user["id"]), user.get("username", "Player")


def get_user(user_id, username):
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO users(id, username) VALUES (?, ?)",
            (user_id, username)
        )
        db.execute(
            "UPDATE users SET username=? WHERE id=?",
            (username, user_id)
        )
        return dict(db.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone())


def log_action(user_id, action, amount):
    with connect() as db:
        db.execute(
            "INSERT INTO history(user_id, action, amount, created) VALUES(?,?,?,?)",
            (user_id, action, amount, int(time.time()))
        )


def auth(authorization):
    if not authorization:
        raise HTTPException(401, "Missing Telegram initData")
    user_id, username = verify_user(authorization)
    return get_user(user_id, username)


@app.get("/")
def home():
    return {"status": "GemUp API is running"}


@app.get("/api/me")
def me(authorization: str = Header(None)):
    user = auth(authorization)
    with connect() as db:
        items = db.execute(
            "SELECT * FROM inventory WHERE user_id=?",
            (user["id"],)
        ).fetchall()

    return {
        "id": user["id"],
        "username": user["username"],
        "balance": user["balance"],
        "inventory": [dict(x) for x in items]
    }


@app.post("/api/daily")
def daily(authorization: str = Header(None)):
    user = auth(authorization)
    now = int(time.time())

    if now - user["last_daily"] < 86400:
        raise HTTPException(400, "Daily bonus already collected")

    with connect() as db:
        db.execute(
            "UPDATE users SET balance=balance+200, last_daily=? WHERE id=?",
            (now, user["id"])
        )

    log_action(user["id"], "daily_bonus", 200)
    return {"success": True, "reward": 200}


class CaseRequest(BaseModel):
    case: str


@app.post("/api/case/open")
def open_case(body: CaseRequest, authorization: str = Header(None)):
    user = auth(authorization)

    if body.case not in CASES:
        raise HTTPException(400, "Unknown case")

    case = CASES[body.case]

    if user["balance"] < case["price"]:
        raise HTTPException(400, "Not enough coins")

    reward = random.choice(case["items"])

    with connect() as db:
        db.execute(
            "UPDATE users SET balance=balance-? WHERE id=?",
            (case["price"], user["id"])
        )
        db.execute(
            "INSERT INTO inventory(user_id,name,value) VALUES(?,?,?)",
            (user["id"], f"Gem {reward}", reward)
        )

    log_action(user["id"], "case_open", -case["price"])

    return {"success": True, "reward": reward}


@app.get("/api/inventory")
def inventory(authorization: str = Header(None)):
    user = auth(authorization)

    with connect() as db:
        items = db.execute(
            "SELECT * FROM inventory WHERE user_id=?",
            (user["id"],)
        ).fetchall()

    return [dict(x) for x in items]


@app.get("/api/leaderboard")
def leaderboard():
    with connect() as db:
        rows = db.execute(
            "SELECT username, balance FROM users ORDER BY balance DESC LIMIT 20"
        ).fetchall()

    return [dict(x) for x in rows]


@app.get("/api/history")
def history(authorization: str = Header(None)):
    user = auth(authorization)

    with connect() as db:
        rows = db.execute(
            "SELECT action, amount, created FROM history "
            "WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user["id"],)
        ).fetchall()

    return [dict(x) for x in rows]


@app.get("/api/cases")
def cases():
    return CASES
app.mount("/", StaticFiles(directory="web", html=True), name="web")
