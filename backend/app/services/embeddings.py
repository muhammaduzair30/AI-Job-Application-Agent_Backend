from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

from app.config import settings

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(settings.PINECONE_INDEX_NAME)

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.GEMINI_API_KEY,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


async def embed_and_store(text: str, doc_id: str, metadata: dict) -> None:
    chunks = text_splitter.split_text(text)
    texts_to_embed = [chunk for chunk in chunks if chunk.strip()]

    if not texts_to_embed:
        return

    embeddings = await embedding_model.aembed_documents(texts_to_embed)

    vectors = [
        {
            "id": f"{doc_id}#{i}",
            "values": embedding,
            "metadata": {**metadata, "chunk_index": i, "text": chunk},
        }
        for i, (chunk, embedding) in enumerate(zip(texts_to_embed, embeddings))
    ]

    for batch_start in range(0, len(vectors), 100):
        batch = vectors[batch_start : batch_start + 100]
        index.upsert(vectors=batch)


async def search_similar(query: str, top_k: int = 10) -> list[dict]:
    query_embedding = await embedding_model.aembed_query(query)

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )

    return [
        {"id": match["id"], "score": match["score"], "metadata": match.get("metadata", {})}
        for match in results["matches"]
    ]


async def delete_vectors(doc_id: str) -> None:
    prefix = f"{doc_id}#"
    index.delete(filter={}, ids=[])  # fallback

    all_ids = []
    for i in range(1000):
        candidate = f"{prefix}{i}"
        all_ids.append(candidate)

    index.delete(ids=all_ids)
