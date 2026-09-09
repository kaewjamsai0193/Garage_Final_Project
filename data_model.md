# โครงสร้างฐานข้อมูล

PostgreSQL อ้างอิงข้อตัดสินใจใน `new_scenario_summary.md` และหน้าจอใน `screens.md`

**26 ตาราง** เงินทุกคอลัมน์เป็น `numeric(12,2)` วันเวลาเป็น `timestamptz` `id` ของทุกตารางเป็น `bigserial`

สถานะการสร้างจริง — ตาราง `users` สร้างแล้ว (migration `0001`) ที่เหลือทยอยสร้างตามเฟสในแผน

---

## ภาพรวมความสัมพันธ์

```mermaid
erDiagram
    users ||--o{ job_orders : "เปิดใบงาน"
    users ||--o{ invoices : "ออกบิล"

    customers ||--o{ vehicles : "เป็นเจ้าของ"
    vehicles ||--o{ job_orders : "เข้าซ่อม"

    job_orders ||--o{ quotations : "เสนอราคาหลายเวอร์ชัน"
    job_orders ||--o| invoices : "ออกบิลเมื่อจบงาน"

    products ||--o{ stock_lots : "รับเข้าเป็นรอบ"
    stock_lots ||--o{ stock_movements : "เคลื่อนไหว"
    stock_lots ||--o{ invoice_item_lots : "ถูกตัดขาย"

    suppliers ||--o{ purchase_orders : "สั่งซื้อจาก"
    purchase_orders ||--o{ goods_receipts : "รับของตามใบสั่ง"
    goods_receipts ||--o{ stock_lots : "สร้าง Lot ใหม่"

    invoices ||--o{ invoice_items : "มีรายการ"
    invoice_items ||--o{ invoice_item_lots : "ตัดจาก Lot"
    invoices ||--|| payments : "รับเงินครั้งเดียว"
    invoices ||--o{ warranties : "ให้ประกัน"

    vehicles ||--o{ maintenance_reminders : "ถึงกำหนดเช็คระยะ"
    vehicles ||--o{ warranties : "อยู่ในประกัน"
```

เส้นที่ต้องอธิบายได้ตอนสอบ

- **`vehicles ||--o{ job_orders`** รถหนึ่งคันมีใบงานได้หลายใบ**ตลอดประวัติ** แต่ที่ยัง**ค้างอยู่**ได้ใบเดียว ซึ่งบังคับด้วย partial unique index ไม่ใช่ด้วยชนิดความสัมพันธ์
- **`job_orders ||--o| invoices`** ใบงานหนึ่งใบออกบิลได้ไม่เกินหนึ่งใบ และบิลขายหน้าร้านไม่มีใบงานเลย `job_id` จึงเป็น null ได้
- **`invoice_items ||--o{ invoice_item_lots`** หนึ่งรายการขายอาจกินหลาย Lot ตารางกลางนี้คือตัวที่ทำให้รู้ต้นทุนจริงและคืนของกลับ Lot เดิมได้

---

## 1. ผู้ใช้

```mermaid
erDiagram
    users {
        bigint id PK
        varchar username UK
        varchar password_hash
        varchar full_name
        varchar role "admin / employee / mechanic"
        boolean is_active
        timestamptz created_at
    }
```

`role` บังคับด้วย `CheckConstraint` ที่ฐานข้อมูล ไม่ใช่แค่ในโค้ด

ทุกตารางที่บันทึกการกระทำอ้าง `users.id` ผ่านคอลัมน์ `*_by` ไม่มีการกระทำไหนที่ไม่รู้ว่าใครทำ

---

## 2. ลูกค้าและรถ

```mermaid
erDiagram
    customers ||--o{ vehicles : "เป็นเจ้าของ"

    customers {
        bigint id PK
        varchar phone UK "ใช้ค้นเป็นอันดับแรก"
        varchar name
        varchar address
        varchar tax_id
        timestamptz created_at
    }

    vehicles {
        bigint id PK
        bigint customer_id FK
        varchar plate UK
        varchar vehicle_type "car / motorcycle"
        varchar brand
        varchar model
        int year
        text notes
    }
```

ลูกค้าขาจรที่ซื้อของหน้าร้านไม่ถูกบันทึกใน `customers` ข้อมูลผู้ซื้อ (ถ้าขอใบกำกับเต็มรูป)
ไปอยู่บนบิลโดยตรง

---

## 3. สินค้าและคลัง

