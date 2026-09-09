# Phase 1 — Foundation & Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** วางโครงโปรเจกต์ทั้งสองฝั่ง เชื่อม PostgreSQL ได้ และมีระบบล็อกอินที่แยกสิทธิ์สามบทบาทใช้งานได้จริงตั้งแต่หน้าเว็บถึงฐานข้อมูล

**Architecture:** Backend เป็น FastAPI + SQLAlchemy 2.0 แบบ sync (endpoint เป็น `def` ธรรมดา FastAPI จะรันใน threadpool ให้เอง) แยกชั้นเป็น `models` / `schemas` / `core` / `api` ให้ชัดตั้งแต่ต้นเพราะเฟสหลัง ๆ มีตารางเพิ่มอีกยี่สิบกว่าตาราง ยืนยันตัวตนด้วย JWT เก็บใน localStorage ฝั่ง React แล้วส่งกลับมาเป็น Bearer token การตรวจสิทธิ์ทำที่ dependency ของ FastAPI ไม่ใช่ในตัว endpoint เพื่อให้เฟสหลังเอาไปใช้ซ้ำได้ทันที

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, psycopg 3, PyJWT, bcrypt, pytest / React 18 (JavaScript ไม่ใช้ TypeScript), Vite, React Router 6, axios, Vitest + Testing Library / PostgreSQL 15+

**Spec:**
- `new_scenario_summary.md` — ข้อตัดสินใจทั้งหมดของระบบ
- `screens.md` — รายการหน้าจอ 18 หน้าและตารางสิทธิ์
- `data_model.md` — โครงสร้างฐานข้อมูลและกฎที่ต้องบังคับในฐานข้อมูล

## แผนทั้งโครงการ

| เฟส | ขอบเขต | สถานะ |
|---|---|---|
| **1** | โครงโปรเจกต์ ฐานข้อมูล ล็อกอิน สิทธิ์สามบทบาท เมนูตามสิทธิ์ | **แผนนี้** |
| 2 | ข้อมูลหลัก — ลูกค้า รถ สินค้า ผู้จำหน่าย ตั้งค่าระบบ | ยังไม่เขียน |
| 3 | คลังและจัดซื้อ — Lot, FIFO, ใบสั่งซื้อ, รับของ, ปรับสต็อก | ยังไม่เขียน |
| 4 | ใบงานและใบเสนอราคา — สถานะ ป้ายรออะไหล่ ตัดสต็อกตอนอนุมัติ | ยังไม่เขียน |
| 5 | บิล รับเงิน ใบกำกับ เลขที่เอกสาร กำไรขั้นต้น | ยังไม่เขียน |
| 6 | ขายหน้าร้าน รับประกัน รอบบำรุงรักษา | ยังไม่เขียน |
| 7 | แดชบอร์ด รายงานการเงิน รายงานภาษี | ยังไม่เขียน |

แต่ละเฟสจบแล้วต้องรันได้และทดสอบได้ด้วยตัวเอง เขียนแผนเฟสถัดไปเมื่อเฟสก่อนหน้าเสร็จ

---

## Global Constraints

ข้อบังคับทั้งโครงการ ทุกงานในทุกเฟสอยู่ใต้ข้อเหล่านี้

- **Python 3.12** / **Node 20 ขึ้นไป** / **PostgreSQL 15 ขึ้นไป**
- **Frontend เป็น JavaScript ไม่ใช้ TypeScript** ไฟล์ React ใช้นามสกุล `.jsx`
- **เงินทุกคอลัมน์เป็น `numeric(12,2)`** ฝั่ง Python รับเป็น `decimal.Decimal` เสมอ ห้ามใช้ `float` กับค่าเงินไม่ว่ากรณีใด
- **วันเวลาทุกคอลัมน์เป็น `timestamptz`** ฝั่ง Python ใช้ `datetime.now(timezone.utc)` ห้ามใช้ `datetime.now()` เปล่า
- **ราคาที่แสดงบนหน้าจอและที่คุยกับลูกค้าเป็นราคารวม VAT แล้ว** การถอด VAT ทำตอนออกบิลเท่านั้น
- **ห้ามใช้ `SEQUENCE` ของ PostgreSQL ออกเลขที่เอกสาร** เพราะ `nextval()` ไม่ย้อนกลับตอน rollback (บังคับใช้จริงในเฟส 5)
- **ทุกการกระทำต้องบันทึกว่าใครทำ** ตารางที่บันทึกการกระทำต้องมีคอลัมน์ `*_by` อ้าง `users.id`
- **ข้อความที่ผู้ใช้เห็นเป็นภาษาไทย** รวมถึงข้อความ error จาก API ส่วนชื่อตัวแปร ตาราง และคอลัมน์เป็นภาษาอังกฤษ
- **บทบาทมีสามค่าเท่านั้น** `admin` / `employee` / `mechanic` ตรงกับตารางสิทธิ์ใน `screens.md`
- **ทดสอบก่อนเขียนโค้ดเสมอ** ทุกงานเริ่มจากเทสต์ที่ยังไม่ผ่าน

---

## File Structure

### Backend

| ไฟล์ | หน้าที่ |
|---|---|
| `backend/app/config.py` | อ่านค่าตั้งจาก environment ที่เดียว |
| `backend/app/db.py` | engine และ session factory |
| `backend/app/models/base.py` | `Base` ของ SQLAlchemy ที่ทุกโมเดลสืบทอด |
| `backend/app/models/user.py` | ตาราง users |
| `backend/app/schemas/auth.py` | รูปแบบ request/response ของการล็อกอิน |
| `backend/app/schemas/user.py` | รูปแบบ request/response ของผู้ใช้ |
| `backend/app/core/security.py` | แฮชรหัสผ่านและออก/ถอด JWT ล้วน ๆ ไม่ยุ่งกับฐานข้อมูล |
| `backend/app/core/deps.py` | dependency ที่ทุก endpoint ใช้ร่วมกัน — session, ผู้ใช้ปัจจุบัน, ตรวจบทบาท |
| `backend/app/api/auth.py` | endpoint ล็อกอินและดูข้อมูลตัวเอง |
| `backend/app/api/users.py` | endpoint จัดการผู้ใช้ สำหรับ admin |
| `backend/app/main.py` | ประกอบแอป ใส่ CORS รวม router |
| `backend/app/seed.py` | สร้างผู้ใช้ admin คนแรก |
| `backend/alembic/` | migration ทั้งหมด |
| `backend/tests/` | เทสต์ |

