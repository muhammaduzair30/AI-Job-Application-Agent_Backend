import hashlib
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
    # Compute the full document embedding for matching
    full_embeddings = await embedding_model.aembed_documents([text])
    full_embedding = full_embeddings[0] if full_embeddings else []
    
    chunks = text_splitter.split_text(text)
    texts_to_embed = [chunk for chunk in chunks if chunk.strip()]

    vectors = []
    
    if full_embedding:
        vectors.append({
            "id": f"{doc_id}#full",
            "values": full_embedding,
            "metadata": {**metadata, "type": "full_document"}
        })

    if texts_to_embed:
        embeddings = await embedding_model.aembed_documents(texts_to_embed)
        vectors.extend([
            {
                "id": f"{doc_id}#{i}",
                "values": embedding,
                "metadata": {**metadata, "chunk_index": i, "text": chunk},
            }
            for i, (chunk, embedding) in enumerate(zip(texts_to_embed, embeddings))
        ])

    if not vectors:
        return

    for batch_start in range(0, len(vectors), 100):
        batch = vectors[batch_start : batch_start + 100]
        index.upsert(vectors=batch)


def fetch_vector(vector_id: str) -> list[float] | None:
    response = index.fetch(ids=[vector_id])
    
    # Handle both dict and object responses depending on Pinecone client version
    vectors = response.get("vectors", {}) if isinstance(response, dict) else getattr(response, "vectors", {})
    if vector_id in vectors:
        vector_data = vectors[vector_id]
        return vector_data.get("values") if isinstance(vector_data, dict) else getattr(vector_data, "values")
        
    return None


async def get_or_create_jd_embedding(jd_text: str) -> list[float]:
    # Hash jd_text to use as a unique ID for caching
    jd_hash = hashlib.sha256(jd_text.encode('utf-8')).hexdigest()
    vector_id = f"jd_{jd_hash}#full"
    
    # Check if already embedded
    existing_vector = fetch_vector(vector_id)
    if existing_vector:
        return existing_vector
        
    # Generate new embedding
    embeddings = await embedding_model.aembed_documents([jd_text])
    if not embeddings:
        return []
        
    embedding = embeddings[0]
    
    # Store
    index.upsert(vectors=[{
        "id": vector_id,
        "values": embedding,
        "metadata": {"type": "jd_full"}
    }])
    
    return embedding


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
    
    all_ids = [f"{prefix}full"]
    for i in range(1000):
        all_ids.append(f"{prefix}{i}")

    index.delete(ids=all_ids)
