#!/usr/bin/env bash
# ติดตั้งของที่ pipeline ต้องใช้ — รันครั้งเดียวพอ
set -euo pipefail

echo "==> ติดตั้ง python packages"
pip3 install --quiet --upgrade imageio-ffmpeg pyyaml

echo "==> ตรวจ ffmpeg"
python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
import ffmpeg_env
exe = ffmpeg_env.ffmpeg()
if not exe:
    sys.exit("หา ffmpeg ไม่เจอ")
print("   ", exe)
PY

echo "==> ตรวจฟอนต์ไทย"
ls assets/fonts/*.ttf >/dev/null 2>&1 || { echo "ไม่พบฟอนต์ใน assets/fonts"; exit 1; }
ls assets/fonts/

echo
echo "พร้อมใช้งานแล้ว ดูขั้นตอนถัดไปใน README.md"