แยก `core/security.py` ออกจาก `core/deps.py` เพราะตัวแรกเป็นฟังก์ชันบริสุทธิ์ที่เทสต์ได้โดยไม่ต้องมีฐานข้อมูล ส่วนตัวหลังผูกกับ request และ session

### Frontend

| ไฟล์ | หน้าที่ |
|---|---|
| `frontend/src/api/client.js` | axios instance ที่แนบ token และจัดการ 401 ที่เดียว |
| `frontend/src/auth/AuthContext.jsx` | สถานะผู้ใช้ปัจจุบัน ล็อกอิน ล็อกเอาต์ |
| `frontend/src/auth/ProtectedRoute.jsx` | กันหน้าที่ต้องล็อกอินและกันหน้าที่บทบาทเข้าไม่ได้ |
| `frontend/src/nav.js` | นิยามเมนู 18 หน้าและบทบาทที่เห็นแต่ละหน้า เป็นฟังก์ชันบริสุทธิ์จึงเทสต์ได้ตรง |
| `frontend/src/components/AppShell.jsx` | โครงหน้าจอ แถบเมนูซ้าย หัวข้อบน ปุ่มออกจากระบบ |
| `frontend/src/pages/LoginPage.jsx` | หน้าเข้าสู่ระบบ |
| `frontend/src/pages/DashboardPage.jsx` | หน้าแดชบอร์ดเปล่าไว้ยืนยันว่าล็อกอินแล้วเข้าถึงได้ |
| `frontend/src/App.jsx` | เส้นทางทั้งหมด |

---

## Task 1: โครงโปรเจกต์ ฐานข้อมูล และ health check

**Files:**
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: ไม่มี งานแรก
- Produces: `app.config.settings` (มี `.database_url`, `.jwt_secret`, `.jwt_algorithm`, `.jwt_expire_minutes`), `app.db.engine`, `app.db.SessionLocal`, `app.main.app`

- [ ] **Step 1: เตรียม git และโครงโฟลเดอร์**

```bash
cd /c/Users/PAT/Desktop/Garage
git init
mkdir -p backend/app/models backend/app/schemas backend/app/core backend/app/api backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/core/__init__.py backend/app/api/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: เขียน `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
venv/
.env
.pytest_cache/
node_modules/
dist/
.vite/
.DS_Store
```

- [ ] **Step 3: เขียน `backend/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
alembic==1.14.0
psycopg[binary]==3.2.3
pydantic==2.10.4
pydantic-settings==2.7.0
pyjwt==2.10.1
bcrypt==4.2.1
pytest==8.3.4
httpx==0.28.1
```

ถ้า pip แจ้งว่าเวอร์ชันไหนไม่มีให้เลื่อนขึ้นเป็นตัวล่าสุดของ minor เดียวกัน แต่ห้ามปล่อยไม่ pin

- [ ] **Step 4: สร้าง virtualenv และติดตั้ง**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

บน PowerShell ใช้ `.venv\Scripts\Activate.ps1` แทนบรรทัด source

- [ ] **Step 5: สร้างฐานข้อมูลสองตัว ตัวจริงกับตัวเทสต์**

```bash
psql -U postgres -c "create user garage with password 'garage';"
psql -U postgres -c "create database garage owner garage;"
psql -U postgres -c "create database garage_test owner garage;"
```

- [ ] **Step 6: เขียน `backend/.env.example`**

```
DATABASE_URL=postgresql+psycopg://garage:garage@localhost:5432/garage
JWT_SECRET=เปลี่ยนค่านี้ก่อนใช้งานจริง
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

แล้วคัดลอกเป็น `.env` ด้วย `cp .env.example .env`

- [ ] **Step 7: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_health.py`

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 8: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 9: เขียน `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://garage:garage@localhost:5432/garage"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480


settings = Settings()
```

- [ ] **Step 10: เขียน `backend/app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
```

`expire_on_commit=False` สำคัญ ไม่งั้นหลัง `commit()` แล้วอ่านฟิลด์ของอ็อบเจกต์จะยิง query ใหม่ ซึ่งพังเวลาส่งกลับเป็น response

- [ ] **Step 11: เขียน `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 12: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS 1 passed

- [ ] **Step 13: ยืนยันว่าเชื่อมฐานข้อมูลได้จริง**

```bash
cd backend
python -c "from sqlalchemy import text; from app.db import engine; print(engine.connect().execute(text('select 1')).scalar())"
```

Expected: พิมพ์ `1` ถ้าเชื่อมไม่ได้ให้แก้ `DATABASE_URL` ใน `.env` ก่อนไปต่อ

- [ ] **Step 14: Commit**

```bash
git add .gitignore backend/
git commit -m "chore: scaffold FastAPI backend with database connection and health check"
```

---

## Task 2: ตาราง users และ Alembic migration

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_create_users.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_user_model.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.db.engine`
- Produces: `app.models.base.Base`, `app.models.user.User` (คอลัมน์ `id`, `username`, `password_hash`, `full_name`, `role`, `is_active`, `created_at`), fixture `db_session` และ `client` สำหรับทุกเทสต์ในเฟสถัดไป

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_user_model.py`

```python
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def test_can_insert_and_read_user(db_session):
    db_session.add(
        User(
            username="somchai",
            password_hash="x",
            full_name="สมชาย ใจดี",
            role="admin",
        )
    )
    db_session.flush()

    user = db_session.scalar(select(User).where(User.username == "somchai"))
    assert user.full_name == "สมชาย ใจดี"
    assert user.role == "admin"
    assert user.is_active is True
    assert user.created_at is not None


def test_username_must_be_unique(db_session):
    db_session.add(User(username="somchai", password_hash="x", full_name="ก", role="admin"))
    db_session.flush()

    db_session.add(User(username="somchai", password_hash="y", full_name="ข", role="employee"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_role_must_be_one_of_three(db_session):
    db_session.add(User(username="ubie", password_hash="x", full_name="ค", role="owner"))
    with pytest.raises(IntegrityError):
        db_session.flush()
```

- [ ] **Step 2: เขียน `backend/tests/conftest.py`**

