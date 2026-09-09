# Phase 1 — Foundation & Auth Implementation Plan

**Goal:** วางโครงโปรเจกต์ทั้งสองฝั่ง เชื่อม PostgreSQL ได้ และมีระบบล็อกอินที่แยกสิทธิ์สามบทบาทใช้งานได้จริงตั้งแต่หน้าเว็บถึงฐานข้อมูล

**Architecture:** Backend เป็น FastAPI + SQLAlchemy 2.0 แบบ sync (endpoint เป็น `def` ธรรมดา FastAPI จะรันใน threadpool ให้เอง) แยกชั้นเป็น `models` / `schemas` / `core` / `api` ให้ชัดตั้งแต่ต้นเพราะเฟสหลัง ๆ มีตารางเพิ่มอีกยี่สิบกว่าตาราง ยืนยันตัวตนด้วย JWT เก็บใน localStorage ฝั่ง React แล้วส่งกลับมาเป็น Bearer token การตรวจสิทธิ์ทำที่ dependency ของ FastAPI ไม่ใช่ในตัว endpoint เพื่อให้เฟสหลังเอาไปใช้ซ้ำได้ทันที

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, psycopg 3, PyJWT, bcrypt / React 18 (JavaScript ไม่ใช้ TypeScript), Vite, React Router 6, axios / PostgreSQL 15+

**Spec:**
- `new_scenario_summary.md` — ข้อตัดสินใจทั้งหมดของระบบ
- `screens.md` — รายการหน้าจอ 18 หน้าและตารางสิทธิ์
- `data_model.md` — โครงสร้างฐานข้อมูลและกฎที่ต้องบังคับในฐานข้อมูล

## วิธีตรวจงาน

**เฟส 1 ตรวจด้วยมือ ไม่เขียนเทสต์อัตโนมัติ** ทุก task จบด้วยรายการตรวจที่ทำได้จริงผ่าน Swagger ที่
`http://localhost:8000/docs` หรือผ่านหน้าเว็บ เพราะสิ่งที่เฟสนี้สร้างเป็นล็อกอินกับหน้าจอ
ซึ่งกดดูแล้วรู้ทันทีว่าถูกหรือผิด

**เฟส 3-5 จะกลับมาเขียนเทสต์เฉพาะสามเรื่องที่มองด้วยตาไม่เห็น**

| เรื่อง | ทำไมตาไม่เห็น |
|---|---|
| ตัดสต็อกแบบ FIFO | หน้าจอขึ้นว่าสำเร็จเหมือนกันหมด ไม่ว่าจะตัดจาก Lot ถูกหรือผิดใบ ต้องเปิดตาราง `stock_lots` ดูทีละแถว |
| ปัดเศษ VAT | ยอดรวมดูปกติทุกกรณี ต้องบวกทีละบรรทัดเทียบเองถึงจะเห็นว่าเศษหายไปบาทสองบาท |
| จองเลขที่เอกสาร | เลขข้ามจะเห็นก็ต่อเมื่อไล่เรียงทั้งเดือน และเกิดเฉพาะตอนบันทึกไม่สำเร็จซึ่งจำลองด้วยมือยาก |

โครงเทสต์ (`backend/tests/conftest.py`) ยังอยู่ พร้อมใช้เมื่อถึงเฟส 3 — มันเตรียมฐานข้อมูลเทสต์
แยกต่างหากและทำให้ทุกเทสต์ย้อนข้อมูลตัวเองทิ้งเมื่อจบ

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

---

## Global Constraints

