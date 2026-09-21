# Prompt สำหรับ Google Flow (Veo) — ช็อตคนพูด

ใช้กับช็อต HOOK และ CTA เท่านั้น **ห้ามให้ Veo วาดตัวสินค้า** — ฉลากกับโลโก้จะเพี้ยน
ตัวสินค้าใช้รูปถ่ายจริงเสมอ แล้วให้ `tools/build.py` ใส่การเคลื่อนไหวให้

## ขั้นตอนใน Flow

1. เปิด Flow เลือกโหมดที่รับรูปอ้างอิงได้ (Ingredients to Video / Frames to Video)
2. อัปรูปหน้าตรงของคุณ 1-3 รูป แสงสม่ำเสมอ พื้นหลังไม่รก
3. วาง prompt ด้านล่าง แก้ส่วนใน `[ ]`
4. render 2 ช็อต: ช็อต HOOK (~4 วิ) และช็อต CTA (~6 วิ) แยกกัน
5. โหลดมาวางที่ `projects/<งาน>/raw/01-hook.mp4` และ `02-cta.mp4`

## แม่แบบ — ช็อต HOOK

```
A [ชาย/หญิง] Thai person in their [อายุ]s, matching the reference photo,
speaking directly to camera in a [bright modern bedroom / tidy home office]
with soft natural window light. Handheld vertical phone video, 9:16,
shot slightly above eye level, shallow depth of field, casual UGC style,
authentic and unpolished.

The person looks genuinely surprised and pleased, leaning slightly toward
the camera at the start.

Dialogue (Thai, natural conversational pace, warm and sincere):
"[ประโยค hook ของคุณ]"

No on-screen text. No captions. No logos. No product in frame.
```

## แม่แบบ — ช็อต CTA

```
Same person, same room, same lighting and outfit as the previous shot,
continuing to speak to camera. Handheld vertical 9:16 UGC video.

The person smiles, nods once, and gestures downward toward the bottom
of the frame at the end of the line.

Dialogue (Thai, upbeat but not shouty):
"[ประโยค CTA ของคุณ]"

No on-screen text. No captions. No logos. No product in frame.
```

## ข้อควรรู้

- **ความต่อเนื่อง**: เขียน "same outfit, same room, same lighting" ในช็อต CTA เสมอ
  ไม่งั้นเสื้อผ้าหรือทรงผมจะเปลี่ยนกลางคลิป คนดูจับได้ทันที
- **สั่งห้ามข้อความ**: ถ้าไม่สั่ง `No on-screen text` Veo ชอบแปะตัวหนังสือมั่ว ๆ
  ที่อ่านไม่ออก ซึ่งจะชนกับซับที่เราใส่เอง
- **ความยาว**: render เผื่อยาวกว่าที่ต้องใช้ 1-2 วิ แล้วค่อยตัดใน `shots.yaml`
  ด้วยค่า `start` กับ `duration` จะได้เลือกจังหวะที่ดีที่สุด
- **ปากไม่ตรงเสียง**: ถ้า lip-sync ภาษาไทยเพี้ยน ให้ลองเขียนบทสั้นลง
  ประโยคยาวเกิน 12-13 คำมักเริ่มหลุด
- **ทำหลายเทค**: render ช็อตละ 3-4 ครั้งแล้วเลือก ถูกกว่าการพยายามแก้ prompt
  ให้สมบูรณ์แบบตั้งแต่ครั้งแรก