```mermaid
erDiagram
    products ||--o{ stock_lots : "รับเข้าเป็นรอบ"
    stock_lots ||--o{ stock_movements : "ทุกการเคลื่อนไหว"
    goods_receipt_items ||--|| stock_lots : "หนึ่งแถวสร้างหนึ่ง Lot"

    products {
        bigint id PK
        varchar code UK
        varchar name
        varchar unit
        numeric sale_price "ราคารวม VAT"
        int min_stock "0 คือไม่เตือน"
        int maintenance_cycle_months "null คือไม่สร้างรายการเตือน"
        int warranty_days
        boolean is_active
    }

    stock_lots {
        bigint id PK
        bigint product_id FK
        bigint receipt_item_id FK
        timestamptz received_at "ใช้เรียงคิว FIFO"
        numeric unit_cost "ก่อน VAT"
        int qty_received
        int qty_remaining
    }

    stock_movements {
        bigint id PK
        bigint product_id FK
        bigint lot_id FK
        int qty "บวกคือเข้า ลบคือออก"
        varchar movement_type "receive / issue / return / adjust"
        varchar ref_type
        bigint ref_id
        text reason "บังคับเมื่อ adjust"
        bigint created_by FK
        timestamptz created_at
    }
```

**`stock_lots` คือหัวใจของระบบ** หนึ่งครั้งที่รับของ = หนึ่ง Lot เสมอ ไม่ว่าจะมาทางใบสั่งซื้อหรือ
ซื้อด่วน หัวเทียนทุน 80 กับทุน 120 จึงอยู่คนละแถว ทำให้คิดกำไรได้แม่น

FIFO เรียงตาม `received_at` แล้ว `id` ส่วน `qty_remaining` เป็นตัวเลขที่เก็บไว้จริง ไม่คำนวณสด
จาก movements เพราะทุกการตัดสต็อกต้อง lock แถวอยู่แล้ว

`stock_movements` คือบัญชีเดินสะพัดของคลังทั้งหมด การคืนของอ้าง `lot_id` เดิมเสมอ ไม่สร้าง Lot ใหม่
ต้นทุนจึงไม่เพี้ยน

---

## 4. จัดซื้อ

```mermaid
erDiagram
    suppliers ||--o{ purchase_orders : "สั่งซื้อจาก"
    suppliers ||--o{ goods_receipts : "รับของจาก"
    purchase_orders ||--o{ purchase_order_items : "มีรายการ"
    purchase_orders ||--o{ goods_receipts : "รับได้หลายครั้ง"
    goods_receipts ||--o{ goods_receipt_items : "มีรายการ"
    products ||--o{ purchase_order_items : "สั่ง"
    products ||--o{ goods_receipt_items : "รับ"

    suppliers {
        bigint id PK
        varchar name
        varchar phone
        varchar tax_id
    }

    purchase_orders {
        bigint id PK
        varchar po_number UK
        bigint supplier_id FK
        varchar status "open / closed / cancelled"
        bigint created_by FK
        timestamptz created_at
    }

    purchase_order_items {
        bigint id PK
        bigint po_id FK
        bigint product_id FK
        int qty_ordered
        int qty_received "รับไม่ครบไม่ใช่ข้อผิดพลาด"
        numeric unit_price
    }

    goods_receipts {
        bigint id PK
        varchar receipt_number
        bigint supplier_id FK
        bigint po_id FK "null เมื่อซื้อด่วน"
        varchar receipt_type "po / urgent"
        varchar supplier_invoice_no "ไม่บังคับ"
        date supplier_invoice_date "ไม่บังคับ"
        bigint created_by FK
        timestamptz created_at
    }

    goods_receipt_items {
        bigint id PK
        bigint receipt_id FK
        bigint product_id FK
        int qty
        numeric unit_cost "ก่อน VAT"
        numeric vat_amount "0 เมื่อไม่มีใบกำกับ"
    }
```

`receipt_type = urgent` คือซื้อด่วนหน้างาน `po_id` เป็น null

ใบกำกับของร้านเป็นข้อมูลไม่บังคับ เพราะร้านเล็กมักไม่ออกให้ ถ้า `supplier_invoice_no` เป็น null
ใบรับนั้นไม่เข้ารายงานภาษีซื้อ และ `unit_cost` คือราคาที่จ่ายทั้งจำนวนโดยไม่แยก VAT

---

## 5. ใบงานและใบเสนอราคา

