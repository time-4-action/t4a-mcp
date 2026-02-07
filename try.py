from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
import os

load_dotenv()

# Load the existing vector store
# IMPORTANT: Must use the same embedding model as when creating the vectorstore
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
)

vectorstore = Chroma(
    collection_name="products",
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

# Check database stats
print(f"📊 Total documents in vectorstore: {vectorstore._collection.count()}\n")

# Search with scores to evaluate match quality
query = "patrik f-race board that has 100l volume"
print(f"🔍 Searching for: '{query}'")
print("=" * 100)

docs_with_scores = vectorstore.similarity_search_with_score(query, k=5)

for i, (doc, score) in enumerate(docs_with_scores, 1):
    print(f"\n🏆 Result #{i} | Score: {score:.4f} (lower = better)")
    print(f"📦 Product: {doc.metadata.get('product_name', 'N/A')}")
    print(f"🔢 Code: {doc.metadata.get('code', 'N/A')}")
    print(f"📊 EAN: {doc.metadata.get('ean', 'N/A')}")
    # print(f"\n📝 Full content:")
    # print(f"   {doc.page_content}")
    print("-" * 100)

# # Try more specific searches
# print("\n\n🔄 Alternative searches:\n")

# alternative_queries = [
#     "Patrik Air Style 93 l",
#     "93 liter paddleboard",
#     "Air Style SUP"
# ]

# for alt_query in alternative_queries:
#     print(f"🔍 '{alt_query}'")
#     results = vectorstore.similarity_search_with_score(alt_query, k=3)
#     for i, (doc, score) in enumerate(results[:3], 1):
#         print(f"   {i}. {doc.metadata.get('product_name')} (score: {score:.4f})")
#     print()