import json
from collections import Counter
from tqdm import tqdm
import os

DATASET_PATH = "./dataset/fivem_dataset_deduped.jsonl"

FRONTEND_EXTS = {".js", ".html", ".css"}
BACKEND_EXTS = {".lua", ".sql", ".json", ".xml", ".cfg"}

def main():
    ext_counter = Counter()
    dir_counter = Counter()
    frontend_count = 0
    backend_count = 0
    total = 0

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Analyzing file types"):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            path = entry.get("path", "")
            ext = os.path.splitext(path)[1].lower()
            base_dir = os.path.basename(os.path.dirname(path))

            if not ext:
                continue

            ext_counter[ext] += 1
            dir_counter[base_dir] += 1
            total += 1

            if ext in FRONTEND_EXTS:
                frontend_count += 1
            elif ext in BACKEND_EXTS:
                backend_count += 1

    print("\n--- File Type Breakdown ---")
    for ext, count in ext_counter.most_common():
        pct = (count / total) * 100
        print(f"{ext:<8}: {count:>5} ({pct:.1f}%)")

    print(f"\nFront-end files : {frontend_count} ({(frontend_count/total)*100:.1f}%)")
    print(f"Back-end files  : {backend_count} ({(backend_count/total)*100:.1f}%)")

    print("\n--- Top 10 Most Represented Directories ---")
    for dir_name, count in dir_counter.most_common(10):
        pct = (count / total) * 100
        print(f"{dir_name:<20}: {count:>5} ({pct:.1f}%)")

    print(f"\nTotal entries analyzed: {total}")

if __name__ == "__main__":
    main()
