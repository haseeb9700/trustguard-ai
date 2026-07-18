"""Trick-question generation — creates demo questions from ingested content.

After a source is ingested, we generate questions that SOUND related to the
source but cannot be answered from it. Running them lets users watch the
hallucination detection and risk flagging fire in real time.
"""

import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("trustguard.trick_questions")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GENERATION_MODEL = "gpt-4o-mini"

MAX_CONTEXT_CHARS = 6000


def generate_trick_questions(chunks: list, source_title: str, n: int = 3) -> list:
    """Generate unanswerable-but-plausible questions for an ingested source.

    Args:
        chunks: The text chunks that were just ingested.
        source_title: Title of the ingested source.
        n: Number of questions to generate.

    Returns:
        A list of question strings, or an empty list on failure — trick
        questions are a demo aid and must never break ingestion.
    """
    sample_text = "\n\n".join(chunks[:4])[:MAX_CONTEXT_CHARS]

    prompt = f"""
Below is content from a document titled "{source_title}".

Write exactly {n} short questions that:
- Sound directly related to this document's topic
- CANNOT be answered from the content below (they ask about details,
  numbers, dates, people, or sections the content does not mention)
- Are realistic questions a user might actually ask

These are used to demonstrate a hallucination-detection system: a good
answer engine must refuse or flag them instead of making something up.

CONTENT:
{sample_text}

Return STRICT JSON only — a list of question strings:
["question 1", "question 2", "question 3"]
"""

    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You write topic-relevant but unanswerable test questions.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.4,
        )

        raw = response.choices[0].message.content
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        parsed = json.loads(cleaned)

        if isinstance(parsed, list):
            return [str(q) for q in parsed if isinstance(q, str) and q.strip()][:n]

    except Exception:
        logger.exception("Trick-question generation failed.")

    return []
