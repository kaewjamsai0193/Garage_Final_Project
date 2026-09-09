# Task 2 — ตาราง users, Alembic migration และโครงเทสต์

**ไฟล์ที่เกิดขึ้น** `backend/app/models/base.py`, `backend/app/models/user.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_users.py`, `backend/tests/conftest.py`, `backend/tests/test_user_model.py`

**ผลลัพธ์** ตาราง `users` มีอยู่จริงในฐานข้อมูล สร้างด้วย migration ที่ย้อนกลับได้ และมีโครงเทสต์ที่ทุก task ต่อจากนี้จะใช้

---

## 1. `models/base.py` คลาสแม่ของทุกตาราง

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

ตัวคลาสว่างเปล่า แต่หน้าที่ของมันคือเป็น **จุดรวมทะเบียนตาราง** ทุกโมเดลที่สืบทอด `Base` จะถูกบันทึกไว้ใน
`Base.metadata` โดยอัตโนมัติ

`Base.metadata` คือสิ่งที่ Alembic เอาไปเทียบกับฐานข้อมูลจริงเพื่อหาว่า "โค้ดมีตารางอะไรที่ฐานข้อมูลยังไม่มี"
ถ้าไม่มีคลาสกลางตัวนี้ Alembic จะไม่รู้จักตารางของเราเลย

---

## 2. `models/user.py` นิยามตาราง

```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role in ('admin', 'employee', 'mechanic')",
            name="users_role_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

### `Mapped[...]` กับ `mapped_column(...)` ต่างกันยังไง

`Mapped[str]` เป็นการบอก **Python** ว่าฟิลด์นี้เป็น str เอาไว้ให้ตัวช่วยใน editor เตือนเวลาเขียนผิด
ส่วน `mapped_column(...)` เป็นการบอก **ฐานข้อมูล** ว่าคอลัมน์นี้ชนิดอะไร ยาวเท่าไหร่ ห้ามว่างหรือไม่
สองอันนี้คนละเรื่องกัน เขียนคู่กันเสมอ

### `CheckConstraint` ทำไมต้องมีทั้งที่โค้ดก็ตรวจอยู่แล้ว

`role` รับได้แค่สามค่า ถ้าตรวจแค่ในโค้ด Python วันหนึ่งมีคนเผลอ `update users set role='owner'` ตรง ๆ
ผ่าน psql ข้อมูลเสียทันทีโดยไม่มีอะไรกั้น

หลักคือ **กฎที่ห้ามผิดเด็ดขาดให้ฐานข้อมูลบังคับ** เพราะฐานข้อมูลคือด่านสุดท้ายที่ทุกทางเข้าต้องผ่าน
ไม่ว่าจะมาจาก API สคริปต์ หรือคนพิมพ์ SQL เอง เรื่องนี้จะกลับมาอีกในเฟส 4 (รถหนึ่งคันเปิดใบงานค้าง
ได้ใบเดียว) และเฟส 5 (เลขที่บิลห้ามข้าม)

### `server_default` ต่างจาก `default` ยังไง

- `default="true"` — Python เป็นคนใส่ค่าให้ตอนสร้างอ็อบเจกต์
- `server_default="true"` — **ฐานข้อมูล** เป็นคนใส่ให้ตอน INSERT

เลือกอย่างหลังเพราะถ้าวันหนึ่งมีคน INSERT ผ่าน SQL ตรง ๆ โดยไม่ผ่านโค้ด Python ค่า default
ก็ยังทำงาน `created_at` ใช้ `func.now()` ซึ่งกลายเป็น `now()` ของ PostgreSQL ด้วยเหตุผลเดียวกัน
และยังได้เวลาจากนาฬิกาของเซิร์ฟเวอร์ฐานข้อมูลตัวเดียว ไม่ใช่นาฬิกาของเครื่องแอปที่อาจเดินไม่ตรงกัน

### `DateTime(timezone=True)` ทำไมต้องมี timezone

ถ้าไม่ใส่ ฐานข้อมูลจะเก็บเป็น `timestamp` เปล่า ๆ ซึ่งไม่รู้ว่าเวลานั้นเป็นเวลาโซนไหน พอระบบ
มีการออกบิลและรายงานภาษีรายเดือน การคำนวณว่า "บิลใบนี้อยู่เดือนไหน" จะผิดได้ที่ขอบเดือน
กฎของโปรเจกต์นี้กำหนดไว้ว่าคอลัมน์เวลาทุกตัวเป็น `timestamptz`

### เรื่อง `BigInteger` — จุดที่โค้ดขัดกับสเปกและตัดสินยังไง

แผน implementation เขียนไว้ว่า `mapped_column(primary_key=True)` เฉย ๆ ซึ่ง SQLAlchemy จะแปลเป็น
`serial` (จำนวนเต็ม 4 ไบต์) แต่เอกสาร `data_model.md` กำหนดว่าทุกตารางใช้ `bigserial` (8 ไบต์)

เลือกตาม `data_model.md` เพราะเป็นเอกสารข้อกำหนด ส่วนแผนเป็นแค่วิธีทำให้ถึงข้อกำหนดนั้น เมื่อสองอย่าง
ขัดกัน ข้อกำหนดชนะ เหตุผลเชิงเทคนิคด้วยคือถ้าตารางนี้เป็น int4 แต่ตารางอื่นเป็น int8 คอลัมน์ที่อ้างถึงกัน
จะคนละชนิด ทำให้ index ทำงานได้ไม่เต็มที่และต้องมาไล่แก้ทีหลัง

---

## 3. Alembic — migration คืออะไร

**ปัญหาที่ migration แก้** ถ้าสร้างตารางด้วยการพิมพ์ `create table` ใน psql เอง วันที่ต้องเอาโปรเจกต์
ไปลงเครื่องใหม่ จะไม่มีใครรู้ว่าต้องพิมพ์อะไรบ้างตามลำดับไหน และถ้าเพิ่มคอลัมน์ทีหลังก็จะจำไม่ได้ว่า
เครื่องไหนอัปเดตแล้วหรือยัง

Alembic แก้ด้วยการเก็บการเปลี่ยนแปลงโครงสร้างฐานข้อมูลเป็นไฟล์เรียงลำดับ แต่ละไฟล์คือหนึ่งขั้น
และในฐานข้อมูลมีตาราง `alembic_version` จดไว้ว่าตอนนี้อยู่ขั้นไหนแล้ว

### `alembic/env.py` — สามบรรทัดที่สำคัญ

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
```

