import json
import hashlib
from tqdm import tqdm

INPUT_PATH = "./dataset/fivem_dataset.jsonl"
OUTPUT_PATH = "./dataset/fivem_dataset_deduped.jsonl"

def hash_entry(entry):
    """Create a unique fingerprint for the entry content."""
    key = (entry.get("prompt", "") + entry.get("completion", "")).strip().lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

def is_valid(entry):
    """Filter out broken or low-quality entries."""
    text = (entry.get("completion") or "").strip()
    return (
        len(text) > 100 and not text.startswith("[Error") and
        "exit status 2" not in text and
        "llama runner process" not in text
    )

def main():
    seen = set()
    kept = 0
    dropped = 0

    with open(INPUT_PATH, "r", encoding="utf-8") as infile, \
         open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:
        for line in tqdm(infile, desc="Deduplicating dataset"):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                dropped += 1
                continue

            if not is_valid(entry):
                dropped += 1
                continue

            fingerprint = hash_entry(entry)
            if fingerprint in seen:
                dropped += 1
                continue

            seen.add(fingerprint)
            json.dump(entry, outfile, ensure_ascii=False)
            outfile.write("\n")
            kept += 1

    print(f"✅ Deduplication complete: {kept} kept, {dropped} dropped")

if __name__ == "__main__":
    main()