```python
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://garage:garage@localhost:5432/garage_test"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrate_test_database():
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade"))
        connection.execute(text("create schema public"))

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
    yield


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = Session()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

ตั้งค่า environment ก่อน import ทุกอย่างเพราะ `settings` ถูกสร้างตอน import โมดูล ถ้าตั้งทีหลังเทสต์จะไปลงฐานข้อมูลจริง

`join_transaction_mode="create_savepoint"` ทำให้ `commit()` ที่เกิดใน endpoint กลายเป็น savepoint ข้างใน transaction ของเทสต์ พอจบเทสต์ rollback ทีเดียวข้อมูลหายหมด ทุกเทสต์จึงเริ่มจากฐานข้อมูลเปล่าเสมอ

fixture `client` import `get_db` ข้างในฟังก์ชันเพราะโมดูลนั้นยังไม่มีจนถึง Task 4 พอถึงตอนนั้นจะใช้ได้ทันทีโดยไม่ต้องแก้ conftest

- [ ] **Step 3: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_user_model.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'app.models.user'`

- [ ] **Step 4: เขียน `backend/app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 5: เขียน `backend/app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role in ('admin', 'employee', 'mechanic')",
            name="users_role_check",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

- [ ] **Step 6: ตั้ง Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 7: แก้ `backend/alembic/env.py`**

แทนที่ทั้งไฟล์ด้วย

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.models.base import Base
import app.models.user  # noqa: F401  ต้อง import ทุกโมเดลเพื่อให้ autogenerate เห็น

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

ทุกครั้งที่เพิ่มโมเดลใหม่ในเฟสถัดไปต้องเพิ่มบรรทัด import ที่ไฟล์นี้ ไม่งั้น autogenerate จะมองไม่เห็นแล้วสร้าง migration ที่ลบตารางทิ้ง

- [ ] **Step 8: สร้าง migration**

```bash
cd backend
alembic revision --autogenerate -m "create users" --rev-id 0001
```

เปิดไฟล์ที่ได้ใน `alembic/versions/` ตรวจว่ามี `op.create_table("users", ...)` พร้อม unique constraint ของ `username` และ check constraint ของ `role` ถ้าขาดให้เติมเอง แล้วเปลี่ยนชื่อไฟล์เป็น `0001_create_users.py`

- [ ] **Step 9: รัน migration กับฐานข้อมูลจริง**

```bash
cd backend
alembic upgrade head
psql -U garage -d garage -c "\d users"
```

Expected: เห็นตาราง users พร้อมคอลัมน์ครบเจ็ดตัว

- [ ] **Step 10: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS ทั้งหมด 4 ตัว (health 1 + user model 3)

- [ ] **Step 11: Commit**

```bash
git add backend/
git commit -m "feat: add users table with alembic migration and test fixtures"
```

---

## Task 3: แฮชรหัสผ่านและ JWT

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `app.config.settings`
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, password_hash: str) -> bool`, `create_access_token(user_id: int, role: str) -> str`, `decode_access_token(token: str) -> dict` (คืน dict ที่มีคีย์ `sub` เป็น str ของ user id และ `role`)

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_security.py`

```python
import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_plain_password():
    hashed = hash_password("รหัสผ่าน123")
    assert hashed != "รหัสผ่าน123"
    assert len(hashed) > 20


def test_verify_accepts_correct_password():
    hashed = hash_password("รหัสผ่าน123")
    assert verify_password("รหัสผ่าน123", hashed) is True


def test_verify_rejects_wrong_password():
    hashed = hash_password("รหัสผ่าน123")
    assert verify_password("รหัสผ่าน124", hashed) is False


def test_same_password_hashes_differently_each_time():
    assert hash_password("abcdef") != hash_password("abcdef")


def test_token_carries_user_id_and_role():
    token = create_access_token(user_id=7, role="mechanic")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "mechanic"


def test_token_signed_with_another_key_is_rejected():
    token = jwt.encode({"sub": "7", "role": "admin"}, "another-key", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_security.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'app.core.security'`

- [ ] **Step 3: เขียน `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))


def create_access_token(user_id: int, role: str) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

bcrypt รับได้สูงสุด 72 ไบต์ ตัวอักษรไทยหนึ่งตัวกินสามไบต์ รหัสผ่านไทย 25 ตัวก็ชนเพดานแล้ว จึงตัดที่ 72 ไบต์ทั้งตอนแฮชและตอนตรวจให้ตรงกัน ไม่งั้น bcrypt จะโยน error ใส่ผู้ใช้

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/test_security.py -v`
Expected: PASS 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: add password hashing and jwt helpers"
```

---

## Task 4: endpoint ล็อกอิน

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/core/deps.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes: `User`, `hash_password`, `verify_password`, `create_access_token`, fixture `client` และ `db_session`
- Produces: `app.core.deps.get_db`, `POST /api/auth/login` (รับ `{username, password}` คืน `{access_token, token_type, user}`), `app.schemas.user.UserOut`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_auth_api.py`

```python
import pytest

from app.core.security import hash_password
from app.models.user import User


@pytest.fixture()
def admin_user(db_session):
    user = User(
        username="owner",
        password_hash=hash_password("secret123"),
        full_name="เจ้าของอู่",
        role="admin",
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_login_with_correct_credentials_returns_token_and_user(client, admin_user):
    response = client.post(
        "/api/auth/login", json={"username": "owner", "password": "secret123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20
    assert body["user"]["username"] == "owner"
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]


def test_login_with_wrong_password_is_rejected(client, admin_user):
    response = client.post(
        "/api/auth/login", json={"username": "owner", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_with_unknown_username_is_rejected(client, admin_user):
    response = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "secret123"}
    )
    assert response.status_code == 401


def test_inactive_user_cannot_login(client, db_session):
    db_session.add(
        User(
            username="quit",
            password_hash=hash_password("secret123"),
            full_name="ลาออกแล้ว",
            role="employee",
            is_active=False,
        )
    )
    db_session.flush()

    response = client.post(
        "/api/auth/login", json={"username": "quit", "password": "secret123"}
    )
    assert response.status_code == 401
```

เทสต์ตัวที่สามยืนยันว่าข้อความ error ของรหัสผิดกับชื่อผู้ใช้ไม่มีต้องเหมือนกัน คือ 401 ทั้งคู่ ไม่บอกว่าอันไหนผิดเพื่อไม่ให้เดาชื่อผู้ใช้ได้

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_auth_api.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'app.core.deps'`

- [ ] **Step 3: เขียน `backend/app/schemas/user.py`**

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=72)
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["admin", "employee", "mechanic"]


class UserActiveUpdate(BaseModel):
    is_active: bool
```

