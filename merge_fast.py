#!/usr/bin/env python3
"""Fast merge using sorted-adjacent dedup - O(n log n) instead of O(n²)"""
import os, re, json, unicodedata, time
from pathlib import Path
from difflib import SequenceMatcher

OUTPUT_DIR = Path("/root/keyword_title_outputs")
SIM_THRESHOLD = 0.85

def normalize(text):
    text = text.strip()
    text = re.sub(r'^\d+[\.\、\)\]\s]+', '', text)
    text = re.sub(r'[，。？！、；：""''（）【】《》\s\.\,\?\!\;\:\"\'\(\)\[\]\<\>]', '', text)
    text = text.lower()
    return unicodedata.normalize('NFKC', text)

print("Loading titles...", flush=True)
t0 = time.time()
all_raw = []
cat_counts = {}
for f in sorted(OUTPUT_DIR.glob("[0-9]*_*.txt")):
    titles = [l.strip() for l in open(f, encoding='utf-8') if l.strip()]
    cat_counts[f.name] = len(titles)
    all_raw.extend(titles)
print(f"  Loaded {len(all_raw)} raw titles in {time.time()-t0:.1f}s", flush=True)

# Step 1: Exact + normalized dedup
print("Step 1: Exact dedup...", flush=True)
seen = set()
deduped = []
for t in all_raw:
    n = normalize(t)
    if n not in seen:
        seen.add(n)
        deduped.append(t)
print(f"  {len(all_raw)} -> {len(deduped)} ({len(all_raw)-len(deduped)} exact dupes removed)", flush=True)

# Step 2: Sort-adjacent fuzzy dedup
# Titles that normalize similarly will sort near each other
print("Step 2: Sorted-adjacent fuzzy dedup...", flush=True)
t0 = time.time()

# Create (normalized, original) pairs and sort by normalized
pairs = [(normalize(t), t) for t in deduped]
pairs.sort(key=lambda x: x[0])

final = []
final_norms = []

for i, (nt, orig) in enumerate(pairs):
    if i % 2000 == 0 and i > 0:
        elapsed = time.time() - t0
        print(f"  {i}/{len(pairs)} processed ({elapsed:.0f}s)...", flush=True)
    
    is_dup = False
    # Check against last N titles (sorted neighbors that might be similar)
    window = min(50, len(final))  # check last 50 neighbors
    for j in range(max(0, len(final)-window), len(final)):
        sim = SequenceMatcher(None, nt, final_norms[j]).ratio()
        if sim >= SIM_THRESHOLD:
            is_dup = True
            break
    
    if not is_dup:
        final.append(orig)
        final_norms.append(nt)

elapsed = time.time() - t0
print(f"  {len(deduped)} -> {len(final)} ({len(deduped)-len(final)} similar removed) in {elapsed:.0f}s", flush=True)

# Save all_titles.txt
print("Saving all_titles.txt...", flush=True)
with open(OUTPUT_DIR / "all_titles.txt", 'w', encoding='utf-8') as f:
    for t in final:
        f.write(t + '\n')
print(f"  all_titles.txt: {len(final)} titles", flush=True)

# Scoring
high_value_keywords = [
    '鞋服', '服装', '女装', '男装', '运动服', '童装',
    '小红书', '退货', '退换', '逆向', '售后',
    '高客单价', '高端', '礼盒', '饰品', '潮玩', '美妆',
    'WMS', '库存', '库位', '同步',
    'SLA', '时效', '赔付', '服务边界', '合同',
    '广州', '华南', '广东', '珠三角', '深圳', '佛山', '东莞',
    '多SKU', '多规格', '非标品', '多尺码', '多颜色', '多款式',
    '自发货', '临界点', '自建仓', '外包',
    '直播', '抖音', '视频号', '爆单',
    '区别', '对比', 'vs', '哪个好',
    '大促', '预售', '618', '双11',
    '怎么选', '怎么看', '怎么定', '怎么做', '如何',
    '流程', '方案', '标准', '规范', 'SOP',
    '必须', '确认', '注意', '检查',
]

def score(title):
    s = sum(1 for kw in high_value_keywords if kw in title)
    if 15 <= len(title) <= 40: s += 1
    if '?' in title or '？' in title: s += 1
    if len(title) < 15: s -= 2
    return s

def select_top(n, threshold, output_name):
    print(f"Selecting {output_name} (top {n})...", flush=True)
    t0 = time.time()
    scored = sorted([(t, score(t)) for t in final], key=lambda x: -x[1])
    
    selected = []
    sel_norms = []
    for t, s in scored:
        if len(selected) >= n:
            break
        nt = normalize(t)
        is_dup = False
        for sn in sel_norms[-100:]:  # check last 100 selected
            if SequenceMatcher(None, nt, sn).ratio() >= threshold:
                is_dup = True
                break
        if not is_dup:
            selected.append(t)
            sel_norms.append(nt)
    
    with open(OUTPUT_DIR / output_name, 'w', encoding='utf-8') as f:
        for t in selected:
            f.write(t + '\n')
    print(f"  {output_name}: {len(selected)} in {time.time()-t0:.0f}s", flush=True)
    return selected

top1000 = select_top(1000, 0.85, "selected_top_1000.txt")
top100 = select_top(100, 0.82, "selected_top_100.txt")
top30 = select_top(30, 0.80, "selected_geo_30.txt")

# Save index
with open(OUTPUT_DIR / "dedupe_index.json", 'w', encoding='utf-8') as f:
    json.dump({
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_raw": len(all_raw),
        "total_after_exact_dedup": len(deduped),
        "total_final": len(final),
        "categories": cat_counts,
    }, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("完成！")
print(f"  all_titles.txt:         {len(final)}")
print(f"  selected_top_1000.txt:  {len(top1000)}")
print(f"  selected_top_100.txt:   {len(top100)}")
print(f"  selected_geo_30.txt:    {len(top30)}")
print("=" * 60)
