"""Query rewrite agent — reformulates user questions for better retrieval."""

import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

REWRITE_MODEL = "gpt-4o-mini"
TRAINING_FILE = "data/query_rewrite_training.csv"


def get_examples(limit: int = 5) -> str:
    """Load few-shot rewrite examples from the training file, if present."""
    if not os.path.exists(TRAINING_FILE):
        return ""

    df = pd.read_csv(TRAINING_FILE)

    if df.empty:
        return ""

    sample = df.sample(min(limit, len(df)), random_state=42)

    examples = [
        f"Raw: {row['raw_user_query']}\nRewrite: {row['rewritten_query']}"
        for _, row in sample.iterrows()
    ]

    return "\n\n".join(examples)


def run_query_rewrite_agent(user_query: str) -> str:
    """Rewrite a user question into a precise, retrieval-friendly query.

    Args:
        user_query: The raw user question.

    Returns:
        The rewritten search query.
    """
    examples = get_examples()

    prompt = f"""
You are a query rewriting agent for a policy-compliance RAG system.

Your job:
Rewrite the user question into a precise, retrieval-friendly search query.

Rules:
- Do not answer the question.
- Preserve the original intent.
- Expand vague or casual language into formal policy terminology.
- Keep it short and searchable.

TRAINING EXAMPLES:
{examples}

USER QUESTION:
{user_query}

Return only the rewritten query.
"""

    response = client.chat.completions.create(
        model=REWRITE_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You rewrite user questions for semantic retrieval.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