`UserOut` ไม่มี `password_hash` เลย แฮชจึงไม่มีทางหลุดออก API ไม่ว่าใครจะเผลอส่งอ็อบเจกต์ User ตรง ๆ

- [ ] **Step 4: เขียน `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
```

- [ ] **Step 5: เขียน `backend/app/core/deps.py`**

```python
from typing import Iterator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Task 5 จะเติม `get_current_user` และ `require_roles` ลงไฟล์นี้

- [ ] **Step 6: เขียน `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))

    if user is None or not user.is_active or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserOut.model_validate(user),
    )
```

- [ ] **Step 7: แก้ `backend/app/main.py` ให้รวม router**

เพิ่มสองบรรทัดนี้ ตัว import ไว้บนสุดกับ `include_router` ไว้ก่อน endpoint health

```python
from app.api import auth

app.include_router(auth.router)
```

- [ ] **Step 8: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS ทั้งหมด 14 ตัว

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: add login endpoint returning jwt and user profile"
```

---

## Task 5: ตรวจสิทธิ์ด้วย dependency และ endpoint ดูข้อมูลตัวเอง

**Files:**
- Modify: `backend/app/core/deps.py`
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/test_permissions.py`

**Interfaces:**
- Consumes: `get_db`, `decode_access_token`, `User`
- Produces: `get_current_user() -> User`, `require_roles(*roles: str)` (คืน dependency ที่ให้ `User` และโยน 403 ถ้าบทบาทไม่ตรง), `GET /api/auth/me`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_permissions.py`

```python
import pytest
from fastapi import Depends

from app.core.deps import require_roles
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User


@pytest.fixture()
def users(db_session):
    created = {}
    for role in ("admin", "employee", "mechanic"):
        user = User(
            username=role,
            password_hash=hash_password("secret123"),
            full_name=f"ผู้ใช้ {role}",
            role=role,
        )
        db_session.add(user)
        created[role] = user
    db_session.flush()
    return created


def auth_header(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_me_returns_the_logged_in_user(client, users):
    response = client.get("/api/auth/me", headers=auth_header(users["mechanic"]))

    assert response.status_code == 200
    assert response.json()["username"] == "mechanic"
    assert response.json()["role"] == "mechanic"


def test_me_without_token_is_rejected(client, users):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token_is_rejected(client, users):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_deactivated_user_token_stops_working(client, users, db_session):
    header = auth_header(users["employee"])
    users["employee"].is_active = False
    db_session.flush()

    assert client.get("/api/auth/me", headers=header).status_code == 401


def test_require_roles_allows_listed_role_and_blocks_others(client, users):
    @app.get("/api/test-admin-only")
    def admin_only(user: User = Depends(require_roles("admin"))):
        return {"ok": True}

    assert client.get("/api/test-admin-only", headers=auth_header(users["admin"])).status_code == 200
    assert client.get("/api/test-admin-only", headers=auth_header(users["employee"])).status_code == 403
    assert client.get("/api/test-admin-only", headers=auth_header(users["mechanic"])).status_code == 403
```

เทสต์ตัวสุดท้ายสร้าง endpoint ปลอมขึ้นมาชั่วคราวเพื่อทดสอบ `require_roles` โดยตรง จะได้ไม่ต้องรอจนมี endpoint จริงในเฟสหลัง

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_permissions.py -v`
Expected: FAIL ด้วย `ImportError: cannot import name 'require_roles'`

- [ ] **Step 3: เติม `backend/app/core/deps.py`**

แทนที่ทั้งไฟล์ด้วย

```python
from typing import Iterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import SessionLocal
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="กรุณาเข้าสู่ระบบใหม่",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ไม่มีสิทธิ์เข้าถึงส่วนนี้",
            )
        return user

    return dependency
```

`get_current_user` อ่านผู้ใช้จากฐานข้อมูลใหม่ทุกครั้งแทนที่จะเชื่อ `role` ในโทเคน เพราะเจ้าของอู่อาจปิดบัญชีหรือเปลี่ยนบทบาทระหว่างที่โทเคนเก่ายังไม่หมดอายุ

- [ ] **Step 4: เติม endpoint `/me` ใน `backend/app/api/auth.py`**

เพิ่ม import `get_current_user` แล้วต่อท้ายไฟล์

```python
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS ทั้งหมด 19 ตัว

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add role-based dependencies and current user endpoint"
```

---

## Task 6: จัดการผู้ใช้สำหรับ admin

**Files:**
- Create: `backend/app/api/users.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_users_api.py`

**Interfaces:**
- Consumes: `require_roles`, `get_db`, `hash_password`, `UserCreate`, `UserActiveUpdate`, `UserOut`
- Produces: `GET /api/users`, `POST /api/users`, `PATCH /api/users/{user_id}/active` ทั้งสามต้องเป็น admin เท่านั้น

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_users_api.py`

```python
import pytest

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


@pytest.fixture()
def admin(db_session):
    user = User(
        username="owner",
        password_hash=hash_password("secret123"),
        full_name="เจ้าของอู่",
        role="admin",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def employee(db_session):
    user = User(
        username="staff",
        password_hash=hash_password("secret123"),
        full_name="พนักงานหน้าร้าน",
        role="employee",
    )
    db_session.add(user)
    db_session.flush()
    return user


def auth_header(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_admin_can_list_users(client, admin, employee):
    response = client.get("/api/users", headers=auth_header(admin))

    assert response.status_code == 200
    usernames = [row["username"] for row in response.json()]
    assert usernames == ["owner", "staff"]


def test_employee_cannot_list_users(client, admin, employee):
    assert client.get("/api/users", headers=auth_header(employee)).status_code == 403


def test_admin_can_create_a_mechanic(client, admin, db_session):
    response = client.post(
        "/api/users",
        headers=auth_header(admin),
        json={
            "username": "chang",
            "password": "secret123",
            "full_name": "ช่างหนึ่ง",
            "role": "mechanic",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "mechanic"

    created = db_session.get(User, response.json()["id"])
    assert created.password_hash != "secret123"
    assert verify_password("secret123", created.password_hash) is True


def test_duplicate_username_is_rejected(client, admin):
    assert (
        client.post(
            "/api/users",
            headers=auth_header(admin),
            json={
                "username": "owner",
                "password": "secret123",
                "full_name": "ซ้ำ",
                "role": "employee",
            },
        ).status_code
        == 409
    )


def test_unknown_role_is_rejected(client, admin):
    assert (
        client.post(
            "/api/users",
            headers=auth_header(admin),
            json={
                "username": "boss",
                "password": "secret123",
                "full_name": "บทบาทมั่ว",
                "role": "owner",
            },
        ).status_code
        == 422
    )


def test_admin_can_deactivate_another_user(client, admin, employee):
    response = client.patch(
        f"/api/users/{employee.id}/active",
        headers=auth_header(admin),
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_cannot_deactivate_themselves(client, admin):
    response = client.patch(
        f"/api/users/{admin.id}/active",
        headers=auth_header(admin),
        json={"is_active": False},
    )
    assert response.status_code == 400
```