บอก Alembic ให้ใช้ URL จาก `config.py` ของเรา ไม่ใช่ค่าที่เขียนไว้ใน `alembic.ini` ประโยชน์คือ
รหัสผ่านฐานข้อมูลอยู่ที่ `.env` ที่เดียว ไม่ต้องเขียนซ้ำใน `alembic.ini` ที่จะถูก commit ขึ้น git

```python
target_metadata = Base.metadata
```

บอก Alembic ว่า "หน้าตาที่ควรจะเป็น" อยู่ที่นี่ เวลา autogenerate มันจะเทียบตัวนี้กับฐานข้อมูลจริง

```python
import app.models.user  # noqa: F401
```

บรรทัดนี้ดูเหมือนไม่ได้ใช้อะไรเลย และ editor จะขีดเส้นใต้เตือนว่า import มาแล้วไม่ได้ใช้
แต่มันจำเป็น เพราะคลาส `User` จะถูกลงทะเบียนใน `Base.metadata` ก็ต่อเมื่อไฟล์นั้นถูก import แล้วเท่านั้น

**ข้อควรระวังที่ต้องจำไปตลอดโปรเจกต์** ทุกครั้งที่เพิ่มโมเดลใหม่ในเฟสถัดไป ต้องเพิ่มบรรทัด import
ที่ไฟล์นี้ด้วย ถ้าลืม Alembic จะมองไม่เห็นตารางใหม่ และที่แย่กว่านั้นคือมันจะคิดว่าตารางเก่าที่มีในฐานข้อมูล
"ไม่ควรมี" แล้วสร้าง migration ที่ลบตารางทิ้ง `# noqa: F401` คือการบอกเครื่องมือตรวจโค้ดว่า
บรรทัดนี้ตั้งใจให้เป็นแบบนี้

### migration ที่ได้

```python
def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        ...
        sa.CheckConstraint("role in ('admin', 'employee', 'mechanic')", name='users_role_check'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )


def downgrade() -> None:
    op.drop_table('users')
```

`upgrade()` คือเดินหน้า `downgrade()` คือถอยกลับ การมี `downgrade()` ทำให้ทดลองแล้วย้อนได้

**ข้อควรระวัง** `--autogenerate` เป็นแค่ตัวช่วยร่าง ไม่ใช่คำตอบสุดท้าย ต้องเปิดไฟล์อ่านทุกครั้งว่าได้
สิ่งที่ต้องการจริงหรือเปล่า ใน task นี้ตรวจแล้วว่ามีครบทั้ง unique ของ `username` และ check ของ `role`

ผลลัพธ์จริงในฐานข้อมูลหลังรัน `alembic upgrade head`

```
 id            | bigint                   | not null | nextval('users_id_seq'::regclass)
 username      | character varying(50)    | not null |
 ...
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "users_username_key" UNIQUE CONSTRAINT, btree (username)
Check constraints:
    "users_role_check" CHECK (role::text = ANY (...))
```

