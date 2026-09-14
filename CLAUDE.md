# กฎของโปรเจกต์นี้

อ่านไฟล์นี้ก่อนเริ่มทำอะไรทุกครั้ง

## เลือก skill ตามประเภทงาน

| งาน | ใช้ skill |
|---|---|
| วางแผน ออกแบบ คิดฟีเจอร์ใหม่ แก้บั๊ก ตรวจงาน ทุกอย่างที่ไม่ใช่การพิมพ์โค้ด | `superpowers:*` |
| เขียนโค้ด แก้โค้ด refactor เลือก library | `ponytail:ponytail` |
| ทำ UI จัดหน้าจอ เลือกสี typography | `ui-ux-pro-max:ui-ux-pro-max` |

**ลำดับเมื่องานหนึ่งเข้าหลายข้อ** — `superpowers` กำหนดแนวทางก่อน แล้ว `ponytail` กับ
`ui-ux-pro-max` เป็นตัวลงมือ

- "ทำฟีเจอร์ X" → `superpowers:brainstorming` → `superpowers:writing-plans` → ตอนเขียนโค้ดจริงใช้ `ponytail`
- "แก้บั๊ก" → `superpowers:systematic-debugging` → ตอนแก้โค้ดจริงใช้ `ponytail`
- "ทำหน้าจอ X" → `superpowers:brainstorming` → `ui-ux-pro-max` → เขียนโค้ดด้วย `ponytail`

## ข้อยกเว้นที่ทับ skill

- **เขียนเทสต์เฉพาะตรรกะ สิทธิ์ และเงิน** สามอย่างนี้พังแบบเงียบ ๆ ไม่มีใครเห็น
  ตรรกะคือฟังก์ชันคำนวณและแฮชรหัสผ่าน/JWT สิทธิ์คือตารางสามบทบาทใน `screens.md`
  เงินคือทุกอย่างที่แตะตัวเลขเงินหรือสต็อก — FIFO ปัดเศษ VAT จองเลขที่เอกสาร คืนของเข้า Lot เดิม
  ตรงนี้ใช้ `superpowers:test-driven-development` เต็มรูปแบบ เขียนเทสต์ให้แดงก่อนแล้วค่อยเขียนโค้ด
- **ไม่เขียนเทสต์ให้ CRUD ธรรมดา หน้าจอ และ frontend** เปิดดูแล้วรู้ทันทีว่าผิด
  ตรวจด้วยมือผ่าน Swagger หน้าเว็บ และ psql ตามรายการตรวจของแต่ละ task
  เกณฑ์ตัดสินคือ **ถ้าเปิดดูแล้วรู้ว่าผิด ให้เปิดดู ถ้าเปิดดูแล้วไม่รู้ ต้องเขียนเทสต์**
- **อย่าเสนอเพิ่มตารางหรือฟีเจอร์นอกสเปก** ขอบเขตปิดแล้วที่ 21 ตาราง 18 หน้าจอ

## เอกสารอ้างอิง

| ไฟล์ | เนื้อหา |
|---|---|
| `new_scenario_summary.md` | ข้อกำหนดและข้อตัดสินใจของระบบ |
| `screens.md` | หน้าจอ 18 หน้าและตารางสิทธิ์ |
| `data_model.md` | โครงสร้างฐานข้อมูล 21 ตาราง |
| `docs/superpowers/plans/` | แผน implementation รายเฟส (ไม่อยู่ใน git) |
| `docs/explain/` | คำอธิบายโค้ดรายส่วน (ไม่อยู่ใน git) |

เมื่อ implement เสร็จหนึ่ง task ให้เขียนคำอธิบายโค้ดลง `docs/explain/task-NN-<ชื่อ>.md`
บอกว่าแต่ละส่วนทำอะไร ทำไมเขียนแบบนั้น และคำถามที่มักถูกถามกับจุดนั้น

## เทคโนโลยี

Backend FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 18
Frontend React 18 + Vite + React Router (**JavaScript ไม่ใช่ TypeScript**)

รัน backend `cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload`
รัน migration `cd backend && ./.venv/Scripts/python.exe -m alembic upgrade head`
psql อยู่ที่ `C:\Program Files\PostgreSQL\18\bin\psql.exe` ไม่ได้อยู่ใน PATH

## กฎที่ห้ามผิด

- เงินและจำนวนสินค้าใช้ `Decimal` เท่านั้น ห้าม `float` ยอดรวม `numeric(12,2)` ราคา/ต้นทุนต่อหน่วย `numeric(14,4)` จำนวน `numeric(12,3)`
- เวลาใช้ `datetime.now(timezone.utc)` ห้าม `datetime.now()` เปล่า
- `id` ทุกตารางเป็น `Integer` เขียน `mapped_column(primary_key=True)` เฉย ๆ ไม่ต้องระบุชนิด
- ราคาที่แสดงบนหน้าจอและที่คุยกับลูกค้าเป็นราคารวม VAT แล้ว ถอด VAT ตอนออกบิลเท่านั้น
- ห้ามใช้ `SEQUENCE` ของ PostgreSQL ออกเลขที่เอกสาร ใช้ `max(doc_number) + 1` จาก `invoices` ภายใต้ `pg_advisory_xact_lock(71001)` ในทรานแซกชันเดียวกับการ insert บิล
- ค่าตั้งทุกตัวใน `config.py` ไม่มีค่าเริ่มต้น ค่าจริงอยู่ที่ `.env` ที่เดียว
- เพิ่มโมเดลใหม่ต้องเพิ่ม import ใน `alembic/env.py` ทุกครั้ง
- ข้อความที่ผู้ใช้เห็นเป็นภาษาไทย ชื่อตัวแปร ตาราง คอลัมน์ เป็นภาษาอังกฤษ