```mermaid
erDiagram
    vehicles ||--o{ job_orders : "เข้าซ่อม"
    customers ||--o{ job_orders : "เจ้าของรถ"
    job_orders ||--o{ job_order_mechanics : "มอบหมายช่าง"
    job_orders ||--o{ job_status_history : "ประวัติสถานะ"
    job_orders ||--o{ quotations : "หลายเวอร์ชัน"
    quotations ||--o{ quotation_items : "มีรายการ"
    users ||--o{ job_order_mechanics : "เป็นช่าง"
    products ||--o{ quotation_items : "อะไหล่ที่เสนอ"

    job_orders {
        bigint id PK
        varchar job_number UK
        bigint vehicle_id FK
        bigint customer_id FK
        int mileage
        text symptom
        varchar status "pending / in_progress / done / closed / cancelled"
        boolean waiting_parts "ป้ายกำกับ ระบบเปิดปิดเอง"
        text cancel_reason
        bigint opened_by FK
        timestamptz opened_at
        timestamptz closed_at
    }

    job_order_mechanics {
        bigint job_id PK
        bigint user_id PK
        boolean is_primary "ช่างหลักได้คนเดียว"
    }

    job_status_history {
        bigint id PK
        bigint job_id FK
        varchar from_status
        varchar to_status
        bigint changed_by FK
        timestamptz changed_at
    }

    quotations {
        bigint id PK
        bigint job_id FK
        int version
        varchar status "draft / approved / superseded"
        numeric labor_total "รวม VAT"
        numeric parts_total "รวม VAT"
        numeric grand_total "รวม VAT"
        bigint created_by FK
        bigint approved_by FK "ห้ามเป็น mechanic"
        timestamptz approved_at
    }

    quotation_items {
        bigint id PK
        bigint quotation_id FK
        bigint product_id FK
        int qty
        numeric unit_price "รวม VAT"
        numeric line_total
    }
```

**`waiting_parts` เป็นคอลัมน์แยกจาก `status` ไม่ใช่ค่าหนึ่งใน status** เพราะช่างทำงานส่วนอื่นต่อได้
ระหว่างรออะไหล่ รถจึงอยู่สถานะ `in_progress` และติดป้ายรออะไหล่พร้อมกันได้

`status` เดินหน้าทางเดียว `pending → in_progress → done → closed` ส่วน `cancelled` แยกออกมา

ใบเสนอราคาเก็บทุกเวอร์ชัน ใบเก่าเปลี่ยนเป็น `superseded` ไม่ถูกลบ แถวที่ `status = approved`
แก้ไม่ได้ บังคับด้วย trigger

ตอนอนุมัติเวอร์ชันใหม่ ระบบเทียบกับเวอร์ชันที่อนุมัติไปก่อนหน้าแล้วตัดหรือคืน**เฉพาะส่วนต่าง**
ไม่คืนทั้งชุดแล้วตัดใหม่

---

## 6. บิลและการรับเงิน

```mermaid
erDiagram
    job_orders ||--o| invoices : "ออกบิลเมื่อจบงาน"
    customers ||--o{ invoices : "ลูกค้า"
    promotions ||--o{ invoices : "ส่วนลดที่ใช้"
    invoices ||--o{ invoice_items : "มีรายการ"
    invoices ||--|| payments : "รับเงินครั้งเดียว"
    invoice_items ||--o{ invoice_item_lots : "ตัดจากหลาย Lot ได้"
    stock_lots ||--o{ invoice_item_lots : "ต้นทุนจริงที่ถูกตัด"
    products ||--o{ invoice_items : "อะไหล่ที่ขาย"

    invoices {
        bigint id PK
        varchar doc_type "tax_invoice / warranty_claim"
        int doc_year
        int doc_number
        varchar invoice_type "repair / counter_sale"
        bigint job_id FK "null เมื่อขายหน้าร้าน"
        bigint customer_id FK
        varchar buyer_name "สำเนา ไม่ใช่ FK"
        varchar buyer_address "สำเนา"
        varchar buyer_tax_id "สำเนา"
        varchar tax_invoice_form "abbreviated / full"
        bigint promotion_id FK
        numeric discount_amount
        numeric subtotal_ex_vat
        numeric vat_amount
        numeric grand_total
        numeric gross_profit "คำนวณตอนออกบิล"
        varchar status "issued / cancelled"
        text cancel_reason
        bigint issued_by FK "ห้ามเป็น mechanic"
        timestamptz issued_at
    }

    invoice_items {
        bigint id PK
        bigint invoice_id FK
        varchar item_type "part / labor"
        bigint product_id FK "null เมื่อเป็นค่าแรง"
        varchar description
        int qty
        numeric unit_price "รวม VAT"
        numeric line_total
        date warranty_expires_on
    }

    invoice_item_lots {
        bigint id PK
        bigint invoice_item_id FK
        bigint lot_id FK
        int qty
        numeric unit_cost "ต้นทุนจริงของ Lot นั้น"
    }

    payments {
        bigint id PK
        bigint invoice_id FK
        numeric amount_received
        numeric withholding_amount "ลูกค้านิติบุคคลหักไว้"
        varchar method
        bigint received_by FK
        timestamptz received_at
    }

    document_sequences {
        varchar doc_type PK
        int doc_year PK
        int last_number
    }
```

