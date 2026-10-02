#!/usr/bin/env python3
"""ตัดคลิปรวม moment จากโฟลเดอร์วีดีโอ ให้พอดีกับท่อนเพลง

ทำ 2 รอบ:

1) scan — ทำภาพรวมเฟรม (contact sheet) ของทุกคลิปในโฟลเดอร์

    python3 tools/moments.py scan ~/Downloads/LEON --project projects/LEON_2_OCT

   ได้รูป sheets/V01.jpg, V02.jpg, ... แต่ละช่องมีเลขคลิปกับวินาทีกำกับ
   ส่งรูปพวกนี้ให้ Claude (หรือดูเอง) เพื่อเลือกช่วงที่จะใช้

2) cut — อ่าน plan.txt แล้วตัดต่อเป็นคลิปแนวตั้งใส่เพลง

    python3 tools/moments.py cut --project projects/LEON_2_OCT \\
        --music ~/Downloads/ยิ้มอันตราย.mp3 --music-start 45

   plan.txt บรรทัดละช็อต: <เลขคลิป> <เริ่มวินาที> <ยาวกี่วินาที>

       V03  12.0  2.5   # หัวเราะ
       V07   4.0  3.0

   ความยาวรวมต้องเท่ากับ --length (ค่าเริ่มต้น 22 วินาที)
   ได้ไฟล์ out/final.mp4 แล้วลากเข้า CapCut ต่อได้เลย
"""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import ffmpeg_env  # noqa: E402
from build import esc  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".webm"}
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
PLAN_RE = re.compile(r"^\s*(V\d+)\s+([\d.]+)\s+([\d.]+)\s*(?:#.*)?$", re.I)

CELL = 320        # ขนาดช่องสี่เหลี่ยมใน contact sheet
COLS = 6
MAX_CELLS = 36    # คลิปยาวกว่านี้จะเว้นช่วงห่างขึ้น


def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-3000:])
        raise SystemExit("ffmpeg ล้มเหลว")


