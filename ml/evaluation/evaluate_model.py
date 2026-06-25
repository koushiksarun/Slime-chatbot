"""
Model Evaluation Script — Step 3 of RLHF pipeline.

Evaluates a fine-tuned model against a held-out test set using:
  - BLEU score (n-gram precision)
  - ROUGE-L (longest common subsequence)
  - LLM-as-Judge (GPT-4o scores quality 1-10)
  - Latency measurements

Usage:
    python ml/evaluation/evaluate_model.py \
        --model ft:gpt-4o-mini-2024-07-18:org:chatbot-v1:abc123 \
        --test-set ml/data/test_set.jsonl \
        --baseline gpt-4o-mini
"""
import argparse
import json
import os
import time
import statistics
from pathlib import Path
from typing import Optional


def bleu_score(reference: str, hypothesis: str) -> float:
    """Sentence-level BLEU-4 (simplified)."""
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    import nltk
    try:
        ref_tokens = reference.lower().split()
        hyp_tokens = hypothesis.lower().split()
        smoothing = SmoothingFunction().method1
        return sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smoothing)
    except Exception:
        return 0.0


def rouge_l_score(reference: str, hypothesis: str) -> float:
    """ROUGE-L F1 score."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref or not hyp:
        return 0.0

    # LCS dynamic programming
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]

    precision = lcs / n if n > 0 else 0
    recall = lcs / m if m > 0 else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def llm_judge(prompt: str, response: str, client) -> int:
    """Use GPT-4o as judge to score response quality 1-10."""
    judge_prompt = f"""Rate the following AI assistant response on a scale of 1-10.
Consider: accuracy, helpfulness, clarity, and completeness.

User prompt: {prompt[:500]}

AI response: {response[:500]}

Score (1-10, reply with only the number):"""

    try:
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": judge_prompt}],
            max_tokens=5,
            temperature=0,
        )
        score = int(result.choices[0].message.content.strip())
        return max(1, min(10, score))
    except Exception:
        return 5  # Neutral on failure


def evaluate(model: str, test_set_path: str, baseline_model: Optional[str], use_llm_judge: bool):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Load test set
    test_examples = []
    with open(test_set_path) as f:
        for line in f:
            ex = json.loads(line)
            messages = ex.get("messages", [])
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
            ref_response = next((m["content"] for m in messages if m["role"] == "assistant"), None)
            if user_msg and ref_response:
                test_examples.append({"prompt": user_msg, "reference": ref_response})

    if not test_examples:
        print("No valid test examples found")
        return

    print(f"Evaluating {model} on {len(test_examples)} examples...")
    if baseline_model:
        print(f"Baseline: {baseline_model}")

    results = {"model": [], "baseline": []}
    models_to_eval = [("model", model)]
    if baseline_model:
        models_to_eval.append(("baseline", baseline_model))

    for key, model_id in models_to_eval:
        bleus, rouges, judges, latencies = [], [], [], []

        for ex in test_examples:
            start = time.time()
            try:
                resp = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": ex["prompt"]},
                    ],
                    max_tokens=512,
                    temperature=0.2,
                )
                generated = resp.choices[0].message.content
                latency = time.time() - start
            except Exception as e:
                print(f"  Error: {e}")
                continue

            bleus.append(bleu_score(ex["reference"], generated))
            rouges.append(rouge_l_score(ex["reference"], generated))
            latencies.append(latency)
            if use_llm_judge:
                judges.append(llm_judge(ex["prompt"], generated, client))

        results[key] = {
            "bleu_avg": round(statistics.mean(bleus), 4) if bleus else 0,
            "rouge_l_avg": round(statistics.mean(rouges), 4) if rouges else 0,
            "llm_judge_avg": round(statistics.mean(judges), 2) if judges else None,
            "avg_latency_s": round(statistics.mean(latencies), 2) if latencies else 0,
            "samples_evaluated": len(bleus),
        }

    # Print report
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    for key, data in results.items():
        if not data:
            continue
        label = model if key == "model" else baseline_model
        print(f"\n{label}")
        print(f"  BLEU-4:        {data['bleu_avg']:.4f}")
        print(f"  ROUGE-L:       {data['rouge_l_avg']:.4f}")
        if data.get("llm_judge_avg"):
            print(f"  LLM Judge:     {data['llm_judge_avg']:.1f}/10")
        print(f"  Avg Latency:   {data['avg_latency_s']:.2f}s")
        print(f"  Samples:       {data['samples_evaluated']}")

    # Save results
    out_path = Path("ml/data/evaluation_results.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a") as f:
        f.write(json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": model,
            "baseline": baseline_model,
            "results": results,
        }) + "\n")
    print(f"\nResults saved to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Model ID to evaluate")
    parser.add_argument("--test-set", required=True, help="Path to JSONL test set")
    parser.add_argument("--baseline", help="Baseline model to compare against")
    parser.add_argument("--no-llm-judge", action="store_true",
                        help="Skip LLM-as-judge evaluation (saves API cost)")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not set")

    evaluate(
        model=args.model,
        test_set_path=args.test_set,
        baseline_model=args.baseline,
        use_llm_judge=not args.no_llm_judge,
    )


if __name__ == "__main__":
    main()