**`(doc_type, doc_year, doc_number)` เป็น unique** งานเคลมอยู่คนละ `doc_type` จึงไม่กิน
เลขใบกำกับตามที่ตกลงไว้

**ข้อมูลผู้ซื้อสามคอลัมน์เป็นสำเนา ไม่ใช่ foreign key** ลูกค้าย้ายที่อยู่แล้วใบกำกับเก่าไม่เปลี่ยนตาม
ถ้าอ่านสดจาก `customers` เท่ากับแก้เอกสารภาษีย้อนหลัง

**`invoice_item_lots` คือตารางที่ทำให้ระบบนี้ต่างจากโปรแกรมขายทั่วไป** ถ้าไม่มีตารางนี้จะรู้แค่ว่า
ขายอะไรไป แต่ไม่รู้ว่าตัดมาจาก Lot ไหน แปลว่าคิดกำไรจริงไม่ได้และคืนของกลับ Lot เดิมไม่ได้

`payments` รับครั้งเดียวต่อบิล ระบบถือว่าครบเมื่อ `amount_received + withholding_amount = grand_total`
แล้วปิดใบงานอัตโนมัติ

---

## 7. โปรโมชั่น รับประกัน และรอบบำรุงรักษา

```mermaid
erDiagram
    invoices ||--o{ warranties : "ให้ประกัน"
    invoice_items ||--o| warranties : "ต่อรายการ"
    vehicles ||--o{ warranties : "ของรถคันนี้"
    vehicles ||--o{ maintenance_reminders : "ถึงกำหนดเช็คระยะ"
    products ||--o{ maintenance_reminders : "อะไหล่ที่ต้องเปลี่ยน"
    maintenance_reminders ||--o{ reminder_calls : "บันทึกทุกครั้งที่โทร"
    invoices ||--o{ maintenance_reminders : "สร้างจากบิลนี้"

    promotions {
        bigint id PK
        varchar name
        varchar scope "all / parts / labor"
        varchar discount_type "percent / amount"
        numeric value
        date start_date
        date end_date
        boolean is_active
    }

    warranties {
        bigint id PK
        bigint invoice_id FK
        bigint invoice_item_id FK
        bigint vehicle_id FK
        bigint product_id FK "null เมื่อเป็นค่าแรง"
        varchar warranty_type "labor / part"
        date expires_on
    }

    maintenance_reminders {
        bigint id PK
        bigint vehicle_id FK
        bigint product_id FK
        date due_date
        bigint source_invoice_id FK
        varchar status "pending / closed"
        timestamptz created_at
    }

    reminder_calls {
        bigint id PK
        bigint reminder_id FK
        varchar result "appointment / refused / no_answer"
        text note
        bigint called_by FK
        timestamptz called_at
    }

    settings {
        varchar key PK
        text value
        bigint updated_by FK
        timestamptz updated_at
    }
```

บิลเก็บ `promotion_id` ไว้อ้างอิงแต่ยอดส่วนลดจริงเก็บเป็นตัวเลขที่ `invoices.discount_amount`
แก้โปรโมชั่นทีหลังจึงไม่กระทบบิลเก่า

`warranties` สร้างตอนออกบิลงานซ่อม หน้ารับรถเข้าอู่อ่านตารางนี้ด้วย `vehicle_id` กับ
`expires_on >= today` บิลขายหน้าร้านไม่สร้างแถวที่นี่เพราะไม่มีรถผูก