---

## 4. `tests/conftest.py` โครงเทสต์ที่ทั้งโปรเจกต์ใช้

`conftest.py` เป็นชื่อพิเศษของ pytest ทุกอย่างที่ประกาศในไฟล์นี้ ไฟล์เทสต์ในโฟลเดอร์เดียวกันเรียกใช้ได้
โดยไม่ต้อง import

### ก. ทำไมตั้ง environment variable ไว้บนสุดของไฟล์

```python
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://garage:garage@localhost:5432/garage_test"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
...
from app.config import settings  # noqa: E402
```

จำจาก Task 1 ได้ว่า `settings = Settings()` ถูกสร้างตอน **import โมดูล** ถ้าตั้ง environment variable
ทีหลัง `settings` จะอ่านค่าจาก `.env` ไปแล้ว แปลว่าเทสต์จะไปวิ่งบนฐานข้อมูลจริง แล้วโดน
`drop schema public cascade` ลบข้อมูลจริงทิ้งทั้งหมด

นี่คือเหตุผลเดียวที่ยอมวาง import ไว้กลางไฟล์ซึ่งผิดธรรมเนียมปกติ `# noqa: E402` คือการประกาศว่า
รู้ตัวและตั้งใจ

### ข. fixture ที่เตรียมฐานข้อมูลเทสต์

```python
@pytest.fixture(scope="session", autouse=True)
def migrate_test_database():
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade"))
        connection.execute(text("create schema public"))

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
    yield
```

- `scope="session"` — ทำครั้งเดียวต่อการรันเทสต์หนึ่งรอบ ไม่ใช่ทำใหม่ทุกเทสต์
- `autouse=True` — ทำงานเองโดยไม่ต้องมีเทสต์ไหนร้องขอ

มันลบ schema ทิ้งทั้งหมดแล้วรัน migration ใหม่ ได้ประโยชน์สองอย่างพร้อมกัน คือเทสต์เริ่มจาก
ฐานข้อมูลสะอาดเสมอ และเป็นการ**ทดสอบ migration ไปในตัว** ถ้า migration พัง เทสต์จะพังทันที

### ค. fixture ที่ทำให้เทสต์ไม่ทิ้งขยะ — จุดที่ฉลาดที่สุดในไฟล์นี้

```python
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
```

อ่านจากล่างขึ้นบน สิ่งที่เกิดขึ้นคือ

1. เปิด connection แล้วเปิด transaction ครอบไว้ก่อน
2. สร้าง session ที่ผูกกับ connection นั้น
3. ส่งให้เทสต์ใช้
4. พอเทสต์จบ **`transaction.rollback()`** ย้อนทุกอย่างที่เทสต์ทำไป

ผลคือข้อมูลที่เทสต์สร้างหายเกลี้ยงเสมอ เทสต์ตัวถัดไปจึงเริ่มจากตารางว่าง ไม่มีทางที่เทสต์ตัวหนึ่ง
จะทำอีกตัวพังเพราะข้อมูลค้าง และไม่ต้องเขียนโค้ดลบข้อมูลท้ายเทสต์เอง

**`join_transaction_mode="create_savepoint"` คือหัวใจ** ปัญหาที่มันแก้คือ endpoint จริงจะเรียก
`db.commit()` ซึ่งปกติจะปิด transaction ไปเลย แล้ว `rollback()` ท้ายเทสต์จะไม่มีอะไรให้ย้อน
ข้อมูลจะค้างในฐานข้อมูลเทสต์

พารามิเตอร์นี้บอก SQLAlchemy ว่า ในเมื่อ connection มี transaction ครอบอยู่แล้ว ให้ session
สร้าง **savepoint** ซ้อนข้างในแทน เวลา endpoint สั่ง `commit()` มันจะ commit แค่ savepoint นั้น
ส่วน transaction ชั้นนอกยังเปิดอยู่ พอเทสต์จบ `rollback()` ชั้นนอกจึงย้อนได้ทุกอย่างจริง

savepoint คือจุดพักภายในทรานแซกชัน เปรียบเหมือน save point ในเกม ย้อนกลับมาจุดนี้ได้โดยไม่ต้อง
เริ่มใหม่ทั้งด่าน

### ง. fixture `client`

