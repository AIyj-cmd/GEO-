#!/usr/bin/env python3
import os, json, urllib.request

# Try to load .env
env_path = os.path.expanduser("~/.hermes/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("MIMO_API_KEY", "") or os.environ.get("XIAOMI_API_KEY", "")
print(f"Key prefix: {API_KEY[:15]}...")
print(f"Key length: {len(API_KEY)}")

url = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
data = json.dumps({
    "model": "mimo-v2.5-pro",
    "messages": [{"role": "user", "content": "回复OK即可"}],
    "max_tokens": 10,
    "temperature": 0.1,
}).encode()
req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
})
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read().decode())
print("API OK:", result["choices"][0]["message"]["content"])
