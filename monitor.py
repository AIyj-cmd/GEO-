#!/usr/bin/env python3
"""Monitor keyword title generation progress"""
import os, time, glob, json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/root/keyword_title_outputs")
LOG = OUTPUT_DIR / "monitor.log"

while True:
    files = sorted(OUTPUT_DIR.glob("[0-9]*_*.txt"))
    now = datetime.now().strftime("%H:%M:%S")
    total = 0
    parts = []
    for f in files:
        count = sum(1 for _ in open(f))
        total += count
        parts.append(f"{f.name[:20]}...: {count}")
    
    # Check if all_titles.txt exists (means generation is done)
    all_file = OUTPUT_DIR / "all_titles.txt"
    done = all_file.exists() and all_file.stat().st_size > 0
    
    line = f"[{now}] Total: {total} | " + " | ".join(parts)
    with open(LOG, 'a') as f:
        f.write(line + "\n")
    print(line, flush=True)
    
    if done:
        all_count = sum(1 for _ in open(all_file))
        print(f"[{now}] GENERATION COMPLETE! all_titles.txt: {all_count}", flush=True)
        break
    
    time.sleep(300)  # check every 5 min
