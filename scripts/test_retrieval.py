import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = "data/chroma_db"
COLLECTION_NAME = "uscis_policy_docs"

def retrieve(query, top_k=3):
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    query_embedding = model.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results

if __name__ == "__main__":
    query = "How many unemployment days are allowed during post-completion OPT?"

    results = retrieve(query)

    for i, doc in enumerate(results["documents"][0]):
        print("\n" + "=" * 80)
        print(f"RESULT {i + 1}")
        print("=" * 80)
        print(doc[:1000])
        print("\nSOURCE:")
        print(results["metadatas"][0][i]["source_title"])
        print(results["metadatas"][0][i]["source_url"])