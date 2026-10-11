---
title: solo-habits — Product Card
doc_id: CARD-solo-habits
doc_type: product-card
verdict: invest
version: 0.1
date: 2026-10-11
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# solo-habits — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

ติดตามนิสัยและกิจวัตรรายวันโดยให้ service เป็นเจ้าของการคำนวณ streak เพื่อให้ตัวเลขตรงเสมอไม่ว่าใครเขียน log

## 2. ปัญหาและผู้ใช้เป้าหมาย

streak ที่คำนวณฝั่ง client เพี้ยนได้และตรวจสอบไม่ได้ ผู้ใช้คือเจ้าของ

## 3. สิ่งที่ทำได้จริงตอนนี้

- API `habits-api` เขียน habit/log และคำนวณ `current_streak` ใหม่ทุกครั้งที่ log เปลี่ยน (ตาม README)
- `habits-publisher` (outbox cron ทุก 15 นาที) และ `habits-autogrant` (cron รายสัปดาห์)
- เทสต์ API, autogrant และ e2e กับ platform
- ทุกการเขียนผ่านลำดับ precheck → เปลี่ยนข้อมูลในเครื่อง → execution บน empire-platform → commit → finish พร้อม row hash และ RLS แบบบังคับต่อ workspace (ตาม README)

## 4. หลักฐานสถานะ

| รายการ | ค่า |
|---|---|
| Stack | Python, FastAPI, PostgreSQL (Neon) |
| Commit | 5 ครั้ง (2026-10-10 ถึง 2026-10-11) |
| ซอร์สโค้ด | 12 ไฟล์ / 2191 บรรทัด |
| เทสต์ | 4 ไฟล์ (ไม่ได้รันในงานนี้) |
| CI | ไม่มี workflow |
| Deploy config | Railway (Serverless) + Neon; ทะเบียน `online-systems.yaml` ระบุสถานะ online (ไม่ได้ probe สดในงานนี้) |
| Live URL | ดูทะเบียน `online-systems.yaml` (ไม่ได้ probe สด) |

## 5. คุณค่าและจุดต่าง

- เป็นส่วนหนึ่งของสถาปัตยกรรม decentralize ที่ 1 domain = 1 cell จึงเปลี่ยนหรือขายแยกได้
- ใช้สิทธิ์/audit กลางร่วมกันโดยไม่ต้องเขียนใหม่ต่อ cell
- **[สมมติฐาน]** มูลค่าเชิงรายได้ยังไม่พิสูจน์ — ใช้เป็นระบบของเจ้าของก่อน

## 6. ช่องว่างสำคัญ

- พึ่ง empire-platform ตัวเดียว: ถ้า platform ล่ม cell เขียนไม่ได้ (fail closed)
- ไม่มี UI ใน repo นี้

## 7. คำตัดสิน

**`invest`** — เป็นแกนข้อมูลของ domain ที่ระบบ Solo Empire ใช้จริงและตาม cell contract เดียวกัน จะเปลี่ยนเป็น `showcase` หากเจ้าของยุบ domain นี้หรือย้ายไปรวมกับ cell อื่น

## 8. ขั้นต่อไป

1. เพิ่มหน้าจอ/การแจ้งเตือนเพื่อให้เกิดการใช้จริงทุกวัน

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `cell.yaml`
- `tests/`