เทสต์ตัวสุดท้ายกันเคสที่ admin คนเดียวของระบบปิดบัญชีตัวเองแล้วไม่มีใครเข้าไปเปิดคืนได้อีกเลย

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_users_api.py -v`
Expected: FAIL ทุกตัวด้วย 404 เพราะยังไม่มี route

- [ ] **Step 3: เขียน `backend/app/api/users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserActiveUpdate, UserCreate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ชื่อผู้ใช้นี้ถูกใช้ไปแล้ว",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
def set_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้")

    if user.id == current_user.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ปิดการใช้งานบัญชีของตัวเองไม่ได้",
        )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 4: แก้ `backend/app/main.py` ให้รวม router ใหม่**

```python
from app.api import auth, users

app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS ทั้งหมด 26 ตัว

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add admin-only user management endpoints"
```

---

## Task 7: สคริปต์สร้าง admin คนแรก

**Files:**
- Create: `backend/app/seed.py`
- Create: `backend/tests/test_seed.py`

**Interfaces:**
- Consumes: `SessionLocal`, `User`, `hash_password`
- Produces: `create_admin(db, username, password, full_name) -> User` และรันจาก command line ได้

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `backend/tests/test_seed.py`

```python
import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.user import User
from app.seed import create_admin


def test_create_admin_inserts_an_active_admin(db_session):
    user = create_admin(db_session, "owner", "secret123", "เจ้าของอู่")

    assert user.role == "admin"
    assert user.is_active is True
    assert verify_password("secret123", user.password_hash) is True


def test_create_admin_refuses_duplicate_username(db_session):
    create_admin(db_session, "owner", "secret123", "เจ้าของอู่")

    with pytest.raises(ValueError):
        create_admin(db_session, "owner", "secret123", "ซ้ำ")

    assert len(db_session.scalars(select(User)).all()) == 1
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd backend && python -m pytest tests/test_seed.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'app.seed'`

- [ ] **Step 3: เขียน `backend/app/seed.py`**

```python
import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.user import User


def create_admin(db: Session, username: str, password: str, full_name: str) -> User:
    exists = db.scalar(select(User).where(User.username == username))
    if exists is not None:
        raise ValueError(f"มีผู้ใช้ชื่อ {username} อยู่แล้ว")

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="สร้างผู้ใช้ admin คนแรก")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    with SessionLocal() as db:
        user = create_admin(db, args.username, args.password, args.full_name)
        print(f"สร้างผู้ใช้ {user.username} เรียบร้อย")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS ทั้งหมด 28 ตัว

- [ ] **Step 5: สร้าง admin จริงในฐานข้อมูลจริง**

```bash
cd backend
python -m app.seed --username owner --password owner1234 --full-name "เจ้าของอู่"
```

Expected: พิมพ์ `สร้างผู้ใช้ owner เรียบร้อย`

- [ ] **Step 6: ยืนยันว่าล็อกอินผ่าน API จริงได้**

เปิดเซิร์ฟเวอร์ในอีกหน้าต่าง

```bash
cd backend && uvicorn app.main:app --reload
```

แล้วยิงคำสั่ง

```bash
curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"owner\",\"password\":\"owner1234\"}"
```

Expected: ได้ JSON ที่มี `access_token` และ `user.role` เป็น `admin` เปิด http://localhost:8000/docs ดู Swagger ได้ด้วย

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: add seed script for first admin user"
```

---

## Task 8: โครง React และหน้าเข้าสู่ระบบ

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/auth/AuthContext.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`
- Create: `frontend/tests/setup.js`
- Create: `frontend/tests/LoginPage.test.jsx`

**Interfaces:**
- Consumes: `POST /api/auth/login`, `GET /api/auth/me`
- Produces: `useAuth()` คืน `{ user, loading, login(username, password), logout() }`, default export `client` จาก `api/client.js`

- [ ] **Step 1: สร้างโปรเจกต์ frontend**

```bash
cd /c/Users/PAT/Desktop/Garage
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install react-router-dom@6.28.0 axios@1.7.9
npm install -D vitest@2.1.8 jsdom@25.0.1 @testing-library/react@16.1.0 @testing-library/jest-dom@6.6.3 @testing-library/user-event@14.5.2
```

ลบไฟล์ตัวอย่างที่ Vite แถมมา `src/App.css` และ `src/assets/`

- [ ] **Step 2: ตั้งค่า Vitest ใน `frontend/vite.config.js`**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
  },
})
```

เพิ่มสคริปต์ใน `package.json`

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "test": "vitest run"
}
```

- [ ] **Step 3: เขียน `frontend/tests/setup.js`**

```js
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: เขียน `frontend/.env.example`**

```
VITE_API_URL=http://localhost:8000
```

แล้ว `cp .env.example .env`

- [ ] **Step 5: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `frontend/tests/LoginPage.test.jsx`

```jsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from '../src/api/client'
import { AuthProvider } from '../src/auth/AuthContext'
import LoginPage from '../src/pages/LoginPage'

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('เก็บ token ลง localStorage เมื่อล็อกอินสำเร็จ', async () => {
    vi.spyOn(client, 'post').mockResolvedValue({
      data: {
        access_token: 'token-123',
        token_type: 'bearer',
        user: { id: 1, username: 'owner', full_name: 'เจ้าของอู่', role: 'admin', is_active: true },
      },
    })

    renderLoginPage()
    await userEvent.type(screen.getByLabelText('ชื่อผู้ใช้'), 'owner')
    await userEvent.type(screen.getByLabelText('รหัสผ่าน'), 'owner1234')
    await userEvent.click(screen.getByRole('button', { name: 'เข้าสู่ระบบ' }))

    expect(localStorage.getItem('token')).toBe('token-123')
  })

  it('แสดงข้อความผิดพลาดและไม่เก็บ token เมื่อรหัสผ่านผิด', async () => {
    vi.spyOn(client, 'post').mockRejectedValue({
      response: { status: 401, data: { detail: 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง' } },
    })

    renderLoginPage()
    await userEvent.type(screen.getByLabelText('ชื่อผู้ใช้'), 'owner')
    await userEvent.type(screen.getByLabelText('รหัสผ่าน'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'เข้าสู่ระบบ' }))

    expect(await screen.findByText('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')).toBeInTheDocument()
    expect(localStorage.getItem('token')).toBeNull()
  })
})
```

