# โครงสร้างฐานข้อมูล

PostgreSQL — 22 ตาราง อ้างอิง `new_scenario_summary.md` และ `screens.md`

เงินทุกคอลัมน์เป็น `numeric(12,2)` วันเวลาเป็น `timestamptz` `id` ของทุกตารางเป็น `bigserial`

---

## ภาพรวม

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

    vehicles ||--o{ maintenance_reminders : "ถึงกำหนดเช็คระยะ"
```

- รถหนึ่งคันมีใบงานได้หลายใบตลอดประวัติ แต่ที่ค้างอยู่ได้ใบเดียว บังคับด้วย partial unique index
- ใบงานหนึ่งใบออกบิลได้ไม่เกินหนึ่งใบ บิลขายหน้าร้าน `job_id` เป็น null
- หนึ่งรายการขายกินได้หลาย Lot จึงต้องมี `invoice_item_lots` คั่นกลาง

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

`role` บังคับด้วย `CheckConstraint` ที่ฐานข้อมูล ทุกตารางที่บันทึกการกระทำอ้าง `users.id` ผ่านคอลัมน์ `*_by`

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

ลูกค้าขาจรที่ซื้อของหน้าร้านไม่ถูกบันทึกที่นี่ ข้อมูลผู้ซื้อไปอยู่บนบิลโดยตรง

---

## 3. สินค้าและคลัง

```mermaid
erDiagram
    products ||--o{ stock_lots : "รับเข้าเป็นรอบ"
    stock_lots ||--o{ stock_movements : "ทุกการเคลื่อนไหว"
    goods_receipts ||--o{ stock_lots : "หนึ่งใบรับ หลาย Lot"

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
        bigint receipt_id FK
        timestamptz received_at "ใช้เรียงคิว FIFO"
        numeric unit_cost "ก่อน VAT"
        numeric vat_amount "ต่อชิ้น 0 เมื่อไม่มีใบกำกับ"
        int qty_received
        int qty_remaining
    }

    stock_movements {
        bigint id PK
        bigint product_id FK
        bigint lot_id FK
        int qty "บวกคือเข้า ลบคือออก"
        varchar movement_type "receive / issue / return / adjust"
        varchar ref_type "job_order / invoice / goods_receipt / adjustment"
        bigint ref_id
        text reason "บังคับเมื่อ adjust"
        bigint created_by FK
        timestamptz created_at
    }
```

- หนึ่งสินค้าที่รับเข้ามาหนึ่งครั้ง = หนึ่ง Lot เสมอ ไม่ว่าจะมาทางใบสั่งซื้อหรือซื้อด่วน
- FIFO เรียงตาม `received_at` แล้ว `id`
- `qty_remaining` เก็บเป็นตัวเลขจริง ไม่คำนวณสดจาก movements
- การคืนของอ้าง `lot_id` เดิมเสมอ ไม่สร้าง Lot ใหม่
- **สต็อกตัดตอนใบเสนอราคาได้รับอนุมัติ ไม่ใช่ตอนออกบิล** การตัดครั้งนั้นเขียน `stock_movements` ที่
  `ref_type = 'job_order'` และ `ref_id` เป็นเลขใบงาน ตารางนี้จึงเป็นที่เดียวที่รู้ว่าใบงานกินไปกี่ชิ้นจาก Lot ไหน
  ทั้งหน้าจอรายละเอียดใบงานและการสร้าง `invoice_item_lots` ตอนออกบิลอ่านจากที่นี่

---

## 4. จัดซื้อ

```mermaid
erDiagram
    suppliers ||--o{ purchase_orders : "สั่งซื้อจาก"
    suppliers ||--o{ goods_receipts : "รับของจาก"
    purchase_orders ||--o{ purchase_order_items : "มีรายการ"
    purchase_orders ||--o{ goods_receipts : "รับได้หลายครั้ง"
    goods_receipts ||--o{ stock_lots : "แต่ละรายการเป็นหนึ่ง Lot"
    products ||--o{ purchase_order_items : "สั่ง"

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
        int qty_received
        numeric unit_price "ราคาที่ตกลงกับร้าน ก่อน VAT"
    }

    goods_receipts {
        bigint id PK
        varchar receipt_number UK
        bigint supplier_id FK
        bigint po_id FK "null เมื่อซื้อด่วน"
        varchar receipt_type "po / urgent"
        varchar supplier_invoice_no "ไม่บังคับ"
        date supplier_invoice_date "ไม่บังคับ"
        bigint created_by FK
        timestamptz created_at
    }
```

- `receipt_type = urgent` คือซื้อด่วนหน้างาน `po_id` เป็น null
- ไม่มีใบกำกับของร้าน = ไม่เข้ารายงานภาษีซื้อ และ `unit_cost` คือราคาที่จ่ายทั้งจำนวนโดยไม่แยก VAT
- รับของไม่ครบตามใบสั่งซื้อได้

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
        bigint customer_id FK "สำเนาเจ้าของ ณ วันรับรถ"
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

- `waiting_parts` เป็นคอลัมน์แยกจาก `status` เพราะช่างทำงานส่วนอื่นต่อได้ระหว่างรออะไหล่
- `status` เดินหน้าทางเดียว `pending → in_progress → done → closed` ส่วน `cancelled` แยกออกมา
- ใบเสนอราคาเก็บทุกเวอร์ชัน ใบเก่าเป็น `superseded` แถวที่ `approved` แก้ไม่ได้ บังคับด้วย trigger
- อนุมัติเวอร์ชันใหม่แล้วตัดหรือคืนเฉพาะส่วนต่างจากเวอร์ชันก่อนหน้า

---

## 6. บิลและการรับเงิน

```mermaid
erDiagram
    job_orders ||--o| invoices : "ออกบิลเมื่อจบงาน"
    customers ||--o{ invoices : "ลูกค้า"
    promotions ||--o{ invoices : "ส่วนลดที่ใช้"
    invoices ||--o{ invoice_items : "มีรายการ"
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
        bigint customer_id FK "null เมื่อลูกค้าขาจร"
        varchar buyer_name "สำเนา ไม่ใช่ FK"
        varchar buyer_address "สำเนา"
        varchar buyer_tax_id "สำเนา"
        varchar tax_invoice_form "abbreviated / full"
        bigint promotion_id FK
        numeric discount_amount "รวม VAT เหมือนราคาที่คุยกับลูกค้า"
        numeric subtotal_ex_vat
        numeric vat_amount
        numeric grand_total
        numeric gross_profit "คำนวณตอนออกบิล"
        varchar status "issued / cancelled"
        text cancel_reason
        bigint issued_by FK "ห้ามเป็น mechanic"
        timestamptz issued_at
        numeric amount_received
        numeric withholding_amount "ลูกค้านิติบุคคลหักไว้"
        varchar payment_method
        bigint received_by FK "ห้ามเป็น mechanic"
        timestamptz received_at "null คือยังไม่ได้รับเงิน"
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

    document_sequences {
        varchar doc_type PK
        int doc_year PK
        int last_number
    }
```

- `(doc_type, doc_year, doc_number)` เป็น unique งานเคลมอยู่คนละ `doc_type` จึงไม่กินเลขใบกำกับ
- ข้อมูลผู้ซื้อสามคอลัมน์เป็นสำเนา ไม่ใช่ foreign key ลูกค้าย้ายที่อยู่แล้วใบกำกับเก่าไม่เปลี่ยนตาม
- รับเงินครบทีเดียว ระบบถือว่าครบเมื่อ `amount_received + withholding_amount = grand_total` แล้วปิดใบงานอัตโนมัติ
- บิลที่ `grand_total = 0` เช่นเอกสารส่งมอบงานเคลม ปิดใบงานตั้งแต่ตอนออกเอกสาร ไม่ต้องกดรับเงิน
- `received_at is null` คือเงื่อนไข "ยังไม่ได้รับเงิน" ใช้ตรวจตอนยกเลิกบิล คู่กับเงื่อนไขบิลของวันนี้
- ค่าแรงเป็นแถวเดียวต่อบิล `item_type = labor` และ `product_id` เป็น null บิลขายหน้าร้านมีแถว labor ไม่ได้
- **ออกบิลกับรับเงินเป็นสองจังหวะ** ตอนออกบิลจองเลขที่ คัดลอกข้อมูลผู้ซื้อ คำนวณ `gross_profit`
  วันหมดประกัน และสร้างรายการเตือนรอบบำรุงรักษา แถวนั้น `received_at` ยังเป็น null
  ตอนรับเงินครบค่อยเซ็ต `amount_received` `received_by` `received_at` แล้วปิดใบงาน
- `invoice_item_lots` ของบิลงานซ่อมไม่ตัดสต็อกใหม่ สร้างจาก `stock_movements` ของใบงานที่ตัดไปแล้ว
  ส่วนบิลขายหน้าร้านตัด FIFO ตอนออกบิลเลยเพราะไม่มีใบงานมาก่อน
- รายงานภาษีขายกรอง `doc_type = 'tax_invoice'` เท่านั้น `warranty_claim` ไม่เข้ารายงาน

---

## 7. โปรโมชั่น รับประกัน และรอบบำรุงรักษา

```mermaid
erDiagram
    vehicles ||--o{ maintenance_reminders : "ถึงกำหนดเช็คระยะ"
    products ||--o{ maintenance_reminders : "อะไหล่ที่ต้องเปลี่ยน"
    invoices ||--o{ maintenance_reminders : "สร้างจากบิลนี้"
    users ||--o{ maintenance_reminders : "คนที่โทรล่าสุด"

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

    maintenance_reminders {
        bigint id PK
        bigint vehicle_id FK
        bigint product_id FK
        date due_date
        bigint source_invoice_id FK
        varchar status "pending / closed"
        varchar last_call_result "appointment / refused / no_answer"
        timestamptz last_called_at "null คือยังไม่เคยโทร"
        bigint last_called_by FK
        text note
        timestamptz created_at
    }

    settings {
        varchar key PK
        text value
        bigint updated_by FK
        timestamptz updated_at
    }
```

- บิลเก็บ `promotion_id` ไว้อ้างอิง แต่ยอดส่วนลดจริงเก็บเป็นตัวเลขที่ `invoices.discount_amount`
- วันหมดประกันเก็บที่ `invoice_items.warranty_expires_on` ค่าแรงใช้จำนวนวันจากหน้าตั้งค่า อะไหล่ใช้ `products.warranty_days`
- หนึ่งคู่ (รถ, สินค้า) มีรายการเตือนที่ยัง `pending` ได้รายการเดียว เปลี่ยนก่อนกำหนดให้ปิดรายการเดิมแล้วสร้างใหม่
- `settings` เก็บข้อมูลอู่สำหรับหัวบิล รูปแบบเลขที่เอกสาร จำนวนวันรับประกันค่าแรง และจำนวนวันที่นับว่าของค้างคลัง

**ตรวจว่ารถคันนี้ยังอยู่ในประกันอะไรบ้าง**

```sql
select ii.description, ii.warranty_expires_on
  from invoice_items ii
  join invoices i   on i.id = ii.invoice_id
  join job_orders j on j.id = i.job_id
 where j.vehicle_id = $1
   and i.status = 'issued'
   and ii.warranty_expires_on >= current_date;
```

ต้องมี index ที่ `job_orders (vehicle_id)` และ `invoice_items (warranty_expires_on)`

---

## กฎที่ต้องบังคับในฐานข้อมูล

**หนึ่งคันหนึ่งใบงานค้าง**

```sql
create unique index job_orders_one_active_per_vehicle
  on job_orders (vehicle_id)
  where status not in ('closed', 'cancelled');
```

**ช่างหลักได้คนเดียวต่อใบงาน**

```sql
create unique index job_order_one_primary_mechanic
  on job_order_mechanics (job_id)
  where is_primary;
```

**หนึ่งใบงานออกบิลได้ใบเดียว**

```sql
create unique index invoices_one_per_job
  on invoices (job_id)
  where job_id is not null and status <> 'cancelled';
```

ยกเว้นบิลที่ยกเลิกไว้ ไม่งั้นออกบิลใหม่แทนใบที่ยกเลิกไม่ได้

**เลขที่เอกสารห้ามข้าม — ห้ามใช้ SEQUENCE ของ PostgreSQL**

`nextval()` ไม่ย้อนกลับเมื่อ rollback เลขจะหายทันทีที่บันทึกไม่สำเร็จ ต้อง lock แถวใน
`document_sequences` ในทรานแซกชันเดียวกับการ insert บิล

```sql
insert into document_sequences (doc_type, doc_year, last_number)
     values ($1, $2, 1)
on conflict (doc_type, doc_year)
  do update set last_number = document_sequences.last_number + 1
  returning last_number;
```

ต้องเป็น upsert เพราะแถวของปีใหม่ยังไม่มี ถ้าใช้ `update` เปล่า บิลใบแรกของทุกปีจะได้ 0 แถวกลับมา

**เลขที่เอกสารอื่นใช้ตารางเดียวกัน** `job_number` `po_number` `receipt_number` ออกจาก `document_sequences`
ด้วย `doc_type` เป็น `job` `po` `receipt` สามชุดนี้ข้ามเลขได้ไม่เป็นไร ไม่ต้องถือ lock ยาวเหมือนใบกำกับ
รูปแบบของทั้งสามต้องมีปีอยู่ในตัวเลขด้วย เพราะ `last_number` รีเซ็ตทุกปี ถ้าไม่มีปี เลขจะชนของเดิมในปีถัดไป

**ตัดสต็อกแบบ FIFO**

```sql
select * from stock_lots
 where product_id = $1 and qty_remaining > 0
 order by received_at, id
   for update;
```

ไล่หัก `qty_remaining` พร้อมเขียน `stock_movements` ในทรานแซกชันเดียวกัน การ lock ตามลำดับเดียวกัน
เสมอกัน deadlock เมื่อสองใบงานตัดสินค้าตัวเดียวกันพร้อมกัน

**qty_remaining ห้ามติดลบ**

```sql
check (qty_remaining >= 0 and qty_remaining <= qty_received)
```

**ช่างห้ามอนุมัติใบเสนอราคาและห้ามออกบิล** บังคับที่ชั้นแอปพลิเคชัน และตรวจว่า `approved_by`,
`issued_by`, `received_by` ต้องไม่ใช่ผู้ใช้ที่ `role = 'mechanic'`

**ยกเลิกใบงานได้เฉพาะตอนยังไม่แตะของ** ตรวจว่าไม่มี `stock_movements` แบบ issue ที่อ้างใบงานนั้น

---

## จุดที่ควรระวังตอน implement

- **กำไรคำนวณตอนออกบิล** จากยอดขายก่อน VAT หลังหักส่วนลด ลบผลรวม `invoice_item_lots.qty * unit_cost`
  ทั้งสองฝั่งเป็นฐานก่อน VAT ถ้าเอา `grand_total` มาลบต้นทุน กำไรจะเกินจริง 7% ทุกใบ
- **ราคาบนหน้าจอรวม VAT แต่ในบิลต้องแยก** `subtotal_ex_vat = round(ยอดรวม / 1.07, 2)` แล้ว
  `vat_amount = grand_total - subtotal_ex_vat` ไม่ปัดเศษสองรอบแยกกัน
- **ยกเลิกบิล** ทำได้เมื่อ `received_at is null` หรือ `issued_at::date = current_date` เงื่อนไขหลังมีไว้ให้
  บิลขายหน้าร้านที่รับเงินไปพร้อมกันในขั้นตอนเดียว คืนเงินสดจากลิ้นชักแล้วกดยกเลิก ข้ามวันไปแล้วยกเลิกไม่ได้
  คืนของตาม `invoice_item_lots` กลับเข้า Lot เดิม เขียน `stock_movements` แบบ return ล้าง `gross_profit`
  ปิดรายการเตือนที่ `source_invoice_id` เป็นบิลใบนั้น แต่ห้ามลบแถวบิลและห้ามคืนเลขที่เอกสาร
- **รับของแล้วตัดให้ใบงานที่รออยู่** ทำในทรานแซกชันเดียวกับการรับของ เรียงตามเวลาที่ใบเสนอราคา
  ได้รับอนุมัติ ตัดครบแล้วเซ็ต `waiting_parts = false`