def label_ass(path, labels, cols, w, h):
    """ไฟล์ .ass ที่วางป้ายเวลาไว้มุมซ้ายบนของแต่ละช่อง"""
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        "Style: L,IBM Plex Sans Thai,26,&H00FFFFFF,&H00000000,&H80000000,1,3,2,0,7,0,0,0",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Text",
    ]
    for i, text in enumerate(labels):
        x, y = (i % cols) * CELL + 6, (i // cols) * CELL + 4
        lines.append(f"Dialogue: 0,0:00:00.00,9:00:00.00,L,{{\\pos({x},{y})}}{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan(args):
    folder = args.folder.expanduser().resolve()
    project = args.project.resolve()
    sheets = project / "sheets"
    sheets.mkdir(parents=True, exist_ok=True)

    videos = sorted(p for p in folder.rglob("*")
                    if p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."))
    if not videos:
        raise SystemExit(f"ไม่พบไฟล์วีดีโอใน {folder}")

    ff = ffmpeg_env.ffmpeg()
    clips = {}
    for n, src in enumerate(videos, 1):
        cid = f"V{n:02d}"
        dur = ffmpeg_env.duration(src)
        # เฟรมละ 1 วิ ถ้าคลิปยาวก็ห่างขึ้นให้ไม่เกิน MAX_CELLS ช่อง
        step = max(1.0, math.ceil(dur / MAX_CELLS * 2) / 2)
        count = max(1, min(MAX_CELLS, int(dur // step) + (1 if dur % step > 0.3 else 0)))
        cols = min(COLS, count)
        rows = math.ceil(count / cols)
        labels = [f"{cid} {i * step:.1f}s" for i in range(count)]
        ass = sheets / f"{cid}.ass"
        label_ass(ass, labels, cols, cols * CELL, rows * CELL)

        vf = (f"fps=1/{step},"
              f"scale={CELL}:{CELL}:force_original_aspect_ratio=decrease,"
              f"pad={CELL}:{CELL}:(ow-iw)/2:(oh-ih)/2,"
              f"tile={cols}x{rows},"
              f"ass=filename='{esc(ass)}':fontsdir='{esc(FONTS)}'")
        out = sheets / f"{cid}.jpg"
        run([ff, "-y", "-v", "error", "-i", str(src), "-vf", vf,
             "-frames:v", "1", "-q:v", "4", str(out)])
        ass.unlink()

        clips[cid] = {"src": str(src), "duration": round(dur, 2)}
        print(f"{cid}  {dur:6.1f}s  ห่างช่องละ {step:g}s  {src.name}")

    (project / "clips.json").write_text(
        json.dumps(clips, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nได้ {len(clips)} คลิป -> {sheets}")
    print("ส่งรูปในโฟลเดอร์ sheets ให้ Claude เพื่อเลือก moment แล้วเขียนลง plan.txt")


def read_plan(path, clips):
    if not path.exists():
        raise SystemExit(f"ไม่พบ {path} — เขียนบรรทัดละช็อต: V03 12.0 2.5")
    shots = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = PLAN_RE.match(line)
        if not m:
            raise SystemExit(f"{path}:{n}: รูปแบบไม่ถูกต้อง -> {line!r}")
        cid, start, dur = m.group(1).upper(), float(m.group(2)), float(m.group(3))
        if cid not in clips:
            raise SystemExit(f"{path}:{n}: ไม่มีคลิป {cid} ใน clips.json")
        if dur <= 0 or start + dur > clips[cid]["duration"] + 0.05:
            raise SystemExit(f"{path}:{n}: {cid} ยาวแค่ {clips[cid]['duration']}s "
                             f"ตัด {start}+{dur} ไม่ได้")
        shots.append({"src": clips[cid]["src"], "start": start,
                      "duration": dur, "audio": False})
    if not shots:
        raise SystemExit(f"{path}: ยังไม่มีช็อตเลย")
    return shots


def cut(args):
    project = args.project.resolve()
    clips_path = project / "clips.json"
    if not clips_path.exists():
        raise SystemExit(f"ไม่พบ {clips_path} — รัน scan ก่อน")
    clips = json.loads(clips_path.read_text(encoding="utf-8"))
    shots = read_plan(project / "plan.txt", clips)

    total = sum(s["duration"] for s in shots)
    if abs(total - args.length) > 0.05:
        raise SystemExit(f"plan.txt รวมได้ {total:.2f}s แต่ต้องการ {args.length:g}s "
                         f"(ขาด/เกิน {args.length - total:+.2f}s)")

    cfg = {"width": 1080, "height": 1920, "fps": 30, "shots": shots,
           "out": "out/final.mp4"}
    if args.music:
        music = args.music.expanduser().resolve()
        if not music.exists():
            raise SystemExit(f"ไม่พบไฟล์เพลง {music}")
        cfg["music"] = {"src": str(music), "start": args.music_start, "volume": 1.0}
    else:
        print("ไม่ได้ใส่ --music: จะได้คลิปเงียบ ไปใส่เพลงใน CapCut เอง")

    (project / "shots.yaml").write_text(
        "# สร้างอัตโนมัติจาก plan.txt โดย tools/moments.py cut — แก้ plan.txt แทน\n"
        + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    build = Path(__file__).parent / "build.py"
    cmd = [sys.executable, str(build), str(project)]
    if args.dry_run:
        cmd.append("--dry-run")
    raise SystemExit(subprocess.run(cmd).returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="ทำ contact sheet ของทุกคลิปในโฟลเดอร์")
    s.add_argument("folder", type=Path, help="โฟลเดอร์วีดีโอ เช่น ~/Downloads/LEON")
    s.add_argument("--project", type=Path, default=Path("projects/LEON_2_OCT"))
    s.set_defaults(func=scan)

    c = sub.add_parser("cut", help="ตัดต่อตาม plan.txt แล้วใส่เพลง")
    c.add_argument("--project", type=Path, default=Path("projects/LEON_2_OCT"))
    c.add_argument("--music", type=Path, help="ไฟล์เพลง เช่น ยิ้มอันตราย.mp3")
    c.add_argument("--music-start", type=float, default=0.0,
                   help="เริ่มเพลงที่วินาทีเท่าไร (เช่นท่อนฮุก)")
    c.add_argument("--length", type=float, default=22.0, help="ความยาวคลิป (วินาที)")
    c.add_argument("--dry-run", action="store_true", help="แสดงคำสั่ง ffmpeg ไม่ render")
    c.set_defaults(func=cut)

    args = ap.parse_args()
    if not ffmpeg_env.ffmpeg():
        raise SystemExit("หา ffmpeg ไม่เจอ — รัน ./setup.sh ก่อน")
    args.func(args)


if __name__ == "__main__":
    main()
