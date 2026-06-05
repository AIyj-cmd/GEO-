#!/usr/bin/env python3
"""Fix the broken generate_keyword_titles.py file"""
import re

filepath = "/root/keyword_title_outputs/generate_keyword_titles.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line 32: the API_KEY assignment
# Pattern: API_KEY=os.environ.get("MIMO_API_KEY", "") or os.environ.get("XIAOMI_API_KEY", "")
old_pattern = r'API_KEY=os\.env[^"]*"[^"]*",\s*""\)\s*or\s*os\.environ\.get\("XIAOMI_API_KEY",\s*""\)'
new_line = 'API_KEY=os.environ.get("MIMO_API_KEY", "") or os.environ.get("XIAOMI_API_KEY", "")'

content = re.sub(old_pattern, new_line, content)

# Fix the error message
old_msg = r'print\("请运行: export MIMO_API_KEY=\*\*\*"\)'
new_msg = 'print("请运行: export MIMO_API_KEY=your_key")'
content = re.sub(old_msg, new_msg, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[30:35], 31):
    print(f"Line {i}: {line.rstrip()}")
