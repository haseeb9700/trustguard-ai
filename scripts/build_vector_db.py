import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = "data/rag_chunks.csv"
DB_PATH = "data/chroma_db"
COLLECTION_NAME = "uscis_policy_docs"


def main():
    df = pd.read_csv(CHUNKS_FILE)

    df = df.dropna(subset=["chunk_text"])
    df["chunk_text"] = df["chunk_text"].astype(str)
    df = df[df["chunk_text"].str.strip().str.len() > 50]

    print(f"Valid chunks found: {len(df)}")

    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    client = chromadb.PersistentClient(path=DB_PATH)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    documents = df["chunk_text"].tolist()
    ids = df["chunk_id"].astype(str).tolist()

    metadatas = []

    for _, row in df.iterrows():
        metadatas.append({
            "source_title": str(row["source_title"]),
            "source_url": str(row["source_url"]),
            "chunk_index": int(row["chunk_index"])
        })

    embeddings = model.encode(
        documents,
        batch_size=32,
        show_progress_bar=True
    ).tolist()

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"Added {len(documents)} chunks to ChromaDB")
    print(f"Vector database saved at {DB_PATH}")


if __name__ == "__main__":
    main()