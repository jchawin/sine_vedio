#!/usr/bin/env python3
"""ประกอบคลิปแนวตั้งจากไฟล์ shots.yaml

    python3 tools/build.py projects/ชื่องาน

อ่านโครงช็อตจาก shots.yaml ในโฟลเดอร์งาน แล้วต่อเป็นคลิปเดียว:
ปรับทุกช็อตเป็น 1080x1920 ใส่ Ken Burns ให้ภาพนิ่ง ต่อเสียง ผสมเพลงประกอบ
และเบิร์นซับ .ass ลงไป
"""
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import ffmpeg_env  # noqa: E402

MOTIONS = {"zoom-in", "zoom-out", "pan-left", "pan-right", "none"}


def esc(path):
    """escape path ให้ใช้ในสตริง filter ของ ffmpeg ได้"""
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def kenburns(motion, dur, fps, w, h):
    """filter สำหรับภาพนิ่ง: ขยายก่อนแล้วค่อย zoompan เพื่อไม่ให้ภาพกระตุก"""
    frames = max(1, int(round(dur * fps)))
    big = f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2}"
    if motion == "none":
        return f"{big},scale={w}:{h}"
    # ซูม 1.0 -> 1.12 ตลอดช็อต
    z_in = f"min(1.12,1+0.12*on/{frames})"
    z_out = f"max(1.0,1.12-0.12*on/{frames})"
    if motion == "zoom-in":
        z, x, y = z_in, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "zoom-out":
        z, x, y = z_out, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "pan-left":
        z, x, y = "1.12", f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
    else:  # pan-right
        z, x, y = "1.12", f"(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"
    return f"{big},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"


def load(project):
    cfg_path = project / "shots.yaml"
    if not cfg_path.exists():
        raise SystemExit(f"ไม่พบ {cfg_path}")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not cfg.get("shots"):
        raise SystemExit(f"{cfg_path}: ต้องมีรายการ shots อย่างน้อยหนึ่งช็อต")
    return cfg


def resolve(project, ref):
    """path ใน shots.yaml อ้างอิงจากโฟลเดอร์งาน แต่ยอมให้ชี้ออกไปนอกได้"""
    p = (project / ref).resolve()
    if not p.exists():
        raise SystemExit(f"ไม่พบไฟล์: {ref} (มองหาที่ {p})")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path, help="โฟลเดอร์งาน เช่น projects/earbuds-01")
    ap.add_argument("--dry-run", action="store_true", help="แสดงคำสั่ง ffmpeg แล้วจบ ไม่ render")
    args = ap.parse_args()

    project = args.project.resolve()
    cfg = load(project)
    w = int(cfg.get("width", 1080))
    h = int(cfg.get("height", 1920))
    fps = int(cfg.get("fps", 30))
    shots = cfg["shots"]

    ff = ffmpeg_env.ffmpeg()
    if not ff:
        raise SystemExit("หา ffmpeg ไม่เจอ — รัน ./setup.sh ก่อน")

    inputs, vparts, aparts = [], [], []
    next_stream = 0

    def add_input(*tokens):
        """เพิ่ม input แล้วคืนหมายเลข stream ของมัน"""
        nonlocal next_stream
        inputs.extend(tokens)
        next_stream += 1
        return next_stream - 1

    # ช็อตที่ไม่มีเสียงของตัวเองจะไปดึงจาก input ความเงียบอันเดียวร่วมกัน
    needs_silence = any(
        not s.get("audio", True)
        or Path(str(s["src"])).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        for s in shots
    )
    silence = add_input("-f", "lavfi", "-t", "3600", "-i", "anullsrc=r=48000:cl=stereo") \
        if needs_silence else None

    total = 0.0
    shot_ids = []
    for shot in shots:
        src = resolve(project, str(shot["src"]))
        dur = float(shot.get("duration", 3.0))
        if dur <= 0:
            raise SystemExit(f"duration ของ {shot['src']} ต้องมากกว่า 0")
        total += dur

        is_image = src.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        motion = shot.get("motion", "zoom-in" if is_image else "none")
        if motion not in MOTIONS:
            raise SystemExit(f"motion ไม่รู้จัก: {motion} (เลือกได้: {', '.join(sorted(MOTIONS))})")

        if is_image:
            n = add_input("-loop", "1", "-t", f"{dur}", "-i", str(src))
            vf = kenburns(motion, dur, fps, w, h)
            use_audio = False
        else:
            n = add_input("-ss", f"{float(shot.get('start', 0))}", "-t", f"{dur}", "-i", str(src))
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}"
            use_audio = shot.get("audio", True) and ffmpeg_env.has_audio(src)

        shot_ids.append(n)
        vparts.append(f"[{n}:v]{vf},setsar=1,format=yuv420p,"
                      f"trim=duration={dur},setpts=PTS-STARTPTS[v{n}]")
        asrc = f"{n}:a" if use_audio else f"{silence}:a"
        aparts.append(f"[{asrc}]atrim=duration={dur},asetpts=PTS-STARTPTS,"
                      f"aformat=sample_rates=48000:channel_layouts=stereo[a{n}]")

    n_shots = len(shots)
    vlabels = "".join(f"[v{i}]" for i in shot_ids)
    alabels = "".join(f"[a{i}]" for i in shot_ids)

    graph = vparts + aparts
    graph.append(f"{vlabels}concat=n={n_shots}:v=1:a=0[vcat]")
    graph.append(f"{alabels}concat=n={n_shots}:v=0:a=1[voice]")

    music = cfg.get("music")
    if music and music.get("src"):
        msrc = resolve(project, str(music["src"]))
        vol = float(music.get("volume", 0.15))
        # start = เริ่มเพลงจากวินาทีที่เท่าไร (เช่นข้ามไปท่อนฮุก)
        mstart = float(music.get("start", 0))
        mstream = add_input("-stream_loop", "-1", "-ss", f"{mstart}", "-i", str(msrc))
        graph.append(f"[{mstream}:a]volume={vol},atrim=duration={total},"
                     f"asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[mus]")
        graph.append("[voice][mus]amix=inputs=2:duration=first:normalize=0,"
                     f"afade=t=out:st={max(0, total - 0.4):.2f}:d=0.4[aout]")
    else:
        graph.append(f"[voice]afade=t=out:st={max(0, total - 0.4):.2f}:d=0.4[aout]")

    subs = cfg.get("subtitles")
    if subs:
        spath = resolve(project, str(subs))
        fonts = Path(__file__).resolve().parent.parent / "assets" / "fonts"
        graph.append(f"[vcat]ass=filename='{esc(spath)}':fontsdir='{esc(fonts)}'[vout]")
        vmap = "[vout]"
    else:
        vmap = "[vcat]"

    out = project / cfg.get("out", "out/final.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [ff, "-y", *inputs, "-filter_complex", ";".join(graph),
           "-map", vmap, "-map", "[aout]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-r", str(fps),
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-t", f"{total}", str(out)]

    if args.dry_run:
        print(" ".join(cmd))
        return

    print(f"กำลัง render {n_shots} ช็อต รวม {total:.1f} วินาที -> {out}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:])
        raise SystemExit("ffmpeg ล้มเหลว")
    print(f"เสร็จแล้ว: {out}  ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
