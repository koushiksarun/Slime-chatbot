"""
Feedback Dataset Exporter — Step 1 of the RLHF pipeline.

Exports admin-approved feedback from PostgreSQL into JSONL format
compatible with OpenAI fine-tuning API and HuggingFace Trainer.

Usage:
    python ml/feedback/export_dataset.py --output data/feedback_dataset.jsonl
    python ml/feedback/export_dataset.py --format hf --output data/hf_dataset

This script NEVER touches model weights — it only exports training data.
Human review (admin approval) has already happened before this runs.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session


def export_openai_format(rows: list[dict], output_path: str):
    """
    OpenAI fine-tuning format:
    {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

    Positive feedback (thumbs_up) → include as-is.
    Negative feedback (thumbs_down) → these are examples of what NOT to do.
    For DPO (Direct Preference Optimization), we need pairs.
    This export creates supervised fine-tuning data from positive examples only.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            if row["rating"] != "thumbs_up":
                continue
            if not row["prompt_snapshot"] or not row["response_snapshot"]:
                continue

            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful, accurate, and thoughtful AI assistant.",
                    },
                    {"role": "user", "content": row["prompt_snapshot"]},
                    {"role": "assistant", "content": row["response_snapshot"]},
                ]
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            count += 1

    print(f"Exported {count} positive examples to {output_path}")
    return count


def export_dpo_format(rows: list[dict], output_path: str):
    """
    DPO (Direct Preference Optimization) format for preference learning.
    Each entry needs a prompt + chosen (positive) + rejected (negative) response.

    This is a simplified pairing — in production, pair on the same prompt.
    Requires at least one positive AND one negative example per prompt.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Group by prompt
    by_prompt: dict[str, dict] = {}
    for row in rows:
        prompt = row.get("prompt_snapshot", "")
        if not prompt:
            continue
        if prompt not in by_prompt:
            by_prompt[prompt] = {"chosen": None, "rejected": None}
        if row["rating"] == "thumbs_up" and not by_prompt[prompt]["chosen"]:
            by_prompt[prompt]["chosen"] = row["response_snapshot"]
        elif row["rating"] == "thumbs_down" and not by_prompt[prompt]["rejected"]:
            by_prompt[prompt]["rejected"] = row["response_snapshot"]

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for prompt, pair in by_prompt.items():
            if pair["chosen"] and pair["rejected"]:
                f.write(json.dumps({
                    "prompt": prompt,
                    "chosen": pair["chosen"],
                    "rejected": pair["rejected"],
                }, ensure_ascii=False) + "\n")
                count += 1

    print(f"Exported {count} DPO preference pairs to {output_path}")
    return count


def load_approved_feedback(db_url: str) -> list[dict]:
    engine = create_engine(db_url.replace("+asyncpg", ""))
    with Session(engine) as session:
        result = session.execute(text("""
            SELECT
                f.rating,
                f.prompt_snapshot,
                f.response_snapshot,
                f.comment,
                f.created_at,
                u.email as user_email
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            WHERE f.status = 'approved'
            ORDER BY f.created_at DESC
        """))
        rows = [dict(r._mapping) for r in result]
    print(f"Loaded {len(rows)} approved feedback records")
    return rows


def main():
    parser = argparse.ArgumentParser(description="Export feedback dataset for fine-tuning")
    parser.add_argument("--output", default="ml/data/feedback_dataset.jsonl")
    parser.add_argument("--format", choices=["openai", "dpo"], default="openai",
                        help="openai=SFT format, dpo=preference pairs")
    parser.add_argument("--db-url", default=os.environ.get(
        "DATABASE_URL_SYNC", "postgresql://chatbot:chatbot@localhost:5432/chatbot_db"
    ))
    args = parser.parse_args()

    rows = load_approved_feedback(args.db_url)
    if not rows:
        print("No approved feedback found. Run admin review first.")
        return

    if args.format == "openai":
        export_openai_format(rows, args.output)
    elif args.format == "dpo":
        export_dpo_format(rows, args.output)

    print(f"\nDataset ready: {args.output}")
    print("Next step: python ml/fine_tuning/fine_tune_openai.py --dataset", args.output)


if __name__ == "__main__":
    main()
