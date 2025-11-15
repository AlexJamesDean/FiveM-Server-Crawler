# === Windows BitsAndBytes Nuker (final form) ===
import sys, types, importlib.machinery
fake_bnb = types.ModuleType("bitsandbytes")
fake_bnb.__spec__ = importlib.machinery.ModuleSpec("bitsandbytes", loader=None)
fake_bnb.nn = types.SimpleNamespace(Linear8bitLt=None)
fake_bnb.functional = None
fake_bnb.__version__ = "0.0.0-fake"
sys.modules["bitsandbytes"] = fake_bnb


import os
os.environ["PEFT_BACKEND"] = "TORCH"  # extra safety

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

# === CONFIG ===
model_id = "meta-llama/Llama-3.2-3B"
dataset_path = "fivem_dataset_lora.jsonl"
output_dir = "./lora-finetuned-fivem"

# === LOAD DATA ===
dataset = load_dataset("json", data_files=dataset_path, split="train")

tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.pad_token = tokenizer.eos_token

def format(example):
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output_text = example.get("output", "")
    text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output_text}"

    tokens = tokenizer(
        text,
        truncation=True,
        max_length=2048,
        padding="max_length",
        return_tensors="pt",  # <-- important: ensures actual torch tensors
    )

    # Flatten single batch dimension if necessary
    for k in tokens:
        tokens[k] = tokens[k].squeeze(0)

    tokens["labels"] = tokens["input_ids"].clone()
    return tokens

tokenized = dataset.map(format, remove_columns=dataset.column_names)

# === LOAD MODEL (no bitsandbytes) ===
# === LOAD MODEL THEN APPLY LORA BEFORE DEVICE SPLIT ===
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    device_map=None  # stay on CPU during LoRA injection
)

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],  # typical for LLaMA-based models
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)

# Ensure LoRA params require grad
for name, param in model.named_parameters():
    if param.requires_grad:
        param.requires_grad_(True)

model.print_trainable_parameters()

model = get_peft_model(model, lora_config)
print("Trainable parameters:", sum(p.numel() for p in model.parameters() if p.requires_grad))

# === TRAINING ARGS ===
args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=2,
    learning_rate=2e-4,
    fp16=True,
    gradient_checkpointing=True,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized
)

trainer.train()
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
