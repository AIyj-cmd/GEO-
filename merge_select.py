#!/usr/bin/env python3
"""Fast merge, dedup, and selection for keyword titles"""
import os, re, json, unicodedata, time
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict

OUTPUT_DIR = Path("/root/keyword_title_outputs")

def normalize(text):
    text = text.strip()
    text = re.sub(r'^\d+[\.\、\)\]\s]+', '', text)
    text = re.sub(r'[，。？！、；：""''（）【】《》\s\.\,\?\!\;\:\"\'\(\)\[\]\<\>]', '', text)
    text = text.lower()
    text = unicodedata.normalize('NFKC', text)
    return text

def load_all():
    """Load titles from all category files"""
    all_titles = []
    cat_counts = {}
    for f in sorted(OUTPUT_DIR.glob("[0-9]*_*.txt")):
        titles = [line.strip() for line in open(f, encoding='utf-8') if line.strip()]
        cat_counts[f.name] = len(titles)
        all_titles.extend(titles)
    return all_titles, cat_counts

# ── Step 1: Load all titles ──
print("Step 1: Loading all titles...", flush=True)
t0 = time.time()
all_titles, cat_counts = load_all()
print(f"  Loaded {len(all_titles)} titles in {time.time()-t0:.1f}s", flush=True)

# ── Step 2: Exact + normalized dedup ──
print("Step 2: Exact + normalized dedup...", flush=True)
t0 = time.time()
seen_norm = set()
exact_deduped = []
for t in all_titles:
    n = normalize(t)
    if n not in seen_norm:
        seen_norm.add(n)
        exact_deduped.append(t)
print(f"  {len(all_titles)} -> {len(exact_deduped)} (removed {len(all_titles)-len(exact_deduped)} exact/norm dupes) in {time.time()-t0:.1f}s", flush=True)

# ── Step 3: Fast similarity dedup using n-gram hashing ──
print("Step 3: Similarity dedup (n-gram pre-filter + SequenceMatcher)...", flush=True)
t0 = time.time()

def get_ngrams(text, n=2):
    """Get character n-grams for fast filtering"""
    nt = normalize(text)
    if len(nt) < n:
        return {nt}
    return {nt[i:i+n] for i in range(len(nt)-n+1)}

SIM_THRESHOLD = 0.85
# Build n-gram index for fast candidate lookup
title_ngrams = []
final_titles = []
final_norms = []

for i, t in enumerate(exact_deduped):
    if i % 1000 == 0 and i > 0:
        print(f"  Processing {i}/{len(exact_deduped)}...", flush=True)
    
    nt = normalize(t)
    ng = get_ngrams(t)
    
    is_dup = False
    # Only check against candidates with similar n-gram overlap
    for j, (fng, fn) in enumerate(zip(title_ngrams, final_norms)):
        # Fast n-gram Jaccard pre-filter
        overlap = len(ng & fng)
        union = len(ng | fng)
        if union == 0:
            jaccard = 0
        else:
            jaccard = overlap / union
        
        # Only do expensive SequenceMatcher if n-gram overlap is promising
        if jaccard > 0.4:
            sim = SequenceMatcher(None, nt, fn).ratio()
            if sim >= SIM_THRESHOLD:
                is_dup = True
                break
    
    if not is_dup:
        final_titles.append(t)
        final_norms.append(nt)
        title_ngrams.append(ng)

elapsed = time.time() - t0
print(f"  {len(exact_deduped)} -> {len(final_titles)} (removed {len(exact_deduped)-len(final_titles)} similar) in {elapsed:.1f}s", flush=True)

# ── Step 4: Save all_titles.txt ──
print("Step 4: Saving all_titles.txt...", flush=True)
with open(OUTPUT_DIR / "all_titles.txt", 'w', encoding='utf-8') as f:
    for t in final_titles:
        f.write(t + '\n')
print(f"  Saved {len(final_titles)} titles", flush=True)

# ── Step 5: Scoring function ──
high_value_keywords = [
    '鞋服', '服装', '女装', '男装', '运动服', '童装',
    '小红书',
    '退货', '退换', '逆向', '售后',
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
    s = 0
    for kw in high_value_keywords:
        if kw in title:
            s += 1
    if 15 <= len(title) <= 40:
        s += 1
    if '?' in title or '？' in title:
        s += 1
    if len(title) < 15:
        s -= 2
    return s

# ── Step 6: Select top-N with strict dedup ──
def select_top(n, threshold, output_name):
    print(f"Selecting {output_name} (top {n}, threshold {threshold})...", flush=True)
    t0 = time.time()
    scored = [(t, score(t)) for t in final_titles]
    scored.sort(key=lambda x: -x[1])
    
    selected = []
    selected_norms = []
    for t, s in scored:
        if len(selected) >= n:
            break
        nt = normalize(t)
        is_dup = False
        ng = get_ngrams(t)
        for j, (sng, sn) in enumerate(zip([get_ngrams(st) for st in selected], selected_norms)):
            overlap = len(ng & sng)
            union = len(ng | sng)
            jaccard = overlap / union if union > 0 else 0
            if jaccard > 0.4:
                sim = SequenceMatcher(None, nt, sn).ratio()
                if sim >= threshold:
                    is_dup = True
                    break
        if not is_dup:
            selected.append(t)
            selected_norms.append(nt)
    
    with open(OUTPUT_DIR / output_name, 'w', encoding='utf-8') as f:
        for t in selected:
            f.write(t + '\n')
    print(f"  {output_name}: {len(selected)} titles in {time.time()-t0:.1f}s", flush=True)
    return selected

top1000 = select_top(1000, 0.85, "selected_top_1000.txt")
top100 = select_top(100, 0.82, "selected_top_100.txt")
top30 = select_top(30, 0.80, "selected_geo_30.txt")

# ── Step 7: Save dedupe index ──
dedupe_index = {
    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total_raw": len(all_titles),
    "total_exact_deduped": len(exact_deduped),
    "total_final": len(final_titles),
    "categories": cat_counts,
    "similarity_threshold": SIM_THRESHOLD,
}
with open(OUTPUT_DIR / "dedupe_index.json", 'w', encoding='utf-8') as f:
    json.dump(dedupe_index, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("完成！")
print(f"  all_titles.txt: {len(final_titles)}")
print(f"  selected_top_1000.txt: {len(top1000)}")
print(f"  selected_top_100.txt: {len(top100)}")
print(f"  selected_geo_30.txt: {len(top30)}")
print("=" * 60)
