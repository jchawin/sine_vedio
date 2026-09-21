"""หา binary ของ ffmpeg/ffprobe ให้เจอ ไม่ว่าจะติดตั้งแบบไหน"""
import os
import shutil


def _from_imageio(name):
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if name == "ffmpeg":
        return exe
    # build ของ imageio มีแต่ ffmpeg ไม่มี ffprobe
    return None


def ffmpeg():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or _from_imageio("ffmpeg")


def ffprobe():
    return os.environ.get("FFPROBE") or shutil.which("ffprobe")


def duration(path):
    """ความยาวไฟล์วีดีโอ/เสียง (วินาที) — ใช้ ffprobe ถ้ามี ไม่มีก็อ่านจาก log ของ ffmpeg"""
    import json
    import re
    import subprocess

    probe = ffprobe()
    if probe:
        out = subprocess.run(
            [probe, "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])

    out = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out.stderr)
    if not m:
        raise RuntimeError(f"อ่านความยาวของ {path} ไม่ได้")
    h, m_, s = m.groups()
    return int(h) * 3600 + int(m_) * 60 + float(s)


def has_audio(path):
    """ไฟล์นี้มีแทร็กเสียงไหม (อ่านจาก log ของ ffmpeg ไม่ต้องพึ่ง ffprobe)"""
    import subprocess

    out = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True)
    return "Audio:" in out.stderr