- **Python 3.12** / **Node 20 ขึ้นไป** / **PostgreSQL 15 ขึ้นไป**
- **Frontend เป็น JavaScript ไม่ใช้ TypeScript** ไฟล์ React ใช้นามสกุล `.jsx`
- **เงินทุกคอลัมน์เป็น `numeric(12,2)`** ฝั่ง Python รับเป็น `decimal.Decimal` เสมอ ห้ามใช้ `float` กับค่าเงินไม่ว่ากรณีใด
- **วันเวลาทุกคอลัมน์เป็น `timestamptz`** ฝั่ง Python ใช้ `datetime.now(timezone.utc)` ห้ามใช้ `datetime.now()` เปล่า
- **`id` ของทุกตารางเป็น `BigInteger`** ตาม `data_model.md` เพื่อให้คอลัมน์ที่อ้างถึงกันเป็นชนิดเดียวกันทั้งระบบ
- **ราคาที่แสดงบนหน้าจอและที่คุยกับลูกค้าเป็นราคารวม VAT แล้ว** การถอด VAT ทำตอนออกบิลเท่านั้น
- **ห้ามใช้ `SEQUENCE` ของ PostgreSQL ออกเลขที่เอกสาร** เพราะ `nextval()` ไม่ย้อนกลับตอน rollback (บังคับใช้จริงในเฟส 5)
- **ทุกการกระทำต้องบันทึกว่าใครทำ** ตารางที่บันทึกการกระทำต้องมีคอลัมน์ `*_by` อ้าง `users.id`
- **ข้อความที่ผู้ใช้เห็นเป็นภาษาไทย** รวมถึงข้อความ error จาก API ส่วนชื่อตัวแปร ตาราง และคอลัมน์เป็นภาษาอังกฤษ
- **บทบาทมีสามค่าเท่านั้น** `admin` / `employee` / `mechanic` ตรงกับตารางสิทธิ์ใน `screens.md`
- **ค่าตั้งทุกตัวใน `config.py` ไม่มีค่าเริ่มต้น** ค่าจริงอยู่ที่ `.env` ที่เดียว ขาดตัวใดตัวหนึ่งแอปต้องไม่สตาร์ต
- **ทุกโมเดลใหม่ต้องเพิ่มบรรทัด import ใน `alembic/env.py`** ถ้าลืม Alembic จะสร้าง migration ที่ลบตารางทิ้ง
- **ทุก task จบด้วยการตรวจด้วยมือตามรายการของ task นั้น แล้วจึง commit**

---

## File Structure

### Backend

| ไฟล์ | หน้าที่ |
|---|---|
| `backend/app/config.py` | ประกาศว่าระบบมีค่าตั้งอะไรบ้าง ค่าจริงอยู่ที่ `.env` |
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
| `backend/tests/conftest.py` | โครงเทสต์ ยังไม่ได้ใช้ในเฟสนี้ เตรียมไว้ให้เฟส 3-5 |

แยก `core/security.py` ออกจาก `core/deps.py` เพราะตัวแรกเป็นฟังก์ชันบริสุทธิ์ที่ไม่ยุ่งกับฐานข้อมูล
ส่วนตัวหลังผูกกับ request และ session

### Frontend

| ไฟล์ | หน้าที่ |
|---|---|
| `frontend/src/api/client.js` | axios instance ที่แนบ token และจัดการ 401 ที่เดียว |
| `frontend/src/auth/AuthContext.jsx` | สถานะผู้ใช้ปัจจุบัน ล็อกอิน ล็อกเอาต์ |
| `frontend/src/auth/ProtectedRoute.jsx` | กันหน้าที่ต้องล็อกอินและกันหน้าที่บทบาทเข้าไม่ได้ |
| `frontend/src/nav.js` | นิยามเมนู 18 หน้าและบทบาทที่เห็นแต่ละหน้า |
| `frontend/src/components/AppShell.jsx` | โครงหน้าจอ แถบเมนูซ้าย หัวข้อบน ปุ่มออกจากระบบ |
| `frontend/src/pages/LoginPage.jsx` | หน้าเข้าสู่ระบบ |
| `frontend/src/pages/DashboardPage.jsx` | หน้าแดชบอร์ดเปล่าไว้ยืนยันว่าล็อกอินแล้วเข้าถึงได้ |
| `frontend/src/App.jsx` | เส้นทางทั้งหมด |

---

## Task 1: โครงโปรเจกต์ ฐานข้อมูล และ health check — ✅ เสร็จแล้ว

