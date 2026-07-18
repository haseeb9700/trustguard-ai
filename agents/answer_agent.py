"""Answer agent — generates a source-grounded answer from retrieved context."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ANSWER_MODEL = "gpt-4o-mini"


def run_answer_agent(query: str, contexts: list) -> str:
    """Generate an answer strictly grounded in the retrieved context.

    Args:
        query: The user's original question.
        contexts: Retrieved chunks, each with "source_title" and "text".

    Returns:
        The generated answer text.
    """
    context_text = "\n\n".join(
        f"Source: {c['source_title']}\nText: {c['text']}" for c in contexts
    )

    prompt = f"""
You are a careful policy-compliance AI assistant.

Answer only using the provided trusted context.

Rules:
- Do not guess.
- If the answer is not supported by context, say:
  "I could not verify this from the provided sources."
- Keep the answer factual, concise, and source-grounded.

USER QUESTION:
{query}

TRUSTED CONTEXT:
{context_text}
"""

    response = client.chat.completions.create(
        model=ANSWER_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a careful enterprise policy reasoning agent.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content
