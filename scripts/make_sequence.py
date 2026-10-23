"""Turn a short video into the scroll-driven image sequence used by the app's opening.

Usage (from the repository root):
    python scripts/make_sequence.py path/to/video.mp4
    python scripts/make_sequence.py path/to/video.mp4 --frames 120 --width 1280 --quality 70

Writes static/sequence/frame_000.webp, frame_001.webp, ... plus poster.webp and
manifest.json, replacing any previous sequence. The app reads manifest.json, so
swapping the video is just: run this script, then restart Streamlit.

Needs ffmpeg: either `pip install imageio-ffmpeg` (it bundles one) or ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "static" / "sequence"


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        found = shutil.which("ffmpeg")
        if found:
            return found
    raise SystemExit("ffmpeg not found. Install it with:  pip install imageio-ffmpeg")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path, help="Source video, e.g. an MP4 from Gemini")
    parser.add_argument("--frames", type=int, default=120, help="Frames to keep (default 120)")
    parser.add_argument("--width", type=int, default=1280, help="Frame width in pixels (default 1280)")
    parser.add_argument("--quality", type=int, default=70, help="WebP quality 1-100 (default 70)")
    args = parser.parse_args()
    if not args.video.exists():
        raise SystemExit(f"Video not found: {args.video}")
    if args.frames < 2:
        raise SystemExit("--frames must be at least 2")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [ffmpeg_executable(), "-v", "error", "-i", str(args.video), "-an",
             "-vf", f"scale={args.width}:-2", str(Path(tmp) / "f_%05d.png")],
            check=True,
        )
        decoded = sorted(Path(tmp).glob("f_*.png"))
        if len(decoded) < 2:
            raise SystemExit("Could not read frames from the video.")
        count = min(args.frames, len(decoded))
        picks = [round(i * (len(decoded) - 1) / (count - 1)) for i in range(count)]

        for old in OUT_DIR.glob("frame_*.webp"):
            old.unlink()
        width = height = 0
        for out_index, source_index in enumerate(picks):
            with Image.open(decoded[source_index]) as frame:
                frame = frame.convert("RGB")
                width, height = frame.size
                frame.save(OUT_DIR / f"frame_{out_index:03d}.webp", "WEBP", quality=args.quality, method=5)
                if out_index == 0:
                    frame.save(OUT_DIR / "poster.webp", "WEBP", quality=82, method=5)

    manifest = {
        "count": count,
        "width": width,
        "height": height,
        "pattern": "frame_{index:03d}.webp",
        "poster": "poster.webp",
        "source": args.video.name,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT_DIR.glob("*.webp"))
    print(f"Wrote {count} frames ({width}x{height}) to {OUT_DIR}, {total / 1e6:.1f} MB in total.")


if __name__ == "__main__":
    main()