commits `4aa5157`, `6a36358`, `c1cd6cf`, `441515e`

สร้าง `.gitignore`, `backend/requirements.txt`, `backend/.env`, `backend/.env.example`,
`backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`

ผลที่ตรวจแล้ว — `select 1` ผ่าน engine คืนค่า 1 / `GET /api/health` คืน `{"status":"ok"}` /
ซ่อนไฟล์ `.env` แล้วแอปไม่สตาร์ตและฟ้องครบทั้งสี่ค่า

คำอธิบายอยู่ที่ `docs/explain/task-01-scaffold-and-config.md`

---

## Task 2: ตาราง users และ Alembic migration — ✅ เสร็จแล้ว

commits `3747b70`, `3b42e54`

สร้าง `backend/app/models/base.py`, `backend/app/models/user.py`, `backend/alembic.ini`,
`backend/alembic/env.py`, `backend/alembic/versions/0001_create_users.py`,
`backend/tests/conftest.py`

ผลที่ตรวจแล้ว — `\d users` แสดง `id bigint`, unique `username`, `users_role_check`,
`created_at timestamptz default now()`

คำอธิบายอยู่ที่ `docs/explain/task-02-users-table-and-migrations.md`

---

## Task 3: แฮชรหัสผ่านและ JWT

**Files:**
- Create: `backend/app/core/security.py`

**Interfaces:**
- Consumes: `app.config.settings`
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, password_hash: str) -> bool`, `create_access_token(user_id: int, role: str) -> str`, `decode_access_token(token: str) -> dict` (คืน dict ที่มีคีย์ `sub` เป็น str ของ user id และ `role`)

- [ ] **Step 1: เขียน `backend/app/core/security.py`**

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

bcrypt รับได้สูงสุด 72 ไบต์ ตัวอักษรไทยหนึ่งตัวกินสามไบต์ รหัสผ่านไทย 25 ตัวก็ชนเพดานแล้ว จึงตัดที่
72 ไบต์ทั้งตอนแฮชและตอนตรวจให้ตรงกัน ไม่งั้น bcrypt จะโยน error ใส่ผู้ใช้

- [ ] **Step 2: ตรวจด้วยมือ**

```bash
cd backend
./.venv/Scripts/python.exe -c "
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
h1 = hash_password('รหัสผ่าน123')
h2 = hash_password('รหัสผ่าน123')
print('แฮชไม่ใช่รหัสเดิม  :', h1 != 'รหัสผ่าน123')
print('แฮชสองครั้งไม่ซ้ำ   :', h1 != h2)
print('รหัสถูกผ่าน        :', verify_password('รหัสผ่าน123', h1))
print('รหัสผิดไม่ผ่าน      :', not verify_password('รหัสผ่าน124', h1))
t = create_access_token(7, 'mechanic')
p = decode_access_token(t)
print('token เก็บ id/role  :', p['sub'] == '7' and p['role'] == 'mechanic')
"
```

ต้องได้ `True` ทั้งห้าบรรทัด

จุดที่ควรสังเกตคือบรรทัด "แฮชสองครั้งไม่ซ้ำ" — bcrypt สุ่ม salt ใหม่ทุกครั้ง รหัสผ่านเดียวกันจึงได้แฮช
คนละค่า ทำให้คนที่ขโมยฐานข้อมูลไปไม่สามารถดูออกว่าผู้ใช้คนไหนใช้รหัสผ่านซ้ำกัน

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/security.py
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

**Interfaces:**
- Consumes: `User`, `verify_password`, `create_access_token`
- Produces: `app.core.deps.get_db`, `POST /api/auth/login` (รับ `{username, password}` คืน `{access_token, token_type, user}`), `app.schemas.user.UserOut`

- [ ] **Step 1: เขียน `backend/app/schemas/user.py`**

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

- [ ] **Step 2: เขียน `backend/app/schemas/auth.py`**

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

- [ ] **Step 3: เขียน `backend/app/core/deps.py`**

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

- [ ] **Step 4: เขียน `backend/app/api/auth.py`**

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

ข้อความ error ของรหัสผิดกับของชื่อผู้ใช้ไม่มีเป็นข้อความเดียวกันโดยตั้งใจ ถ้าแยกกันคนร้ายจะลองยิง
ชื่อผู้ใช้ไปเรื่อย ๆ เพื่อดูว่าชื่อไหนมีอยู่จริงในระบบ

- [ ] **Step 5: แก้ `backend/app/main.py` ให้รวม router**

เพิ่ม `from app.api import auth` ไว้บนสุด และ `app.include_router(auth.router)` ไว้ก่อน endpoint health

- [ ] **Step 6: ตรวจด้วยมือ**

ยังไม่มีผู้ใช้ในฐานข้อมูล จึงสร้างชั่วคราวหนึ่งคนก่อน (Task 7 จะทำสคริปต์ถาวร)

```bash
cd backend
./.venv/Scripts/python.exe -c "
from app.db import SessionLocal
from app.models.user import User
from app.core.security import hash_password
db = SessionLocal()
db.add(User(username='owner', password_hash=hash_password('owner1234'), full_name='เจ้าของอู่', role='admin'))
db.commit()
print('สร้างผู้ใช้ owner แล้ว')
"
uvicorn app.main:app --reload
```

เปิด `http://localhost:8000/docs` แล้วตรวจทีละข้อ

