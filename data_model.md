# โครงสร้างฐานข้อมูล

PostgreSQL อ้างอิงข้อตัดสินใจใน `new_scenario_summary.md` และหน้าจอใน `screens.md`

เงินทุกคอลัมน์เป็น `numeric(12,2)` วันเวลาเป็น `timestamptz` ทุกตารางมี `id bigserial` เว้นที่ระบุไว้เป็นอย่างอื่น

---

## ผู้ใช้

**users** — `username` unique, `password_hash`, `full_name`, `role` (admin / employee / mechanic), `is_active`, `created_at`

ทุกตารางที่บันทึกการกระทำอ้าง `users.id` ผ่านคอลัมน์ `*_by` ไม่มีการกระทำไหนที่ไม่รู้ว่าใครทำ

---

## ลูกค้าและรถ

**customers** — `phone` unique, `name`, `address`, `tax_id`, `created_at`

ลูกค้าขาจรที่ซื้อของหน้าร้านไม่ถูกบันทึกที่นี่ ข้อมูลผู้ซื้อ (ถ้าขอใบกำกับเต็มรูป) ไปอยู่บนบิลโดยตรง

**vehicles** — `customer_id`, `plate` unique, `vehicle_type` (car / motorcycle), `brand`, `model`, `year`, `notes`

---

## สินค้าและคลัง

**products** — `code` unique, `name`, `unit`, `sale_price`, `min_stock` default 0, `maintenance_cycle_months` nullable, `warranty_days` default 0, `is_active`

- `sale_price` เป็นราคารวม VAT ตามที่ตกลงว่าราคาที่คุยกับลูกค้าคือราคาจ่ายจริง
- `min_stock` = 0 คือไม่เตือน
- `maintenance_cycle_months` เป็น null คือไม่สร้างรายการเตือน

**stock_lots** — `product_id`, `receipt_item_id`, `received_at`, `unit_cost` (ก่อน VAT), `qty_received`, `qty_remaining`

- หนึ่งครั้งที่รับของ = หนึ่ง Lot เสมอ ไม่ว่าจะมาทางใบสั่งซื้อหรือซื้อด่วน
- FIFO เรียงตาม `received_at` แล้ว `id`
- `qty_remaining` เป็นตัวเลขที่เก็บไว้จริง ไม่คำนวณสดจาก movements เพราะทุกการตัดสต็อกต้อง lock แถวอยู่แล้ว

**stock_movements** — `product_id`, `lot_id`, `qty` (บวกคือเข้า ลบคือออก), `movement_type` (receive / issue / return / adjust), `ref_type`, `ref_id`, `reason`, `created_by`, `created_at`

- บัญชีเดินสะพัดของคลังทั้งหมด ทุกการเคลื่อนไหวลงที่นี่หมด
- การคืนของอ้าง `lot_id` เดิมเสมอ ไม่สร้าง Lot ใหม่ ต้นทุนจึงไม่เพี้ยน
- `movement_type = adjust` บังคับต้องมี `reason`

---

## จัดซื้อ

**suppliers** — `name`, `phone`, `tax_id`

**purchase_orders** — `po_number` unique, `supplier_id`, `status` (open / closed / cancelled), `created_by`, `created_at`

**purchase_order_items** — `po_id`, `product_id`, `qty_ordered`, `qty_received`, `unit_price`

ปิดใบเมื่อ `qty_received` ครบทุกรายการ หรือปิดทิ้งเมื่อร้านส่งไม่ได้ รับไม่ครบไม่ใช่ข้อผิดพลาด

**goods_receipts** — `receipt_number`, `supplier_id`, `po_id` nullable, `receipt_type` (po / urgent), `supplier_invoice_no` nullable, `supplier_invoice_date` nullable, `created_by`, `created_at`

- `receipt_type = urgent` คือซื้อด่วนหน้างาน `po_id` เป็น null
- ใบกำกับของร้านเป็นข้อมูลไม่บังคับ ถ้า `supplier_invoice_no` เป็น null ใบรับนั้นไม่เข้ารายงานภาษีซื้อ

**goods_receipt_items** — `receipt_id`, `product_id`, `qty`, `unit_cost` (ก่อน VAT), `vat_amount`

- ถ้าไม่มีใบกำกับ `unit_cost` คือราคาที่จ่ายทั้งจำนวนและ `vat_amount` เป็น 0
- ทุกแถวสร้าง `stock_lots` หนึ่งแถวและ `stock_movements` แบบ receive หนึ่งแถว

---

## ใบงาน

**job_orders** — `job_number` unique, `vehicle_id`, `customer_id`, `mileage`, `symptom`, `status` (pending / in_progress / done / closed / cancelled), `waiting_parts` boolean, `cancel_reason`, `opened_by`, `opened_at`, `closed_at`