```python
@pytest.fixture()
def client(db_session):
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

`dependency_overrides` เป็นความสามารถของ FastAPI ที่ให้สลับตัวจริงเป็นตัวปลอมตอนเทสต์ได้
ตรงนี้บอกว่า "เวลา endpoint ขอ session จากฐานข้อมูล ให้ยื่น session ของเทสต์ให้แทน"

ถ้าไม่ทำแบบนี้ endpoint จะเปิด session ของตัวเองที่อยู่คนละ transaction กับเทสต์ ผลคือข้อมูลที่
เทสต์เตรียมไว้ endpoint จะมองไม่เห็น และข้อมูลที่ endpoint เขียนก็จะไม่ถูก rollback

**`from app.core.deps import get_db` ทำไมอยู่ข้างในฟังก์ชัน** เพราะตอนเขียน Task 2 ไฟล์
`app/core/deps.py` ยังไม่มี (จะสร้างใน Task 4) ถ้า import ไว้บนสุดของไฟล์ เทสต์ของ Task 2
จะพังทันทีเพราะหาโมดูลไม่เจอ การย้ายมาไว้ข้างในทำให้บรรทัดนี้ทำงานเฉพาะตอนที่มีเทสต์เรียกใช้
fixture `client` จริง ๆ ซึ่งเริ่มเกิดขึ้นใน Task 4

---

## 5. เทสต์สามตัวและสิ่งที่แต่ละตัวพิสูจน์

| เทสต์ | พิสูจน์อะไร |
|---|---|
| `test_can_insert_and_read_user` | บันทึกและอ่านกลับได้ ค่า default ของ `is_active` และ `created_at` ทำงานจริง |
| `test_username_must_be_unique` | ฐานข้อมูลปฏิเสธชื่อผู้ใช้ซ้ำ ด้วย `IntegrityError` |
| `test_role_must_be_one_of_three` | `CheckConstraint` ทำงานจริง ใส่ `role='owner'` แล้วฐานข้อมูลไม่ยอม |

สองตัวหลังใช้ `pytest.raises(IntegrityError)` ซึ่งแปลว่า "เทสต์นี้ผ่านก็ต่อเมื่อคำสั่งข้างในพัง"
เป็นวิธีทดสอบว่ากฎที่ตั้งไว้บังคับได้จริง ไม่ใช่แค่เขียนไว้เฉย ๆ

`db_session.flush()` คือการส่งคำสั่ง SQL ลงฐานข้อมูลโดยยังไม่ commit ใช้ตรงนี้เพราะต้องการให้
ฐานข้อมูลตรวจ constraint เดี๋ยวนั้นเลยจะได้เห็นว่ามัน error จริง

---

## คำถามที่มักถูกถามกับ task นี้

| คำถาม | คำตอบ |
|---|---|
| migration คืออะไร ทำไมไม่พิมพ์ `create table` เอง | migration เก็บการเปลี่ยนโครงสร้างเป็นไฟล์เรียงลำดับ ย้ายเครื่องหรืออัปเดตทีหลังก็รันตามลำดับได้ และมีตาราง `alembic_version` จดว่าฐานนี้อยู่ขั้นไหนแล้ว |
| ทำไมตรวจ role ทั้งในโค้ดและในฐานข้อมูล | ฐานข้อมูลคือด่านสุดท้ายที่ทุกทางเข้าต้องผ่าน ถ้ามีคน INSERT ตรงผ่าน SQL โค้ด Python กันไม่ได้ |
| `server_default` ต่างจาก `default` ยังไง | `default` Python เป็นคนใส่ `server_default` ฐานข้อมูลเป็นคนใส่ อย่างหลังทำงานแม้ INSERT ตรงผ่าน SQL |
| ทำไมเทสต์ไม่ทิ้งข้อมูลค้าง | ทุกเทสต์ทำงานในทรานแซกชันที่ถูก rollback ทิ้งเมื่อจบ ข้อมูลจึงไม่เคยถูกบันทึกจริง |
| `commit()` ใน endpoint จะทำให้ rollback ไม่ทำงานไหม | ไม่ เพราะตั้ง `join_transaction_mode="create_savepoint"` ทำให้ `commit()` ปิดแค่ savepoint ข้างใน ส่วนทรานแซกชันชั้นนอกของเทสต์ยังเปิดอยู่ |
| ถ้าเพิ่มตารางใหม่แล้วลืมทำอะไร | ลืม `import` โมเดลใหม่ใน `alembic/env.py` ผลคือ Alembic มองไม่เห็นตารางใหม่ และอาจสร้าง migration ที่ลบตารางเก่าทิ้ง |
| ทำไม `id` เป็น `bigint` ไม่ใช่ `int` | `data_model.md` กำหนดว่าทุกตารางใช้ `bigserial` และถ้าตารางหนึ่งเป็น int4 แต่ตารางที่อ้างถึงเป็น int8 ชนิดจะไม่ตรงกัน ทำให้ index ทำงานได้ไม่เต็มที่ |