1. `POST /api/auth/login` ด้วย `owner` / `owner1234` → ได้ 200 พร้อม `access_token` และ `user.role` เป็น `admin`
2. ใน response ต้อง **ไม่มี** `password_hash` โผล่มา
3. ล็อกอินด้วยรหัสผิด → 401 พร้อมข้อความ `ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง`
4. ล็อกอินด้วยชื่อที่ไม่มีในระบบ → 401 ข้อความ**เหมือนกันเป๊ะ**กับข้อ 3
5. ปิดบัญชีด้วย `update users set is_active = false where username = 'owner';` แล้วล็อกอินอีกครั้ง → 401 (อย่าลืมเปิดคืน)

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: add login endpoint returning jwt and user profile"
```

---

## Task 5: ตรวจสิทธิ์ด้วย dependency และ endpoint ดูข้อมูลตัวเอง

**Files:**
- Modify: `backend/app/core/deps.py`
- Modify: `backend/app/api/auth.py`

**Interfaces:**
- Consumes: `get_db`, `decode_access_token`, `User`
- Produces: `get_current_user() -> User`, `require_roles(*roles: str)` (คืน dependency ที่ให้ `User` และโยน 403 ถ้าบทบาทไม่ตรง), `GET /api/auth/me`

- [ ] **Step 1: เขียนทับ `backend/app/core/deps.py`**

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

`get_current_user` อ่านผู้ใช้จากฐานข้อมูลใหม่ทุกครั้งแทนที่จะเชื่อ `role` ในโทเคน เพราะเจ้าของอู่
อาจปิดบัญชีหรือเปลี่ยนบทบาทระหว่างที่โทเคนเก่ายังไม่หมดอายุ

**401 กับ 403 ต่างกัน** 401 คือ "ไม่รู้ว่าคุณเป็นใคร" ส่วน 403 คือ "รู้ว่าคุณเป็นใครแต่คุณเข้าตรงนี้ไม่ได้"

- [ ] **Step 2: เติม endpoint `/me` ใน `backend/app/api/auth.py`**

เพิ่ม `get_current_user` เข้าไปใน import แล้วต่อท้ายไฟล์

```python
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 3: ตรวจด้วยมือ**

เปิด `http://localhost:8000/docs` กด **Authorize** มุมขวาบน แล้ววาง `access_token` ที่ได้จากการล็อกอิน

