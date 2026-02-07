"""Main script for generating and using the product vectorstore."""

from ingestion.loader import get_products
from ingestion.flattener import flatten_products
from ingestion.cleaner import clean_products
from ingestion.embedding_formatter import create_embeddings_text
from embeddings.generator import generate_vectorstore, load_vectorstore


def main():
    """Run the complete pipeline to create a vectorstore."""
    print("🚀 Starting product vectorstore generation...")
    print("=" * 60)

    # Step 1: Load products from data source
    print("\n📥 Step 1: Loading products...")
    products = get_products()
    print(f"   ✓ Loaded {len(products)} products")

    # Step 2: Flatten nested product structures
    print("\n🔄 Step 2: Flattening products...")
    flat = flatten_products(products)
    print(f"   ✓ Flattened to {len(flat)} items")

    # Step 3: Clean HTML and format data
    print("\n🧹 Step 3: Cleaning products...")
    clean = clean_products(flat)
    print(f"   ✓ Cleaned {len(clean)} items")

    # Step 4: Create embedding-ready texts
    print("\n📝 Step 4: Creating embedding texts...")
    embedding_texts = create_embeddings_text(clean)
    print(f"   ✓ Created {len(embedding_texts)} embedding texts")

    # Step 5: Generate vectorstore with embeddings
    print("\n🔮 Step 5: Generating vectorstore...")
    print("   This will use OpenAI API to create embeddings...")
    vectorstore = generate_vectorstore(
        products=clean,
        embedding_texts=embedding_texts,
        persist_directory="./chroma_db",
        collection_name="products"
    )

    print("\n" + "=" * 60)
    print("✅ Vectorstore generation complete!")
    print("\n💡 Next steps:")
    print("   1. Use vectorstore.similarity_search(query, k=5) to search")
    print("   2. Load existing vectorstore with load_vectorstore()")
    print("   3. Build a RAG application using this vectorstore")

    return vectorstore


if __name__ == "__main__":
    # Generate the vectorstore
    vectorstore = main()

    # Example: Test a query
    print("\n" + "=" * 60)
    print("🔍 Testing similarity search...")
    query = "inflatable paddle board for beginners"
    results = vectorstore.similarity_search(query, k=3)

    print(f"\nQuery: '{query}'")
    print(f"Top {len(results)} results:\n")

    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc.metadata['product_name']}")
        print(f"   Code: {doc.metadata['code']}")
        print(f"   Categories: {', '.join(doc.metadata.get('categories', []))}")
        print(f"   Stock: {doc.metadata.get('stock_amount', 0)}")
        print(f"   Preview: {doc.page_content[:150]}...")
        print()