- [ ] **Step 6: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd frontend && npm test`
Expected: FAIL ด้วยหาไฟล์ `../src/api/client` ไม่เจอ

- [ ] **Step 7: เขียน `frontend/src/api/client.js`**

```js
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default client
```

- [ ] **Step 8: เขียน `frontend/src/auth/AuthContext.jsx`**

```jsx
import { createContext, useContext, useEffect, useState } from 'react'

import client from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }

    client
      .get('/api/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(username, password) {
    const response = await client.post('/api/auth/login', { username, password })
    localStorage.setItem('token', response.data.access_token)
    setUser(response.data.user)
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth ต้องอยู่ภายใน AuthProvider')
  }
  return context
}
```

- [ ] **Step 9: เขียน `frontend/src/pages/LoginPage.jsx`**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>ระบบจัดการอู่ซ่อมรถ</h1>

        <label htmlFor="username">ชื่อผู้ใช้</label>
        <input
          id="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
        />

        <label htmlFor="password">รหัสผ่าน</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          เข้าสู่ระบบ
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Step 10: เขียน `frontend/src/styles.css`**

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: 'Sarabun', 'Segoe UI', sans-serif;
  background: #f4f5f7;
  color: #1f2933;
}

.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
}

.login-card {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 320px;
}

.login-card h1 {
  font-size: 20px;
  margin: 0 0 16px;
  text-align: center;
}

.login-card input {
  padding: 10px;
  border: 1px solid #cbd2d9;
  border-radius: 6px;
  font-size: 15px;
}

.login-card button {
  margin-top: 16px;
  padding: 10px;
  border: 0;
  border-radius: 6px;
  background: #1f6feb;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}

.login-card button:disabled {
  background: #9aa5b1;
  cursor: not-allowed;
}

.error {
  color: #c0392b;
  font-size: 14px;
  margin: 4px 0 0;
}
```

- [ ] **Step 11: เขียน `frontend/src/main.jsx` และ `App.jsx` ชั่วคราว**

`main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
```

`App.jsx` ชั่วคราว Task 9 จะเขียนทับ

```jsx
import { Route, Routes } from 'react-router-dom'

import LoginPage from './pages/LoginPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<LoginPage />} />
    </Routes>
  )
}
```

- [ ] **Step 12: รันเทสต์ให้ผ่าน**

Run: `cd frontend && npm test`
Expected: PASS 2 passed

- [ ] **Step 13: Commit**

```bash
git add frontend/
git commit -m "feat: add react scaffold with auth context and login page"
```

---

## Task 9: กันเส้นทางตามสิทธิ์และเมนู 18 หน้า

**Files:**
- Create: `frontend/src/nav.js`
- Create: `frontend/src/auth/ProtectedRoute.jsx`
- Create: `frontend/src/components/AppShell.jsx`
- Create: `frontend/src/pages/DashboardPage.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`
- Create: `frontend/tests/nav.test.js`
- Create: `frontend/tests/ProtectedRoute.test.jsx`

**Interfaces:**
- Consumes: `useAuth()`
- Produces: `MENU` (อาร์เรย์ของ `{ path, label, roles }`), `menuForRole(role)`, `<ProtectedRoute roles={[...]}>`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `frontend/tests/nav.test.js`

```js
import { describe, expect, it } from 'vitest'

import { MENU, menuForRole } from '../src/nav'

describe('เมนูตามสิทธิ์', () => {
  it('มีครบ 18 หน้าตามขอบเขตของระบบ', () => {
    expect(MENU).toHaveLength(18)
  })

  it('admin เห็นทุกหน้า', () => {
    expect(menuForRole('admin')).toHaveLength(18)
  })

  it('employee ไม่เห็นรายงานการเงิน รายงานภาษี และตั้งค่า', () => {
    const paths = menuForRole('employee').map((item) => item.path)

    expect(paths).not.toContain('/reports/financial')
    expect(paths).not.toContain('/reports/tax')
    expect(paths).not.toContain('/settings')
    expect(paths).toContain('/billing')
  })

  it('mechanic ไม่เห็นหน้าที่เกี่ยวกับเงินและรายงาน', () => {
    const paths = menuForRole('mechanic').map((item) => item.path)

    expect(paths).not.toContain('/billing')
    expect(paths).not.toContain('/counter-sale')
    expect(paths).not.toContain('/invoices')
    expect(paths).not.toContain('/reports/financial')
    expect(paths).toContain('/jobs')
  })

  it('บทบาทที่ไม่รู้จักไม่เห็นเมนูอะไรเลย', () => {
    expect(menuForRole('stranger')).toHaveLength(0)
  })
})
```

สร้าง `frontend/tests/ProtectedRoute.test.jsx`

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from '../src/api/client'
import { AuthProvider } from '../src/auth/AuthContext'
import ProtectedRoute from '../src/auth/ProtectedRoute'

