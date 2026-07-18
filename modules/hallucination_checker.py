"""LLM-based hallucination evaluation for generated answers."""

import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("trustguard.hallucination")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EVALUATION_MODEL = "gpt-4o-mini"


def _parse_evaluation(raw: str) -> dict:
    """Parse the evaluator's response into a dict, tolerating code fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        logger.warning("Evaluator returned non-JSON output; passing through raw text.")

    return {"hallucination_score": None, "reason": raw.strip()}


def evaluate_hallucination(question: str, answer: str, contexts: list) -> dict:
    """Score how well an answer is grounded in the retrieved context.

    Args:
        question: The original user question.
        answer: The generated answer to evaluate.
        contexts: Retrieved context chunks (each with a "text" key).

    Returns:
        A dict with "hallucination_score" (0 = fully grounded,
        1 = partially unsupported, 2 = major hallucination) and "reason".
    """
    context_text = "\n\n".join(c["text"] for c in contexts)

    prompt = f"""
You are an enterprise AI governance evaluator.

Your task is to determine whether the AI answer is fully supported by the retrieved context.

QUESTION:
{question}

AI ANSWER:
{answer}

RETRIEVED CONTEXT:
{context_text}

Evaluate the answer using these rules:

0 = Fully grounded in the context
1 = Partially unsupported / minor hallucination
2 = Major hallucination or unsupported claims

Return STRICT JSON only in this format:

{{
    "hallucination_score": 0,
    "reason": "short explanation"
}}
"""

    response = client.chat.completions.create(
        model=EVALUATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a strict AI governance evaluator.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return _parse_evaluation(response.choices[0].message.content)
