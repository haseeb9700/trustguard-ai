import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def evaluate_hallucination(question, answer, contexts):
    context_text = "\n\n".join([c["text"] for c in contexts])

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
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a strict AI governance evaluator."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content