- `waiting_parts` เป็นป้ายกำกับแยกจาก `status` ระบบเปิดปิดเอง คนแก้ไม่ได้
- `status` เดินหน้าทางเดียว pending → in_progress → done → closed ส่วน cancelled แยกออกมา
- `cancel_reason` บังคับเมื่อ `status = cancelled`

**job_order_mechanics** — `job_id`, `user_id`, `is_primary` — คีย์รวม (job_id, user_id)

หนึ่งใบมีช่างหลักได้คนเดียว บังคับด้วย partial unique index รายงานผลงานช่างนับเฉพาะแถวที่ `is_primary`

**job_status_history** — `job_id`, `from_status`, `to_status`, `changed_by`, `changed_at`

ทั้งสามบทบาทเลื่อนสถานะได้ ตารางนี้คือคำตอบว่าใครเลื่อน

---

## ใบเสนอราคา

**quotations** — `job_id`, `version`, `status` (draft / approved / superseded), `labor_total`, `parts_total`, `grand_total`, `created_by`, `created_at`, `approved_by`, `approved_at`

- ยอดทุกตัวเป็นราคารวม VAT ตรงกับที่ลูกค้าเห็น
- หนึ่งใบงานมีได้หลายเวอร์ชัน ใบเก่าเปลี่ยนเป็น `superseded` ไม่ถูกลบ
- `approved_by` ต้องเป็น admin หรือ employee เท่านั้น ช่างกดไม่ได้
- แถวที่ `status = approved` แก้ไม่ได้ บังคับด้วย trigger

**quotation_items** — `quotation_id`, `product_id`, `qty`, `unit_price` (รวม VAT), `line_total`

ตอนอนุมัติเวอร์ชันใหม่ ระบบเทียบกับเวอร์ชันที่อนุมัติไปก่อนหน้าแล้วตัดหรือคืนเฉพาะส่วนต่าง ไม่คืนทั้งชุดแล้วตัดใหม่

---

## บิลและการรับเงิน

**invoices** — `doc_type` (tax_invoice / warranty_claim), `doc_year`, `doc_number`, `invoice_type` (repair / counter_sale), `job_id` nullable, `customer_id` nullable, `buyer_name`, `buyer_address`, `buyer_tax_id`, `tax_invoice_form` (abbreviated / full), `promotion_id` nullable, `discount_amount`, `subtotal_ex_vat`, `vat_amount`, `grand_total`, `gross_profit`, `status` (issued / cancelled), `cancel_reason`, `issued_by`, `issued_at`

- `(doc_type, doc_year, doc_number)` unique — งานเคลมอยู่คนละ `doc_type` จึงไม่กินเลขใบกำกับ
- ข้อมูลผู้ซื้อสามคอลัมน์เป็นสำเนา ไม่ใช่ foreign key ลูกค้าย้ายที่อยู่แล้วบิลเก่าไม่เปลี่ยนตาม
- `gross_profit` คำนวณและเก็บตอนออกบิล ไม่คำนวณสดตอนดูรายงาน
- บิลขายหน้าร้าน `job_id` เป็น null บิลงานซ่อมมีเสมอ

**invoice_items** — `invoice_id`, `item_type` (part / labor), `product_id` nullable, `description`, `qty`, `unit_price` (รวม VAT), `line_total`, `warranty_expires_on` nullable

ค่าแรงเป็นแถวเดียวต่อบิล `item_type = labor` และ `product_id` เป็น null บิลขายหน้าร้านมีแถว labor ไม่ได้

**invoice_item_lots** — `invoice_item_id`, `lot_id`, `qty`, `unit_cost`

ต้นทุนจริงที่ถูกตัดต่อ Lot หนึ่งรายการขายอาจกินหลาย Lot ตารางนี้คือฐานของ `gross_profit` และเป็นตัวที่ทำให้คืนของกลับ Lot เดิมได้ถูกต้อง

**payments** — `invoice_id`, `amount_received`, `withholding_amount`, `method`, `received_by`, `received_at`

รับครั้งเดียวต่อบิล ระบบถือว่าครบเมื่อ `amount_received + withholding_amount = grand_total` แล้วปิดใบงานอัตโนมัติ

**document_sequences** — `doc_type`, `doc_year`, `last_number` — คีย์รวม (doc_type, doc_year)

---

## โปรโมชั่นและรับประกัน

**promotions** — `name`, `scope` (all / parts / labor), `discount_type` (percent / amount), `value`, `start_date`, `end_date`, `is_active`

บิลเก็บ `promotion_id` ไว้อ้างอิงแต่ยอดส่วนลดจริงเก็บเป็นตัวเลขที่ `invoices.discount_amount` แก้โปรโมชั่นทีหลังจึงไม่กระทบบิลเก่า

**warranties** — `invoice_id`, `invoice_item_id`, `vehicle_id`, `product_id` nullable, `warranty_type` (labor / part), `expires_on`

