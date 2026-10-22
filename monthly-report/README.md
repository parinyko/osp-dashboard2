# OSP Monthly Report

รายงานประจำเดือน Team Performance แยกทุกบริษัท (DMP · Origin · Ex-Press · 3BB · NY CABLE …) จากไฟล์
`Data Job done <ปี>.xlsx` ไฟล์เดียว · หน้าเว็บ React (Vite) + API FastAPI รวมใน Docker image เดียว

แอปนี้แยกจากแดชบอร์ด (`app.py` ที่ root ของ repo) — รันเป็นอีก service หนึ่ง

## รันบน Render

1. **New → Web Service** → เลือก repo นี้
2. **Root Directory**: `monthly-report`
3. **Runtime / Language**: **Docker** (ใช้ `Dockerfile` ในโฟลเดอร์นี้ ไม่ต้องใส่ Build / Start Command)
4. **Environment** (ดู `.env.example`):

   | Key | Value |
   |---|---|
   | `OSP_SECRET` | ข้อความสุ่มยาวๆ (ใช้เซ็น cookie) |
   | `OSP_ADMIN_PASSWORD` | รหัสสำหรับอัปโหลด Excel / ตั้งเป้า · เว้นว่าง = ใครก็อัปโหลดได้ |
   | `OSP_VIEW_PASSWORD` | รหัสสำหรับดูรายงาน · เว้นว่าง = ดูได้ไม่ต้องใส่รหัส |
   | `PORT` | ไม่ต้องใส่ — Render ตั้งให้เอง |

5. Deploy → เปิดเว็บ → กด **Upload Excel** แล้วเลือกไฟล์ `Data Job done 2026.xlsx`

ข้อควรรู้บน Render: ดิสก์ไม่เก็บไฟล์ข้ามการ deploy (ไฟล์ Excel ที่อัปโหลดและเป้าที่ตั้งจะหาย) ถ้าจะใช้จริง
ผูก **Persistent Disk** ที่ `/data` (โค้ดเก็บข้อมูลไว้ที่ `OSP_STORAGE=/data` อยู่แล้ว)

## รันบนเครื่อง

```bash
cd monthly-report
npm install
python3 -m venv server/.venv && server/.venv/bin/pip install -r server/requirements.txt
npm run dev:all          # เว็บ http://localhost:5190 + API :8795 (ไม่มี login ตอน dev)
npm test                 # pytest ของ backend
```

## ตัวเลือกเพิ่มเติม

- `OSP_BASE_PATH` (build arg) — เสิร์ฟใต้ path ย่อย เช่น `/monthly` เมื่อใช้โดเมนเดียวกับแดชบอร์ด
  (มีแถบเมนูกลับไปหน้าแดชบอร์ดให้อัตโนมัติ) · เว้นว่าง = เสิร์ฟที่ `/`
- `OSP_AUTH_DB` — path ไฟล์ SQLite ผู้ใช้ของแดชบอร์ด (`AUTH_DB`) ถ้าอยากให้ล็อกอินร่วมกับแดชบอร์ด
  ต้องอยู่เครื่องเดียวกันและโดเมนเดียวกัน · บน Render ที่แยก service ไม่ต้องตั้ง
- ไฟล์ข้อมูลงาน (`*.xlsx`) ห้าม commit — เป็นข้อมูลภายใน อัปโหลดผ่านหน้าเว็บเท่านั้น

## หมายเหตุ

โค้ดชุดนี้คัดลอกมาจากต้นฉบับที่ใช้รันที่ osp-dashboard.workproth.com/monthly (ณ 2026-10-22) —
แก้ในโฟลเดอร์นี้ไม่ได้ขึ้นเว็บนั้นอัตโนมัติ