function renderAt(path, element) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<p>หน้าเข้าสู่ระบบ</p>} />
          <Route path="/" element={<p>หน้าแรก</p>} />
          <Route path="/secret" element={element} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('ส่งไปหน้าเข้าสู่ระบบเมื่อยังไม่ได้ล็อกอิน', async () => {
    renderAt('/secret', <ProtectedRoute><p>ความลับ</p></ProtectedRoute>)

    expect(await screen.findByText('หน้าเข้าสู่ระบบ')).toBeInTheDocument()
  })

  it('ให้ผ่านเมื่อบทบาทตรงกับที่กำหนด', async () => {
    localStorage.setItem('token', 'token-123')
    vi.spyOn(client, 'get').mockResolvedValue({
      data: { id: 1, username: 'owner', full_name: 'เจ้าของอู่', role: 'admin', is_active: true },
    })

    renderAt('/secret', <ProtectedRoute roles={['admin']}><p>ความลับ</p></ProtectedRoute>)

    expect(await screen.findByText('ความลับ')).toBeInTheDocument()
  })

  it('ส่งกลับหน้าแรกเมื่อล็อกอินแล้วแต่บทบาทไม่ได้รับอนุญาต', async () => {
    localStorage.setItem('token', 'token-123')
    vi.spyOn(client, 'get').mockResolvedValue({
      data: { id: 2, username: 'chang', full_name: 'ช่างหนึ่ง', role: 'mechanic', is_active: true },
    })

    renderAt('/secret', <ProtectedRoute roles={['admin']}><p>ความลับ</p></ProtectedRoute>)

    await waitFor(() => expect(screen.getByText('หน้าแรก')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd frontend && npm test`
Expected: FAIL หาไฟล์ `../src/nav` และ `../src/auth/ProtectedRoute` ไม่เจอ

- [ ] **Step 3: เขียน `frontend/src/nav.js`**

```js
const ALL = ['admin', 'employee', 'mechanic']
const OFFICE = ['admin', 'employee']
const ADMIN_ONLY = ['admin']

export const MENU = [
  { path: '/', label: 'แดชบอร์ด', roles: ALL },
  { path: '/intake', label: 'รับรถเข้าอู่', roles: ALL },
  { path: '/jobs', label: 'รายการใบงาน', roles: ALL },
  { path: '/quotations', label: 'ใบเสนอราคา', roles: ALL },
  { path: '/billing', label: 'ออกบิลและรับเงิน', roles: OFFICE },
  { path: '/counter-sale', label: 'ขายอะไหล่หน้าร้าน', roles: OFFICE },
  { path: '/invoices', label: 'รายการบิล', roles: OFFICE },
  { path: '/customers', label: 'ลูกค้าและรถ', roles: ALL },
  { path: '/reminders', label: 'ติดตามรอบบำรุงรักษา', roles: OFFICE },
  { path: '/products', label: 'สินค้าและอะไหล่', roles: ALL },
  { path: '/purchase-orders', label: 'ใบสั่งซื้อ', roles: OFFICE },
  { path: '/goods-receipts', label: 'รับของเข้าคลัง', roles: ALL },
  { path: '/stock', label: 'สต็อกและ Lot', roles: ALL },
  { path: '/promotions', label: 'โปรโมชั่น', roles: ADMIN_ONLY },
  { path: '/reports/financial', label: 'รายงานการเงิน', roles: ADMIN_ONLY },
  { path: '/reports/tax', label: 'รายงานภาษี', roles: ADMIN_ONLY },
  { path: '/users', label: 'ผู้ใช้และสิทธิ์', roles: ADMIN_ONLY },
  { path: '/settings', label: 'ตั้งค่าระบบ', roles: ADMIN_ONLY },
]

export function menuForRole(role) {
  return MENU.filter((item) => item.roles.includes(role))
}
```

หมายเหตุ ใน `screens.md` โปรโมชั่นกับผู้ใช้ถูกยุบเข้าหน้าตั้งค่าเพื่อให้นับได้ 18 หน้า ที่นี่แยกเป็นเมนูของตัวเองเพราะเมนูคือทางเข้า ไม่ใช่หน่วยนับหน้าจอ ส่วนที่นับไม่ครบ 18 คือรายการใบงานกับรายละเอียดใบงานที่ใช้เมนูเดียวกัน

- [ ] **Step 4: เขียน `frontend/src/auth/ProtectedRoute.jsx`**

```jsx
import { Navigate } from 'react-router-dom'

import { useAuth } from './AuthContext'

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <p className="loading">กำลังโหลด...</p>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return children
}
```

- [ ] **Step 5: เขียน `frontend/src/components/AppShell.jsx`**

```jsx
import { NavLink } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { menuForRole } from '../nav'

const ROLE_LABEL = {
  admin: 'เจ้าของอู่',
  employee: 'พนักงานหน้าร้าน',
  mechanic: 'ช่าง',
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth()
  const menu = menuForRole(user.role)

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">อู่ซ่อมรถ</div>
        <nav>
          {menu.map((item) => (
            <NavLink key={item.path} to={item.path} end={item.path === '/'}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="content">
        <header className="topbar">
          <span>
            {user.full_name} · {ROLE_LABEL[user.role]}
          </span>
          <button type="button" onClick={logout}>
            ออกจากระบบ
          </button>
        </header>
        <main>{children}</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: เขียน `frontend/src/pages/DashboardPage.jsx`**

```jsx
import { useAuth } from '../auth/AuthContext'

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <section>
      <h1>แดชบอร์ด</h1>
      <p>ยินดีต้อนรับ {user.full_name}</p>
      <p className="muted">
        ตัวเลขคิวงาน สุขภาพสต็อก และการเงิน จะเพิ่มในเฟส 7
      </p>
    </section>
  )
}
```

- [ ] **Step 7: เขียนทับ `frontend/src/App.jsx`**

```jsx
import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './auth/ProtectedRoute'
import AppShell from './components/AppShell'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
```

เส้นทางของอีก 17 หน้าจะทยอยเพิ่มในเฟสถัดไป ตอนนี้ทุก path ที่ยังไม่มีจะเด้งกลับแดชบอร์ด

- [ ] **Step 8: ต่อท้าย `frontend/src/styles.css`**

```css
.shell {
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 100vh;
}

.sidebar {
  background: #1f2933;
  color: #e4e7eb;
  padding: 16px 0;
}

.brand {
  font-size: 18px;
  font-weight: 600;
  padding: 0 16px 16px;
}

.sidebar nav {
  display: flex;
  flex-direction: column;
}

.sidebar a {
  color: #cbd2d9;
  text-decoration: none;
  padding: 9px 16px;
  font-size: 14px;
}

.sidebar a:hover {
  background: #323f4b;
}

.sidebar a.active {
  background: #1f6feb;
  color: #fff;
}

.topbar {
  background: #fff;
  border-bottom: 1px solid #e4e7eb;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.topbar button {
  border: 1px solid #cbd2d9;
  background: #fff;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
}

main {
  padding: 24px;
}

.muted {
  color: #7b8794;
}

.loading {
  padding: 24px;
}
```

- [ ] **Step 9: รันเทสต์ให้ผ่าน**

Run: `cd frontend && npm test`
Expected: PASS 10 passed (login 2 + nav 5 + protected route 3)

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: add role-aware navigation, protected routes and app shell"
```

---

## Task 10: ยืนยันทั้งระบบและเขียน README

**Files:**
- Create: `README.md`
- Modify: `frontend/src/api/client.js`
- Create: `frontend/tests/client.test.js`

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1-9
- Produces: เอกสารวิธีรันโปรเจกต์ และ interceptor ที่เตะผู้ใช้ออกเมื่อโทเคนหมดอายุ

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `frontend/tests/client.test.js`

```js
import { beforeEach, describe, expect, it } from 'vitest'

import client from '../src/api/client'

describe('axios client', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('แนบ Authorization header เมื่อมี token', () => {
    localStorage.setItem('token', 'token-123')
    const handler = client.interceptors.request.handlers[0].fulfilled
    const config = handler({ headers: {} })

    expect(config.headers.Authorization).toBe('Bearer token-123')
  })

  it('ไม่แนบ header เมื่อไม่มี token', () => {
    const handler = client.interceptors.request.handlers[0].fulfilled
    const config = handler({ headers: {} })

    expect(config.headers.Authorization).toBeUndefined()
  })

  it('ลบ token ทิ้งเมื่อเซิร์ฟเวอร์ตอบ 401', async () => {
    localStorage.setItem('token', 'token-123')
    const handler = client.interceptors.response.handlers[0].rejected

    await expect(handler({ response: { status: 401 } })).rejects.toBeTruthy()
    expect(localStorage.getItem('token')).toBeNull()
  })
})
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าไม่ผ่าน**

Run: `cd frontend && npm test`
Expected: FAIL ที่เทสต์ตัวที่สาม เพราะยังไม่มี response interceptor

- [ ] **Step 3: เติม response interceptor ใน `frontend/src/api/client.js`**

เพิ่มก่อนบรรทัด `export default client`

```js
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  },
)
```

ลบแค่ token ไม่ต้อง redirect ที่นี่ เพราะ `ProtectedRoute` จะพาไปหน้าล็อกอินเองในการ render รอบถัดไป การสั่ง `window.location` ตรงนี้จะทำให้เทสต์พังและทำให้ผู้ใช้เสียข้อมูลในฟอร์มที่ยังไม่ได้บันทึก

- [ ] **Step 4: รันเทสต์ทั้งหมดสองฝั่ง**

```bash
cd backend && python -m pytest tests/ -v
cd ../frontend && npm test
```

Expected: backend 28 passed, frontend 13 passed

- [ ] **Step 5: ทดสอบด้วยมือทั้งเส้นทาง**

เปิดสองหน้าต่าง

```bash
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

เข้า http://localhost:5173 แล้วตรวจทีละข้อ

1. ยังไม่ล็อกอิน เข้า `/` แล้วเด้งไป `/login`
2. ใส่รหัสผิด เห็นข้อความ `ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง`
3. ล็อกอินด้วย `owner` / `owner1234` เข้าแดชบอร์ดได้ เมนูซ้ายมี 18 รายการ
4. รีเฟรชหน้า ยังล็อกอินอยู่
5. กดออกจากระบบ กลับไปหน้าล็อกอิน
6. สร้างผู้ใช้ช่างผ่าน Swagger ที่ http://localhost:8000/docs แล้วล็อกอินด้วยบัญชีช่าง เมนูซ้ายต้องเหลือ 8 รายการ ไม่มีออกบิล ขายหน้าร้าน รายการบิล โปรโมชั่น รายงาน ผู้ใช้ ตั้งค่า และติดตามรอบบำรุงรักษา
7. ล็อกอินเป็นช่างแล้วพิมพ์ `/settings` บน address bar ต้องเด้งกลับแดชบอร์ด

- [ ] **Step 6: เขียน `README.md`**

````markdown
# ระบบจัดการอู่ซ่อมรถ

โปรเจกต์จบ ระบบจัดการอู่ซ่อมรถสาขาเดียว รับซ่อมรถยนต์และมอเตอร์ไซค์

## เอกสาร

- `new_scenario_summary.md` — ข้อกำหนดและข้อตัดสินใจทั้งหมด
- `screens.md` — หน้าจอ 18 หน้าและสิทธิ์การเข้าถึง
- `data_model.md` — โครงสร้างฐานข้อมูล
- `docs/superpowers/plans/` — แผน implementation รายเฟส

## เทคโนโลยี

Backend FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL
Frontend React 18 + Vite + React Router

## เตรียมเครื่อง

```bash
psql -U postgres -c "create user garage with password 'garage';"
psql -U postgres -c "create database garage owner garage;"
psql -U postgres -c "create database garage_test owner garage;"
```

## รัน backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed --username owner --password owner1234 --full-name "เจ้าของอู่"
uvicorn app.main:app --reload
```

เอกสาร API อัตโนมัติอยู่ที่ http://localhost:8000/docs

## รัน frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## รันเทสต์

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npm test
```
````

- [ ] **Step 7: Commit**

```bash
git add README.md frontend/
git commit -m "docs: add readme and handle expired tokens in api client"
```

---

## เสร็จเฟส 1 แล้วได้อะไร

- ล็อกอินได้จริงทั้งสามบทบาท โทเคนหมดอายุแล้วถูกเตะออกเอง
- เมนูและเส้นทางกรองตามบทบาทแล้ว ช่างพิมพ์ URL ตรงเข้าหน้าต้องห้ามไม่ได้
- ฐานข้อมูลมี migration เป็นลำดับ ย้อนกลับได้ และมีฐานข้อมูลเทสต์แยก
- เทสต์ 41 ตัวรันผ่าน เป็นฐานให้เฟสถัดไปเพิ่มต่อโดยไม่ต้องรื้อ
- `require_roles` และ fixture `client` พร้อมให้ทุก endpoint ในเฟส 2-7 ใช้ซ้ำทันที

## สิ่งที่ยังไม่ทำในเฟสนี้ โดยตั้งใจ

- หน้าจออีก 17 หน้ายังเป็นเส้นทางว่าง เด้งกลับแดชบอร์ด
- ยังไม่มีตารางอื่นนอกจาก users
- ยังไม่มี refresh token ผู้ใช้ล็อกอินใหม่เมื่อครบ 8 ชั่วโมง ซึ่งพอสำหรับอู่ที่เปิดเป็นกะ