หนึ่งคู่ (รถ, สินค้า) มีรายการเตือนที่ยัง `pending` ได้รายการเดียว ถ้าลูกค้ากลับมาเปลี่ยนตัวเดิม
ก่อนกำหนด รายการเดิมถูกปิดแล้วสร้างรอบใหม่แทน ไม่เตือนซ้อน

`reminder_calls` เก็บทุกครั้งที่โทร ไม่ทับของเดิม เพราะ KPI นับจำนวนครั้งที่โทรด้วย

`settings` เก็บข้อมูลอู่สำหรับหัวบิล จำนวนวันรับประกันค่าแรงเริ่มต้น และจำนวนวันที่นับว่าของค้างคลัง
(ค่าเริ่มต้น 90)

---

## กฎที่ต้องบังคับในฐานข้อมูล ไม่ใช่ในโค้ดอย่างเดียว

**หนึ่งคันหนึ่งใบงานค้าง**

```sql
create unique index job_orders_one_active_per_vehicle
  on job_orders (vehicle_id)
  where status not in ('closed', 'cancelled');
```

**เลขที่เอกสารห้ามข้าม — ห้ามใช้ SEQUENCE ของ PostgreSQL**

`nextval()` ไม่ย้อนกลับเมื่อทรานแซกชัน rollback เลขจะหายไปหนึ่งใบทันทีที่บันทึกไม่สำเร็จ ซึ่งคือ
สิ่งที่ระบบพยายามกันไว้ตั้งแต่ต้น ต้องออกเลขด้วยการ lock แถวใน `document_sequences`
ในทรานแซกชันเดียวกับการ insert บิล

```sql
update document_sequences
   set last_number = last_number + 1
 where doc_type = $1 and doc_year = $2
returning last_number;
```

**การตัดสต็อก FIFO**

```sql
select * from stock_lots
 where product_id = $1 and qty_remaining > 0
 order by received_at, id
   for update;
```

แล้วไล่หัก `qty_remaining` พร้อมเขียน `stock_movements` ในทรานแซกชันเดียวกัน การ lock ตามลำดับ
เดียวกันเสมอกัน deadlock เมื่อสองใบงานตัดสินค้าตัวเดียวกันพร้อมกัน

**qty_remaining ห้ามติดลบ** — `check (qty_remaining >= 0 and qty_remaining <= qty_received)`

**ช่างหลักได้คนเดียวต่อใบงาน**

```sql
create unique index job_order_one_primary_mechanic
  on job_order_mechanics (job_id)
  where is_primary;
```

**ช่างห้ามอนุมัติใบเสนอราคาและห้ามออกบิล** — บังคับที่ชั้นแอปพลิเคชัน และย้ำด้วย constraint
ที่ตรวจว่า `approved_by` และ `issued_by` ต้องไม่ใช่ผู้ใช้ที่ `role = 'mechanic'`

**ยกเลิกใบงานได้เฉพาะตอนยังไม่แตะของ** — ตรวจว่าไม่มี `stock_movements` แบบ issue ที่อ้าง
ใบงานนั้น ถ้ามีต้องไปทางออกบิลแทน

---

## จุดที่ควรระวังตอน implement

- **กำไรคำนวณตอนออกบิล** จากยอดขายก่อน VAT หลังหักส่วนลด ลบผลรวม `invoice_item_lots.qty * unit_cost`
  ทั้งสองฝั่งเป็นฐานก่อน VAT ถ้าเผลอเอา `grand_total` มาลบต้นทุน กำไรจะเกินจริง 7% ทุกใบ
- **ราคาบนหน้าจอรวม VAT แต่ในบิลต้องแยก** `subtotal_ex_vat = round(ยอดรวม / 1.07, 2)` แล้ว
  `vat_amount = grand_total - subtotal_ex_vat` เพื่อให้ผลรวมกลับมาเท่าเดิมเสมอ ไม่ปัดเศษสองรอบแยกกัน
- **ยกเลิกบิล** ต้องคืนของตาม `invoice_item_lots` กลับเข้า Lot เดิม เขียน `stock_movements` แบบ return
  และล้าง `gross_profit` แต่ห้ามลบแถวบิลและห้ามคืนเลขที่เอกสาร
- **รับของแล้วตัดให้ใบงานที่รออยู่** ทำในทรานแซกชันเดียวกับการรับของ เรียงตามเวลาที่ใบเสนอราคา
  ได้รับอนุมัติ ตัดครบแล้วเซ็ต `waiting_parts = false`
