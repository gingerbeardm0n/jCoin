"""Pull YouTube auto-caption transcripts for Trader Mayne videos -> raw text files.
Caption-only (fast). Skips files already present."""
import os
import re
import glob
import subprocess
import sys

OUT = r"C:\Repositories\jCoin\pipeline\raw"
os.makedirs(OUT, exist_ok=True)

VIDEOS = {
    "mayne_liquidity_sweeps":      "https://www.youtube.com/watch?v=8lhYu10v0NQ",
    "mayne_equal_high_low":        "https://www.youtube.com/watch?v=-UIrmQ3y0nI",
    "mayne_market_structure_ep2":  "https://www.youtube.com/watch?v=YxMMov8roBQ",
    "mayne_market_structure_pro":  "https://www.youtube.com/watch?v=jt5ncnNoCTQ",
    "mayne_order_blocks":          "https://www.youtube.com/watch?v=NSTmMdnQg7Y",
}

def vtt_to_text(vtt_path):
    lines = []
    seen = set()
    with open(vtt_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # strip inline timing tags <00:00:00.000> and <c> tags
            line = re.sub(r"<[^>]+>", "", line)
            line = line.strip()
            if not line:
                continue
            if line in seen:  # auto-captions repeat lines heavily
                continue
            seen.add(line)
            lines.append(line)
    return " ".join(lines)

def main():
    for name, url in VIDEOS.items():
        out_txt = os.path.join(OUT, name + ".txt")
        if os.path.exists(out_txt):
            print(f"SKIP {name} (exists)")
            continue
        tmpl = os.path.join(OUT, name)
        # download auto subs only, no video
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "-o", tmpl,
            url,
        ]
        print(f"FETCH {name} ...")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERR yt-dlp: {r.stderr.strip().splitlines()[-1] if r.stderr else 'unknown'}")
            continue
        # find the produced vtt
        vtts = glob.glob(tmpl + "*.vtt")
        if not vtts:
            print(f"  NO CAPTIONS for {name}")
            continue
        text = vtt_to_text(vtts[0])
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(text)
        # cleanup vtt
        for v in vtts:
            os.remove(v)
        print(f"  OK {name}: {len(text)} chars")

if __name__ == "__main__":
    main()
