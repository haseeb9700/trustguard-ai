import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INPUT_FILE = "data/rag_chunks.csv"
OUTPUT_FILE = "data/query_rewrite_training.csv"


def generate_examples(chunk_text, source_title, source_url):
    prompt = f"""
You are creating training data for a query rewriting model.

Given the policy/context text below, generate query rewrite training examples.

For each example:
- raw_user_query should be casual, vague, slang, broken English, or user-like
- rewritten_query should be formal, precise, retrieval-friendly, and policy-focused
- Keep rewritten_query short and searchable
- Focus on immigration, compliance, AI governance, risk, policy, or employment rules if relevant

Return STRICT JSON only as a list of objects.

Each object must have:
{{
  "raw_user_query": "...",
  "rewritten_query": "..."
}}

Generate 5 examples.

SOURCE TITLE:
{source_title}

SOURCE URL:
{source_url}

TEXT:
{chunk_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate high-quality query rewriting training data.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        return []


def main():
    df = pd.read_csv(INPUT_FILE)

    df = df.dropna(subset=["chunk_text"])
    df["chunk_text"] = df["chunk_text"].astype(str)

    rows = []

    # Use only first 50 chunks initially to control API cost
    sample_df = df.head(50)

    for index, row in sample_df.iterrows():
        print(f"Generating examples for chunk {index + 1}/{len(sample_df)}")

        examples = generate_examples(
            row["chunk_text"],
            row.get("source_title", "No Title"),
            row.get("source_url", ""),
        )

        for ex in examples:
            rows.append(
                {
                    "raw_user_query": ex.get("raw_user_query", ""),
                    "rewritten_query": ex.get("rewritten_query", ""),
                    "domain": "policy_compliance",
                    "source_title": row.get("source_title", "No Title"),
                    "source_url": row.get("source_url", ""),
                }
            )

    output_df = pd.DataFrame(rows)
    output_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved {len(output_df)} training examples to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