1. `GET /api/auth/me` พร้อม token → 200 คืนข้อมูลผู้ใช้ที่ล็อกอินอยู่
2. `GET /api/auth/me` โดยไม่ส่ง token → 401
3. ส่ง token มั่ว ๆ เช่น `Bearer not-a-token` → 401
4. ปิดบัญชีด้วย SQL ระหว่างที่ token ยังไม่หมดอายุ แล้วเรียก `/me` ด้วย token เดิม → **401 ทันที** ไม่ต้องรอหมดอายุ (อย่าลืมเปิดคืน)

ข้อ 4 คือหัวใจของ task นี้ ถ้ามันคืน 200 แปลว่าโค้ดกำลังเชื่อข้อมูลในโทเคนแทนที่จะอ่านจากฐานข้อมูล

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add role-based dependencies and current user endpoint"
```

---

## Task 6: จัดการผู้ใช้สำหรับ admin

**Files:**
- Create: `backend/app/api/users.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `require_roles`, `get_db`, `hash_password`, `UserCreate`, `UserActiveUpdate`, `UserOut`
- Produces: `GET /api/users`, `POST /api/users`, `PATCH /api/users/{user_id}/active` ทั้งสามต้องเป็น admin เท่านั้น

- [ ] **Step 1: เขียน `backend/app/api/users.py`**

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

เงื่อนไขสุดท้ายกันเคสที่ admin คนเดียวของระบบปิดบัญชีตัวเอง แล้วไม่มีใครเข้าไปเปิดคืนได้อีกเลย

- [ ] **Step 2: แก้ `backend/app/main.py`**

```python
from app.api import auth, users

app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 3: ตรวจด้วยมือ**

ล็อกอินเป็น `owner` แล้ว Authorize ใน Swagger

1. `POST /api/users` สร้างช่าง `{"username":"chang","password":"chang1234","full_name":"ช่างหนึ่ง","role":"mechanic"}` → 201
2. สร้างพนักงาน `{"username":"staff","password":"staff1234","full_name":"พนักงานหน้าร้าน","role":"employee"}` → 201
3. `GET /api/users` → 200 เห็นสามคน
4. สร้างซ้ำชื่อ `owner` → 409 `ชื่อผู้ใช้นี้ถูกใช้ไปแล้ว`
5. สร้างด้วย `"role":"owner"` → **422** (FastAPI ปฏิเสธตั้งแต่ตรวจรูปแบบ ยังไม่ทันเข้าโค้ดเรา)
6. สร้างด้วยรหัสผ่าน 3 ตัว → 422
7. `PATCH /api/users/{id ของ staff}/active` ด้วย `{"is_active": false}` → 200
8. `PATCH` ปิดบัญชีตัวเอง → 400 `ปิดการใช้งานบัญชีของตัวเองไม่ได้`
9. ล็อกอินเป็น `chang` เอา token ไป Authorize แล้วเรียก `GET /api/users` → **403**

ข้อ 9 คือข้อสำคัญที่สุด มันพิสูจน์ว่า `require_roles` ทำงาน ตรวจในฐานข้อมูลด้วยว่ารหัสผ่านถูกเก็บ
เป็นแฮชจริง

```bash
psql -U garage -h localhost -d garage -c "select username, role, left(password_hash, 20) from users;"
```

คอลัมน์สุดท้ายต้องขึ้นต้นด้วย `$2b$` ไม่ใช่รหัสผ่านที่พิมพ์เข้าไป

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add admin-only user management endpoints"
```

---

## Task 7: สคริปต์สร้าง admin คนแรก

**Files:**
- Create: `backend/app/seed.py`

**Interfaces:**
- Consumes: `SessionLocal`, `User`, `hash_password`
- Produces: `create_admin(db, username, password, full_name) -> User` และรันจาก command line ได้

- [ ] **Step 1: เขียน `backend/app/seed.py`**

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

**ทำไมต้องมีสคริปต์นี้** เพราะ `POST /api/users` ต้องเป็น admin ถึงจะเรียกได้ แต่ตอนติดตั้งระบบใหม่
ยังไม่มี admin สักคน สคริปต์นี้คือทางเดียวที่จะสร้างคนแรกโดยไม่ต้องเปิดช่องโหว่ให้ใครก็สมัครเป็น
admin ได้ผ่าน API

