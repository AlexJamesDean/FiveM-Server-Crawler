import json

src = "fivem_dataset_deduped.jsonl"
out = "fivem_dataset_lora.jsonl"

with open(src, "r", encoding="utf-8") as f, open(out, "w", encoding="utf-8") as o:
    for line in f:
        ex = json.loads(line)
        prompt = ex.get("prompt", "").strip()
        completion = ex.get("completion", "").strip()
        if not prompt or not completion:
            continue
        record = {
            "instruction": "Explain, analyze, or answer this FiveM code segment.",
            "input": prompt,
            "output": completion
        }
        o.write(json.dumps(record, ensure_ascii=False) + "\n")

print("✅ dataset ready:", out)