สร้างตอนออกบิลงานซ่อม หน้ารับรถเข้าอู่อ่านตารางนี้ด้วย `vehicle_id` กับ `expires_on >= today` เพื่อบอกว่ารายการไหนยังอยู่ในประกัน บิลขายหน้าร้านไม่สร้างแถวที่นี่เพราะไม่มีรถผูก

---

## รอบบำรุงรักษา

**maintenance_reminders** — `vehicle_id`, `product_id`, `due_date`, `source_invoice_id`, `status` (pending / closed), `created_at`

หนึ่งคู่ (รถ, สินค้า) มีรายการที่ยัง pending ได้รายการเดียว ถ้าลูกค้ากลับมาเปลี่ยนตัวเดิมก่อนกำหนด รายการเดิมถูกปิดแล้วสร้างรอบใหม่แทน ไม่เตือนซ้อน

**reminder_calls** — `reminder_id`, `result` (appointment / refused / no_answer), `note`, `called_by`, `called_at`

เก็บทุกครั้งที่โทร ไม่ทับของเดิม เพราะ KPI นับจำนวนครั้งที่โทรด้วย

---

## ตั้งค่า

**settings** — `key` เป็น primary key, `value`, `updated_by`, `updated_at`

เก็บข้อมูลอู่สำหรับหัวบิล จำนวนวันรับประกันค่าแรงเริ่มต้น และจำนวนวันที่นับว่าของค้างคลัง (ค่าเริ่มต้น 90)

---

## กฎที่ต้องบังคับในฐานข้อมูล ไม่ใช่ในโค้ดอย่างเดียว

**หนึ่งคันหนึ่งใบงานค้าง**

```sql
create unique index job_orders_one_active_per_vehicle
  on job_orders (vehicle_id)
  where status not in ('closed', 'cancelled');
```

**เลขที่เอกสารห้ามข้าม — ห้ามใช้ SEQUENCE ของ PostgreSQL**

`nextval()` ไม่ย้อนกลับเมื่อทรานแซกชัน rollback เลขจะหายไปหนึ่งใบทันทีที่บันทึกไม่สำเร็จ ซึ่งคือสิ่งที่ระบบพยายามกันไว้ตั้งแต่ต้น ต้องออกเลขด้วยการ lock แถวใน `document_sequences` ในทรานแซกชันเดียวกับการ insert บิล

```sql
update document_sequences
   set last_number = last_number + 1
 where doc_type = $1 and doc_year = $2
returning last_number;
```

**การตัดสต็อก FIFO** — `select ... from stock_lots where product_id = $1 and qty_remaining > 0 order by received_at, id for update` แล้วไล่หัก `qty_remaining` พร้อมเขียน `stock_movements` ในทรานแซกชันเดียวกัน การ lock ตามลำดับเดียวกันเสมอกัน deadlock เมื่อสองใบงานตัดสินค้าตัวเดียวกันพร้อมกัน

**qty_remaining ห้ามติดลบ** — `check (qty_remaining >= 0 and qty_remaining <= qty_received)`

**ช่างห้ามอนุมัติใบเสนอราคาและห้ามออกบิล** — บังคับที่ชั้นแอปพลิเคชัน และย้ำด้วย constraint ที่ตรวจว่า `approved_by` และ `issued_by` ต้องไม่ใช่ผู้ใช้ที่ `role = 'mechanic'`

**ยกเลิกใบงานได้เฉพาะตอนยังไม่แตะของ** — ตรวจว่าไม่มี `stock_movements` แบบ issue ที่อ้างใบงานนั้น ถ้ามีต้องไปทางออกบิลแทน

---

## จุดที่ควรระวังตอน implement

- **กำไรคำนวณตอนออกบิล** จากยอดขายก่อน VAT หลังหักส่วนลด ลบผลรวม `invoice_item_lots.qty * unit_cost` ทั้งสองฝั่งเป็นฐานก่อน VAT ถ้าเผลอเอา `grand_total` มาลบต้นทุน กำไรจะเกินจริง 7% ทุกใบ
- **ราคาบนหน้าจอรวม VAT แต่ในบิลต้องแยก** `subtotal_ex_vat = round(ยอดรวม / 1.07, 2)` แล้ว `vat_amount = grand_total - subtotal_ex_vat` เพื่อให้ผลรวมกลับมาเท่าเดิมเสมอ ไม่ปัดเศษสองรอบแยกกัน
- **ยกเลิกบิล** ต้องคืนของตาม `invoice_item_lots` กลับเข้า Lot เดิม เขียน `stock_movements` แบบ return และล้าง `gross_profit` แต่ห้ามลบแถวบิลและห้ามคืนเลขที่เอกสาร
- **รับของแล้วตัดให้ใบงานที่รออยู่** ทำในทรานแซกชันเดียวกับการรับของ เรียงตามเวลาที่ใบเสนอราคาได้รับอนุมัติ ตัดครบแล้วเซ็ต `waiting_parts = false`