- [ ] **Step 2: ตรวจด้วยมือ**

```bash
cd backend
./.venv/Scripts/python.exe -m app.seed --username boss --password boss1234 --full-name "เจ้าของอู่คนที่สอง"
```

1. ครั้งแรกต้องพิมพ์ `สร้างผู้ใช้ boss เรียบร้อย`
2. รันคำสั่งเดิมซ้ำ → ต้องขึ้น `ValueError: มีผู้ใช้ชื่อ boss อยู่แล้ว` และในฐานข้อมูลต้องมี `boss` แค่คนเดียว
3. ล็อกอินด้วย `boss` / `boss1234` ผ่าน Swagger ได้จริง

```bash
psql -U garage -h localhost -d garage -c "select count(*) from users where username = 'boss';"
```

ต้องได้ `1`

- [ ] **Step 3: Commit**

```bash
git add backend/app/seed.py
git commit -m "feat: add seed script for first admin user"
```

---

## Task 8: โครง React และหน้าเข้าสู่ระบบ

**Files:**
- Create: `frontend/` ทั้งโปรเจกต์
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/auth/AuthContext.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/main.jsx`, `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `POST /api/auth/login`, `GET /api/auth/me`
- Produces: `useAuth()` คืน `{ user, loading, login(username, password), logout() }`, default export `client` จาก `api/client.js`

- [ ] **Step 1: สร้างโปรเจกต์**

```bash
cd /c/Users/PAT/Desktop/Garage
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install react-router-dom@6.28.0 axios@1.7.9
```

ลบไฟล์ตัวอย่างที่ Vite แถมมา — `src/App.css`, `src/index.css`, `src/assets/`

- [ ] **Step 2: เขียน `frontend/.env.example` แล้วก๊อปเป็น `.env`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 3: เขียน `frontend/src/api/client.js`**

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

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  },
)

export default client
```

interceptor ตัวแรกแนบ token ให้ทุก request อัตโนมัติ จะได้ไม่ต้องเขียน header เองทุกหน้า
ตัวที่สองลบ token ทิ้งเมื่อเซิร์ฟเวอร์ตอบ 401 ซึ่งแปลว่าโทเคนหมดอายุหรือบัญชีถูกปิด
ไม่ต้องสั่งเปลี่ยนหน้าตรงนี้ เพราะ `ProtectedRoute` ใน Task 9 จะพาไปหน้าล็อกอินเองในการ render รอบถัดไป

- [ ] **Step 4: เขียน `frontend/src/auth/AuthContext.jsx`**

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

`useEffect` ตอนเปิดเว็บทำหน้าที่สำคัญ — ถ้ามี token ค้างใน localStorage ให้ถามเซิร์ฟเวอร์ว่ายังใช้ได้ไหม
ผู้ใช้จึงไม่ต้องล็อกอินใหม่ทุกครั้งที่รีเฟรชหน้า และถ้าโทเคนใช้ไม่ได้แล้วก็ลบทิ้งทันที
`loading` มีไว้กันหน้าจอกะพริบไปหน้าล็อกอินระหว่างที่ยังถามเซิร์ฟเวอร์ไม่เสร็จ

- [ ] **Step 5: เขียน `frontend/src/pages/LoginPage.jsx`**

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

`disabled={submitting}` กันผู้ใช้กดปุ่มรัว ๆ ตอนเน็ตช้าแล้วยิงคำขอซ้ำหลายรอบ

- [ ] **Step 6: เขียน `frontend/src/styles.css`**

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

- [ ] **Step 7: เขียน `frontend/src/main.jsx` และ `App.jsx` ชั่วคราว**

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

- [ ] **Step 8: ตรวจด้วยมือ**

เปิดสองหน้าต่าง `uvicorn app.main:app --reload` กับ `npm run dev` แล้วเข้า `http://localhost:5173`

