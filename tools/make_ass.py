#!/usr/bin/env python3
"""สร้างไฟล์ซับ .ass สไตล์คลิปสั้น จากไฟล์ cue แบบอ่านง่าย

รูปแบบไฟล์ cue (บรรทัดละคิว, บรรทัดที่ขึ้นต้นด้วย # คือคอมเมนต์):

    0.0-2.8 | ใครหาหูฟังงบ *ไม่ถึงห้าร้อย*
    2.8-6.4 | เสียงเบสแน่นเกินราคาไปมาก

ข้อความใน *ดอกจัน* จะถูกเน้นสีต่างจากตัวอื่น

หมายเหตุเรื่องภาษาไทย: ภาษาไทยไม่เว้นวรรคระหว่างคำ การตัดคำทีละคำแบบ
ซับ TikTok ภาษาอังกฤษจึงเชื่อถือไม่ได้ถ้าไม่มีตัวตัดคำ สคริปต์นี้เลย
แสดงทีละวลีตามที่เขียนในไฟล์ cue แล้วใส่จังหวะ "เด้ง" ตอนขึ้นแทน
ซึ่งอ่านง่ายกว่าบนจอมือถือและคุมเองได้ทั้งหมด
"""
import argparse
import re
from pathlib import Path

CUE_RE = re.compile(r"^\s*([\d.]+)\s*-\s*([\d.]+)\s*\|\s*(.+?)\s*$")


def ts(seconds):
    """วินาที -> H:MM:SS.cc ตามรูปแบบของ ASS"""
    cs = round(seconds * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def parse_cues(path):
    cues = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = CUE_RE.match(line)
        if not m:
            raise SystemExit(f"{path}:{n}: รูปแบบไม่ถูกต้อง -> {line!r}")
        start, end, text = float(m.group(1)), float(m.group(2)), m.group(3)
        if end <= start:
            raise SystemExit(f"{path}:{n}: เวลาจบต้องมากกว่าเวลาเริ่ม")
        cues.append((start, end, text))
    if not cues:
        raise SystemExit(f"{path}: ไม่พบคิวซับเลย")
    return cues


def render_text(text, highlight):
    """แปลง *เน้น* เป็น ASS color tag แล้วใส่แอนิเมชันเด้งตอนขึ้น"""
    parts = text.split("*")
    out = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2:  # อยู่ระหว่างดอกจัน
            out.append(f"{{\\c&H{highlight}&}}{part}{{\\c&HFFFFFF&}}")
        else:
            out.append(part)
    body = "".join(out).replace("\n", "\\N")
    pop = "{\\fscx88\\fscy88\\t(0,130,\\fscx100\\fscy100)}"
    return pop + body


def build(cues, font, size, highlight, margin_v, width, height):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},&H00FFFFFF,&H00000000,&H80000000,-1,1,{max(3, size // 14)},2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [
        f"Dialogue: 0,{ts(s)},{ts(e)},Main,,0,0,0,,{render_text(t, highlight)}"
        for s, e, t in cues
    ]
    return header + "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cues", help="ไฟล์ cue (.txt)")
    ap.add_argument("-o", "--out", required=True, help="ไฟล์ .ass ที่จะเขียน")
    ap.add_argument("--font", default="Noto Sans Thai", help="ชื่อฟอนต์ (ต้องมีใน assets/fonts)")
    ap.add_argument("--size", type=int, default=96, help="ขนาดตัวอักษร")
    ap.add_argument("--highlight", default="00E5FF", help="สีคำที่เน้น เป็น BBGGRR แบบ ASS (ค่าตั้งต้น = เหลืองทอง)")
    ap.add_argument("--margin-v", type=int, default=420, help="ระยะจากขอบล่าง (พิกเซล)")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    args = ap.parse_args()

    cues = parse_cues(args.cues)
    ass = build(cues, args.font, args.size, args.highlight, args.margin_v, args.width, args.height)
    Path(args.out).write_text(ass, encoding="utf-8")
    print(f"เขียน {args.out} แล้ว ({len(cues)} คิว, จบที่ {cues[-1][1]:.1f} วิ)")


if __name__ == "__main__":
    main()
