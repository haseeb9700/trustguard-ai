import pandas as pd
import uuid
import os

INPUT_FILE = "data/raw_sources.csv"
OUTPUT_FILE = "data/rag_chunks.csv"

def chunk_text(text, chunk_size=800, overlap=150):
    words = str(text).split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks

def main():
    os.makedirs("data", exist_ok=True)

    df = pd.read_csv(INPUT_FILE)
    rows = []

    for _, row in df.iterrows():
        chunks = chunk_text(row["raw_text"], chunk_size=400, overlap=80)

        for i, chunk in enumerate(chunks):
            rows.append({
                "chunk_id": str(uuid.uuid4()),
                "source_title": row["source_title"],
                "source_url": row["source_url"],
                "chunk_index": i,
                "chunk_text": chunk
            })

    chunk_df = pd.DataFrame(rows)
    chunk_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Created {len(chunk_df)} chunks")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()