1. เห็นหน้าล็อกอิน
2. ใส่รหัสผิด → เห็นข้อความ `ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง` บนหน้าจอ ไม่ใช่แค่ใน console
3. ใส่ `owner` / `owner1234` → ไม่มี error เปิด DevTools แท็บ Application → Local Storage เห็นคีย์ `token` มีค่าอยู่
4. แท็บ Network ดู request `login` → มี `Authorization` header ในคำขอถัดไป
5. ปิด uvicorn แล้วลองล็อกอิน → เห็น `เชื่อมต่อเซิร์ฟเวอร์ไม่ได้`

ข้อ 5 พิสูจน์ว่าโค้ดแยกกรณี "เซิร์ฟเวอร์ตอบว่าผิด" ออกจาก "ติดต่อเซิร์ฟเวอร์ไม่ได้"

- [ ] **Step 9: Commit**

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

**Interfaces:**
- Consumes: `useAuth()`
- Produces: `MENU` (อาร์เรย์ของ `{ path, label, roles }`), `menuForRole(role)`, `<ProtectedRoute roles={[...]}>`

- [ ] **Step 1: เขียน `frontend/src/nav.js`**

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

หมายเหตุ ใน `screens.md` โปรโมชั่นกับผู้ใช้ถูกยุบเข้าหน้าตั้งค่าเพื่อให้นับได้ 18 หน้า ที่นี่แยกเป็นเมนู
ของตัวเองเพราะเมนูคือทางเข้า ไม่ใช่หน่วยนับหน้าจอ ส่วนที่หายไปคือหน้าล็อกอิน (ไม่ใช่เมนู) และ
หน้ารายละเอียดใบงาน (เข้าจากรายการใบงาน) จำนวนจึงเท่ากันพอดี

- [ ] **Step 2: เขียน `frontend/src/auth/ProtectedRoute.jsx`**

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

ลำดับการตรวจสำคัญ ต้องเช็ค `loading` ก่อนเสมอ ไม่งั้นตอนเปิดเว็บครั้งแรกที่ยังถาม `/me` ไม่เสร็จ
`user` จะยังเป็น `null` แล้วผู้ใช้ที่ล็อกอินอยู่จะถูกเด้งออกไปหน้าล็อกอินทุกครั้งที่รีเฟรช

- [ ] **Step 3: เขียน `frontend/src/components/AppShell.jsx`**

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

- [ ] **Step 4: เขียน `frontend/src/pages/DashboardPage.jsx`**

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

- [ ] **Step 5: เขียนทับ `frontend/src/App.jsx`**

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

- [ ] **Step 6: ต่อท้าย `frontend/src/styles.css`**

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

- [ ] **Step 7: ตรวจด้วยมือ — นี่คือรายการตรวจที่สำคัญที่สุดของทั้งเฟส**

| # | ทำอะไร | ต้องได้อะไร |
|---|---|---|
| 1 | ยังไม่ล็อกอิน เข้า `http://localhost:5173/` | เด้งไปหน้า `/login` |
| 2 | ล็อกอินเป็น `owner` (admin) | เข้าแดชบอร์ด เมนูซ้ายมี **18 รายการ** |
| 3 | กด F5 รีเฟรช | ยังล็อกอินอยู่ ไม่เด้งออก |
| 4 | กดออกจากระบบ | กลับหน้าล็อกอิน และ `token` ใน Local Storage หายไป |
| 5 | ล็อกอินเป็น `staff` (employee) | เมนูเหลือ **13 รายการ** ไม่มีโปรโมชั่น รายงานการเงิน รายงานภาษี ผู้ใช้ ตั้งค่า |
| 6 | ล็อกอินเป็น `chang` (mechanic) | เมนูเหลือ **8 รายการ** ไม่มีออกบิล ขายหน้าร้าน รายการบิล ติดตามรอบบำรุงรักษา ใบสั่งซื้อ และทั้งห้ารายการของข้อ 5 |
| 7 | ขณะเป็น `chang` พิมพ์ `/settings` บน address bar | เด้งกลับแดชบอร์ด |
| 8 | ขณะเป็น `chang` พิมพ์ `/reports/financial` | เด้งกลับแดชบอร์ด |

