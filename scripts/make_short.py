"""Cut a long screen recording into a short captioned video.

Usage: uv run --with pillow python scripts/make_short.py <cuts.json>

cuts.json:
{
  "input": "demos/demo-3.mp4", "output": "demos/demo-3-short.mp4",
  "crop": [w, h, x, y],            # region of the recording to keep (app area, no browser chrome)
  "width": 1920,                    # output width; height follows the crop aspect (+ caption bar)
  "title": ["line 1", "line 2"],   # optional title card (3 s)
  "end": ["line 1", "line 2"],     # optional end card (3 s)
  "segments": [[start_s, end_s, speed, "caption"], ...],
  "audio": "music"                  # optional: replace narration with a generated ambient pad
}
Speed > 1 fast-forwards (e.g. LLM waits); the caption says so when speed >= 2.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
BAR = 120


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT, size, index=1 if bold else 0)
    except OSError:
        return ImageFont.load_default()


def caption_png(text: str, width: int, path: Path, note: str = ""):
    img = Image.new("RGB", (width, BAR), (24, 24, 27))
    d = ImageDraw.Draw(img)
    f = font(40, bold=True)
    d.text((width // 2, BAR // 2 - (10 if note else 0)), text, font=f, fill=(255, 255, 255), anchor="mm")
    if note:
        d.text((width // 2, BAR - 22), note, font=font(26), fill=(170, 170, 178), anchor="mm")
    img.save(path)


def card_png(lines: list[str], width: int, height: int, path: Path):
    img = Image.new("RGB", (width, height), (246, 245, 241))
    d = ImageDraw.Draw(img)
    y = height // 2 - (len(lines) - 1) * 45
    for i, line in enumerate(lines):
        d.text((width // 2, y + i * 90), line, font=font(64 if i == 0 else 40, bold=i == 0),
               fill=(29, 29, 31) if i == 0 else (90, 90, 96), anchor="mm")
    img.save(path)


def make_pad(duration: float, path: Path):
    """Soft ambient pad: slow sine chords (Cmaj7 → Am7 → Fmaj7 → G6), gentle swell, fade in/out. Self-made audio."""
    chords = [[130.81, 196.00, 246.94, 329.63], [110.00, 164.81, 196.00, 261.63],
              [87.31, 130.81, 174.61, 220.00], [98.00, 146.83, 196.00, 246.94]]
    bar = 8.0
    terms = []
    for k, chord in enumerate(chords):
        on = f"(gte(mod(t,{bar * 4}),{k * bar})*lt(mod(t,{bar * 4}),{(k + 1) * bar}))"
        env = f"sin(PI*mod(t,{bar})/{bar})"  # each chord swells in and out
        for f in chord:
            terms.append(f"{on}*{env}*sin(2*PI*{f}*t)")
    expr = "0.11*(" + "+".join(terms) + ")*(1+0.15*sin(2*PI*0.2*t))"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={duration:.2f}",
         "-af", f"lowpass=f=1800,aecho=0.8:0.7:220:0.25,afade=t=in:d=2,afade=t=out:st={max(0, duration - 3):.2f}:d=3,"
                "pan=stereo|c0=c0|c1=c0", str(path)])


def atempo(speed: float) -> str:
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main(cuts_path: str):
    cfg = json.loads(Path(cuts_path).read_text())
    cw, ch, cx, cy = cfg["crop"]
    W = cfg.get("width", 1920)
    H = round(ch * W / cw / 2) * 2
    tmp = Path(tempfile.mkdtemp(prefix="short_"))
    parts = []
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-ar", "48000", "-ac", "2"]

    def card(lines, name):
        png = tmp / f"{name}.png"
        card_png(lines, W, H + BAR, png)
        out = tmp / f"{name}.mp4"
        run(["ffmpeg", "-y", "-loop", "1", "-t", "3", "-i", str(png), "-f", "lavfi", "-t", "3",
             "-i", "anullsrc=r=48000:cl=stereo", *enc, "-shortest", str(out)])
        parts.append(out)

    if cfg.get("title"):
        card(cfg["title"], "title")
    for i, (start, end, speed, text) in enumerate(cfg["segments"]):
        png = tmp / f"cap{i}.png"
        caption_png(text, W, png, note=f"fast-forward {speed:g}×" if speed >= 2 else "")
        out = tmp / f"seg{i:02d}.mp4"
        vf = (f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{H},setpts=(PTS-STARTPTS)/{speed},"
              f"pad={W}:{H + BAR}:0:0:black[v];[v][1:v]overlay=0:{H}[out]")
        run(["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", cfg["input"], "-i", str(png),
             "-filter_complex", vf + f";[0:a]asetpts=PTS-STARTPTS,{atempo(speed)}[a]",
             "-map", "[out]", "-map", "[a]", *enc, str(out)])
        parts.append(out)
    if cfg.get("end"):
        card(cfg["end"], "end")
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    if cfg.get("audio") == "music":  # replace narration with a generated ambient pad (no third-party assets)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(joined)], capture_output=True, text=True).stdout)
        pad = tmp / "pad.wav"
        make_pad(dur, pad)
        run(["ffmpeg", "-y", "-i", str(joined), "-i", str(pad), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "160k", "-shortest", cfg["output"]])
    else:
        joined.replace(cfg["output"])
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", cfg["output"]],
                         capture_output=True, text=True).stdout.strip()
    print(f"wrote {cfg['output']} ({float(dur):.1f} s, {len(cfg['segments'])} segments)")


if __name__ == "__main__":
    main(sys.argv[1])
