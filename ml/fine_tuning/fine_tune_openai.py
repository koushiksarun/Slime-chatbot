"""
OpenAI Fine-Tuning Script — Step 2 of RLHF pipeline.

Uploads a JSONL dataset to OpenAI and starts a fine-tuning job.
Polls for completion and saves the resulting model ID.

Usage:
    python ml/fine_tuning/fine_tune_openai.py \
        --dataset ml/data/feedback_dataset.jsonl \
        --base-model gpt-4o-mini-2024-07-18 \
        --suffix chatbot-v1

Prerequisites:
    - At least 10 training examples in the JSONL file
    - OPENAI_API_KEY env var set
    - python ml/feedback/export_dataset.py has already been run
"""
import argparse
import json
import os
import time
from pathlib import Path


def validate_dataset(path: str) -> int:
    count = 0
    with open(path, "r") as f:
        for i, line in enumerate(f):
            try:
                ex = json.loads(line)
                messages = ex.get("messages", [])
                roles = [m["role"] for m in messages]
                assert "user" in roles and "assistant" in roles, f"Line {i+1}: missing user/assistant"
                count += 1
            except (json.JSONDecodeError, AssertionError) as e:
                print(f"[WARN] Line {i+1}: {e}")
    return count


def run_fine_tuning(dataset_path: str, base_model: str, suffix: str):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Validate
    print(f"Validating dataset: {dataset_path}")
    count = validate_dataset(dataset_path)
    if count < 10:
        raise ValueError(f"Need at least 10 valid examples, got {count}")
    print(f"  {count} valid examples")

    # Upload file
    print("Uploading training file to OpenAI...")
    with open(dataset_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="fine-tune")
    print(f"  File ID: {file_obj.id}")

    # Start fine-tune job
    print(f"Starting fine-tuning job (base: {base_model})...")
    job = client.fine_tuning.jobs.create(
        training_file=file_obj.id,
        model=base_model,
        suffix=suffix,
        hyperparameters={
            "n_epochs": "auto",
            "batch_size": "auto",
            "learning_rate_multiplier": "auto",
        },
    )
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")

    # Poll for completion
    print("\nPolling for completion (this may take 10-60 minutes)...")
    while job.status not in ("succeeded", "failed", "cancelled"):
        time.sleep(60)
        job = client.fine_tuning.jobs.retrieve(job.id)

        # Print latest events
        events = client.fine_tuning.jobs.list_events(job.id, limit=5)
        for event in reversed(events.data):
            print(f"  [{event.created_at}] {event.message}")

        print(f"  Status: {job.status}")

    if job.status == "succeeded":
        model_id = job.fine_tuned_model
        print(f"\nFine-tuning complete!")
        print(f"  Fine-tuned model: {model_id}")

        # Save model ID to file
        output = {
            "model_id": model_id,
            "base_model": base_model,
            "job_id": job.id,
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "training_examples": count,
        }
        out_path = Path("ml/data/fine_tuned_models.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(json.dumps(output) + "\n")
        print(f"\nModel ID saved to {out_path}")
        print(f"\nTo deploy: set OPENAI_MODEL={model_id} in your .env and restart the backend")
    else:
        print(f"\nFine-tuning failed: {job.status}")
        raise RuntimeError(f"Job {job.id} failed with status: {job.status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--base-model", default="gpt-4o-mini-2024-07-18")
    parser.add_argument("--suffix", default="chatbot-ft")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not set")

    run_fine_tuning(args.dataset, args.base_model, args.suffix)


if __name__ == "__main__":
    main()