ข้อ 7 กับ 8 สำคัญเพราะพิสูจน์ว่าการซ่อนเมนูไม่ใช่การป้องกัน คนที่รู้ URL ยังพิมพ์เข้ามาเองได้
ต้องมี `ProtectedRoute` กันอีกชั้น

**และต้องเข้าใจให้ชัดว่า** การกันทั้งหมดนี้เป็นเรื่องของหน้าจอเท่านั้น ตัวที่กันจริงคือ `require_roles`
ฝั่ง backend เพราะใครก็แก้โค้ด JavaScript ในเบราว์เซอร์ตัวเองได้

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: add role-aware navigation, protected routes and app shell"
```

---

## Task 10: ตรวจทั้งระบบและเขียน README

**Files:**
- Create: `README.md`

- [ ] **Step 1: ตรวจเส้นทางเต็มอีกรอบจากศูนย์**

ปิดทั้งสองเซิร์ฟเวอร์ ล้าง Local Storage ในเบราว์เซอร์ แล้วเริ่มใหม่ตั้งแต่ต้น ไล่รายการตรวจของ
Task 9 ทั้งแปดข้ออีกครั้ง เพื่อยืนยันว่าไม่มีอะไรพึ่งสถานะค้างจากการทดสอบก่อนหน้า

- [ ] **Step 2: ตรวจว่าไฟล์ลับไม่ขึ้น git**

```bash
git status --short
git ls-files | grep -E "\.env$" && echo "อันตราย มี .env ถูก track" || echo "ปลอดภัย .env ไม่ถูก track"
```

- [ ] **Step 3: เขียน `README.md`**

````markdown
# ระบบจัดการอู่ซ่อมรถ

โปรเจกต์จบ ระบบจัดการอู่ซ่อมรถสาขาเดียว รับซ่อมรถยนต์และมอเตอร์ไซค์

## เอกสาร

- `new_scenario_summary.md` — ข้อกำหนดและข้อตัดสินใจทั้งหมด
- `screens.md` — หน้าจอ 18 หน้าและสิทธิ์การเข้าถึง
- `data_model.md` — โครงสร้างฐานข้อมูล
- `docs/explain/` — คำอธิบายโค้ดรายส่วน
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
cp .env.example .env      # แล้วเติม JWT_SECRET
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

## วิธีตรวจงาน

เฟส 1-2 ตรวจด้วยมือผ่าน Swagger และหน้าเว็บ รายการตรวจอยู่ในแผนของแต่ละเฟส
เฟส 3-5 จะมีเทสต์อัตโนมัติเฉพาะการตัดสต็อก FIFO การปัดเศษ VAT และการจองเลขที่เอกสาร
ซึ่งเป็นสามเรื่องที่ตรวจด้วยตาไม่ได้
````

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add readme"
```

---

## เสร็จเฟส 1 แล้วได้อะไร

- ล็อกอินได้จริงทั้งสามบทบาท โทเคนหมดอายุหรือบัญชีถูกปิดแล้วถูกเตะออกทันที
- เมนูและเส้นทางกรองตามบทบาทแล้ว ช่างพิมพ์ URL ตรงเข้าหน้าต้องห้ามไม่ได้
- ฐานข้อมูลมี migration เป็นลำดับ ย้อนกลับได้ และมีฐานข้อมูลเทสต์แยกไว้ให้เฟสหลัง
- `require_roles` พร้อมให้ทุก endpoint ในเฟส 2-7 ใช้ซ้ำทันที

## สิ่งที่ยังไม่ทำในเฟสนี้ โดยตั้งใจ

- หน้าจออีก 17 หน้ายังเป็นเส้นทางว่าง เด้งกลับแดชบอร์ด
- ยังไม่มีตารางอื่นนอกจาก users
- ยังไม่มี refresh token ผู้ใช้ล็อกอินใหม่เมื่อครบ 8 ชั่วโมง ซึ่งพอสำหรับอู่ที่เปิดเป็นกะ
