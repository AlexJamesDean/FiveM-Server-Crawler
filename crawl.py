"""
FiveM Resource Crawler & Dataset Builder (Logic-Aware Version)
-------------------------------------------------------------
A production-grade asynchronous crawler that indexes FiveM resources by reading
fxmanifest.lua files, parsing code by *logical blocks* (functions, events, callbacks),
and generating contextual Q/A dataset entries using a local Ollama model.

Usage:
    python crawl_fivem_resources.py
"""

import os
import re
import json
import asyncio
import aiohttp
import glob
import hashlib
import time
from datetime import datetime
import asyncio, aiohttp, json, subprocess, time

# --------------------------------------
# CONFIGURATION
# --------------------------------------
MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/chat"
DATASET_PATH = "./dataset/fivem_dataset.jsonl"
PROGRESS_LOG = "./dataset/progress.json"
ROOT_DIR = os.getcwd()
TEMPERATURE = 0.8
CHUNK_LIMIT = 4000  # soft limit per logical block

# --------------------------------------
# UTILITIES
# --------------------------------------
def safe_read(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ""

def parse_fxmanifest(path):
    data = safe_read(path)
    fx = {}
    for key in ["name", "author", "description", "version", "ui_page"]:
        match = re.search(fr'{key}\s+\"([^\"]+)\"', data)
        if match:
            fx[key] = match.group(1)
    for block in ["client_scripts", "server_scripts", "shared_scripts", "files"]:
        matches = re.findall(fr'{block}\s+{{([^}}]+)}}', data)
        if matches:
            entries = []
            for group in matches:
                entries += [x.strip().strip("'\"") for x in group.split(',') if x.strip()]
            fx[block] = entries
    return fx

def hash_id(*args):
    return hashlib.sha1("::".join(args).encode()).hexdigest()

# --------------------------------------
# LOGIC-AWARE CHUNKING
# --------------------------------------
def extract_lua_blocks(code):
    blocks, stack, start, lines = [], 0, 0, code.splitlines()
    for i, line in enumerate(lines):
        if re.match(r'\s*function\b', line) or 'RegisterNetEvent' in line or 'RegisterNUICallback' in line:
            if stack == 0:
                start = i
            stack += 1
        if re.match(r'\s*end\b', line) and stack > 0:
            stack -= 1
            if stack == 0 and i > start:
                block = '\n'.join(lines[start:i+1])
                if len(block.strip()) > 80:
                    blocks.append(block[:CHUNK_LIMIT])
    return blocks or [code[:CHUNK_LIMIT]]

def extract_js_blocks(code):
    blocks = []
    pattern = re.compile(r'(function\s+\w+\s*\(|window\.addEventListener|fetch\(|postMessage)', re.MULTILINE)
    matches = list(pattern.finditer(code))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(code)
        block = code[start:end]
        if len(block.strip()) > 80:
            blocks.append(block[:CHUNK_LIMIT])
    return blocks or [code[:CHUNK_LIMIT]]

def extract_html_blocks(code):
    blocks = re.findall(r'<script[\s\S]*?</script>', code)
    return [b[:CHUNK_LIMIT] for b in blocks] or [code[:CHUNK_LIMIT]]

def extract_blocks(text, ext):
    if ext == '.lua':
        return extract_lua_blocks(text)
    elif ext == '.js':
        return extract_js_blocks(text)
    elif ext == '.html':
        return extract_html_blocks(text)
    else:
        return [text[:CHUNK_LIMIT]]

# --------------------------------------
# LLM CALLER
# --------------------------------------
ollama_lock = asyncio.Lock()

async def query_llm(payload, max_retries=3, retry_delay=30):
    """
    Send one request at a time to Ollama and retry automatically if the runner dies.
    """
    async with ollama_lock:
        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OLLAMA_URL, json=payload, timeout=600) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            raise RuntimeError(f"HTTP {resp.status}: {text}")

                        final_text = ""
                        async for line in resp.content:
                            if not line:
                                continue
                            try:
                                obj = json.loads(line.decode().strip())
                                if "message" in obj and "content" in obj["message"]:
                                    final_text += obj["message"]["content"]
                            except Exception:
                                continue

                        if final_text.strip():
                            return final_text.strip()

                        # fallthrough: no text, maybe error JSON
                        text = await resp.text()
                        if "exit status 2" in text.lower():
                            raise RuntimeError("Ollama runner crashed")
                        return text

            except Exception as e:
                print(f"[Error] Attempt {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    print(f"[Ollama] Restarting server and retrying in {retry_delay}s...")
                    try:
                        subprocess.run(["ollama", "stop", "all"], check=False)
                    except Exception:
                        pass
                    time.sleep(retry_delay)
                    continue
                else:
                    return f"[Error: {e}]"

# --------------------------------------
# MAIN RESOURCE CRAWLER
# --------------------------------------
async def process_resource(resource_dir):
    fx_path = os.path.join(resource_dir, "fxmanifest.lua")
    if not os.path.exists(fx_path):
        return []

    fx = parse_fxmanifest(fx_path)
    all_files = set()
    for key in ["client_scripts", "server_scripts", "shared_scripts", "files"]:
        for pattern in fx.get(key, []):
            # Skip commented or blank lines
            if pattern.startswith("--") or not pattern.strip():
                continue

            # Resolve relative to the manifest directory
            abs_pattern = os.path.join(resource_dir, pattern).replace("\\", "/")

            # Expand single and recursive wildcards
            expanded = glob.glob(abs_pattern, recursive=True)

            # If it’s a direct file with no wildcard, add it manually if it exists
            if not expanded and os.path.exists(abs_pattern):
                expanded = [abs_pattern]

            if not expanded:
                print(f"[Warn] No files matched pattern {pattern} in {resource_dir}")
            else:
                for f in expanded:
                    all_files.add(os.path.normpath(f))


    ui_root = fx.get("ui_page")
    if ui_root:
        ui_path = os.path.join(resource_dir, ui_root)
        if os.path.exists(ui_path):
            all_files.add(ui_path)

    dataset_records = []

    for file_path in all_files:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ('.lua', '.js', '.html', '.css'):
            continue

        text = safe_read(file_path)
        blocks = extract_blocks(text, ext)
        print(f"[Blocks] {file_path} -> {len(blocks)} blocks found")

        for block in blocks:
            chunk_id = hash_id(resource_dir, file_path, block)
            sys_prompt = (
                f"You are an expert FiveM developer analyzing {ext} code. "
                f"Explain what this block does, identify any events or NUI communication, "
                f"and generate 2-3 realistic developer questions about it."
            )

            user_prompt = f"Resource: {os.path.basename(resource_dir)}\nFile: {file_path}\n\n{block[:CHUNK_LIMIT]}"

            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "options": {"temperature": TEMPERATURE, "num_predict": 1024}
            }

            answer = await query_llm(payload)
            record = {
                "id": chunk_id,
                "timestamp": datetime.utcnow().isoformat(),
                "resource": os.path.basename(resource_dir),
                "path": file_path,
                "fxmanifest": fx,
                "prompt": user_prompt,
                "completion": answer
            }

            os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
            with open(DATASET_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            dataset_records.append(record)
            await asyncio.sleep(1.5)

    return dataset_records

async def main():
    # Load previous progress if exists
    progress = {}
    if os.path.exists(PROGRESS_LOG):
        try:
            with open(PROGRESS_LOG, 'r', encoding='utf-8') as pf:
                progress = json.load(pf)
        except Exception:
            progress = {}

    while True:
        resource_dirs = []

        # Recursively find all folders that contain an fxmanifest.lua
        for root, dirs, files in os.walk(ROOT_DIR):
            for d in dirs:
                candidate = os.path.join(root, d)
                manifest = os.path.join(candidate, "fxmanifest.lua")
                if os.path.exists(manifest):
                    resource_dirs.append(candidate)

        print(f"[Crawler] Found {len(resource_dirs)} resources with fxmanifest.lua.")

        for resource_path in resource_dirs:
            resource_name = os.path.basename(resource_path)

            print(f"[Crawler] Processing {resource_name} -> {resource_path} ...")
            records = await process_resource(resource_path)

            progress[resource_name] = {
                "last_run": datetime.utcnow().isoformat(),
                "count": len(records),
                "path": resource_path,
            }

            # Persist progress after each resource
            os.makedirs(os.path.dirname(PROGRESS_LOG), exist_ok=True)
            with open(PROGRESS_LOG, 'w', encoding='utf-8') as pf:
                json.dump(progress, pf, indent=2)

        print("[Crawler] Epoch complete. Sleeping before next pass...")
        await asyncio.sleep(3600)  # 1 hour between epochs


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Crawler] Gracefully shutting down.")

