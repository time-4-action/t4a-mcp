import os
import re
import requests
from html import unescape
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()

# ============================================
# PHASE 1: Data Collection - Fetch from API
# ============================================

def fetch_products(api_url: str) -> list:
    """Fetch products from the API."""
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()
    return data.get("data", [])


# ============================================
# PHASE 2: Data Processing
# ============================================

def strip_html(html_text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not html_text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_text)
    # Decode HTML entities
    text = unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_price(pricelist: list) -> str:
    """Format price information into readable text."""
    if not pricelist:
        return "Price on request"

    prices = []
    for p in pricelist:
        price_str = f"{p.get('name', 'Price')}: €{p.get('price', 0):.2f}"
        if p.get('vat'):
            price_str += f" (VAT {p['vat']}%)"
        prices.append(price_str)
    return " | ".join(prices)


def product_to_document(product: dict) -> list[Document]:
    """
    Convert a product into documents using hierarchical approach:
    - Summary doc (small, optimized for retrieval)
    - Detail doc (full context, returned to user)
    - Variant docs (each variant as separate searchable unit)

    This implements "retrieve small, return large" pattern.
    """
    documents = []

    # Extract parent product info
    product_name = product.get("product_name", "Unknown Product")
    product_code = product.get("code", "")
    short_desc = strip_html(product.get("short_description", ""))
    detailed_desc = strip_html(product.get("detailed_description", ""))
    categories = [cat.get("categoryName", "") for cat in product.get("ai_categories", [])]
    category_str = ", ".join(categories) if categories else "Uncategorized"

    # Extract variant info for summary
    variants = product.get("child_products", [])
    variant_names = [v.get("product_name", "") for v in variants]
    variant_summary = ", ".join(variant_names) if variant_names else "No variants"

    # Price range from variants
    all_prices = []
    for v in variants:
        for p in v.get("pricelist", []):
            if p.get("price"):
                all_prices.append(p["price"])
    price_range = f"€{min(all_prices):.0f} - €{max(all_prices):.0f}" if all_prices else "Price on request"

    # Stock status
    total_stock = sum(v.get("stock_amount", 0) for v in variants)
    in_stock_variants = [v for v in variants if v.get("stock_amount", 0) > 0]

    # ==========================================
    # DOC 1: Summary (optimized for retrieval)
    # ==========================================
    summary_content = f"""{product_name} - {category_str}
{short_desc}
Variants: {variant_summary}
Price: {price_range}
Stock: {len(in_stock_variants)}/{len(variants)} variants available"""

    summary_metadata = {
        "doc_type": "summary",
        "product_code": product_code,
        "product_name": product_name,
        "categories": category_str,
        "price_range": price_range,
        "total_stock": total_stock,
        "variant_count": len(variants),
        "is_new": product.get("new", False),
    }

    documents.append(Document(page_content=summary_content, metadata=summary_metadata))

    # ==========================================
    # DOC 2: Full detail (returned for context)
    # ==========================================
    detail_content = f"""# {product_name}
Category: {category_str}
Product Code: {product_code}

## Summary
{short_desc}

## Description
{detailed_desc}

## Available Variants
"""
    for v in variants:
        v_name = v.get("product_name", "")
        v_price = format_price(v.get("pricelist", []))
        v_stock = v.get("stock_amount", 0)
        v_ean = v.get("ean_code", "")
        status = "✓ In Stock" if v_stock > 0 else "✗ Out of Stock"
        detail_content += f"\n• {v_name}\n  Code: {v.get('code', '')} | EAN: {v_ean}\n  Price: {v_price}\n  {status} ({v_stock} units)\n"

    detail_metadata = {
        "doc_type": "detail",
        "product_code": product_code,
        "product_name": product_name,
        "categories": category_str,
        "is_new": product.get("new", False),
    }

    documents.append(Document(page_content=detail_content, metadata=detail_metadata))

    # ==========================================
    # DOC 3+: Individual variants (for specific searches)
    # ==========================================
    for child in variants:
        child_name = child.get("product_name", "")
        child_code = child.get("code", "")
        child_price = format_price(child.get("pricelist", []))
        stock = child.get("stock_amount", 0)
        ean = child.get("ean_code", "")

        # Compact variant doc - includes parent context
        variant_content = f"""{child_name}
Part of: {product_name} ({category_str})
Code: {child_code} | EAN: {ean}
Price: {child_price}
Stock: {stock} units {"(In Stock)" if stock > 0 else "(Out of Stock)"}
{short_desc}"""

        variant_metadata = {
            "doc_type": "variant",
            "product_code": child_code,
            "product_name": child_name,
            "parent_code": product_code,
            "parent_name": product_name,
            "ean_code": ean,
            "categories": category_str,
            "stock_amount": stock,
            "in_stock": stock > 0,
        }

        documents.append(Document(page_content=variant_content, metadata=variant_metadata))

    return documents


def process_products(products: list) -> list[Document]:
    """Process all products into documents."""
    all_documents = []
    for product in products:
        if product.get("published", True) and not product.get("archived", False):
            docs = product_to_document(product)
            all_documents.extend(docs)
    return all_documents


# ============================================
# PHASE 3: Embedding & Indexing (No Chunking)
# ============================================

def create_vector_store(documents: list[Document], persist_dir: str = "./chroma_db"):
    """Create vector store - products are atomic units, no chunking needed."""

    # Products are already semantic units - don't chunk them
    # Each product/variant is a complete, self-contained document
    print(f"Indexing {len(documents)} product documents (no chunking)")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="products"
    )

    return vector_store


def load_vector_store(persist_dir: str = "./chroma_db"):
    """Load existing vector store."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="products"
    )


# ============================================
# PHASE 4 & 5: Retrieval & Agent
# ============================================

# Global vector store (initialized later)
vector_store = None


@tool
def search_products(query: str) -> str:
    """Search the product catalog for relevant products.
    Use this to find products by name, category, description, or any product-related query.
    Returns detailed product information with variants, prices, and stock."""
    if vector_store is None:
        return "Knowledge base not initialized."

    # Step 1: Search summaries for fast retrieval (retrieve small)
    summary_results = vector_store.similarity_search(
        query,
        k=10,
        filter={"doc_type": "summary"}
    )

    if not summary_results:
        # Fallback: search all docs
        summary_results = vector_store.similarity_search(query, k=5)

    if not summary_results:
        return "No products found matching your query."

    # Step 2: Get full details for matched products (return large)
    output = []
    seen_codes = set()

    for summary_doc in summary_results[:5]:  # Top 5 matches
        product_code = summary_doc.metadata.get("product_code", "")

        if product_code in seen_codes:
            continue
        seen_codes.add(product_code)

        # Fetch the detail document for this product
        detail_results = vector_store.similarity_search(
            product_code,
            k=1,
            filter={"$and": [{"doc_type": "detail"}, {"product_code": product_code}]}
        )

        if detail_results:
            output.append(detail_results[0].page_content)
            output.append("-" * 40)
        else:
            # Fallback to summary if detail not found
            output.append(summary_doc.page_content)
            output.append("-" * 40)

    return "\n".join(output)


@tool
def get_product_by_code(code: str) -> str:
    """Get a specific product by its product code or EAN code.
    Returns full product details including all variants."""
    if vector_store is None:
        return "Knowledge base not initialized."

    # Try to find detail doc by product code
    results = vector_store.similarity_search(
        code,
        k=1,
        filter={"$and": [{"doc_type": "detail"}, {"product_code": code}]}
    )

    if results:
        return results[0].page_content

    # Try variant code
    results = vector_store.similarity_search(
        code,
        k=1,
        filter={"$and": [{"doc_type": "variant"}, {"product_code": code}]}
    )

    if results:
        # Found variant, also get parent detail
        parent_code = results[0].metadata.get("parent_code", "")
        parent_results = vector_store.similarity_search(
            parent_code,
            k=1,
            filter={"$and": [{"doc_type": "detail"}, {"product_code": parent_code}]}
        )
        if parent_results:
            return parent_results[0].page_content
        return results[0].page_content

    # Try EAN code
    results = vector_store.similarity_search(
        code,
        k=1,
        filter={"ean_code": code}
    )

    if results:
        return results[0].page_content

    return f"No product found with code: {code}"


@tool
def search_in_stock(query: str) -> str:
    """Search only for products that are currently in stock.
    Use this when the user specifically wants available products."""
    if vector_store is None:
        return "Knowledge base not initialized."

    # Search variants that are in stock
    results = vector_store.similarity_search(
        query,
        k=10,
        filter={"$and": [{"doc_type": "variant"}, {"in_stock": True}]}
    )

    if not results:
        return "No in-stock products found matching your query."

    output = ["Products currently in stock:\n"]
    for doc in results:
        output.append(doc.page_content)
        output.append("")

    return "\n".join(output)


@tool
def list_categories() -> str:
    """List all available product categories."""
    if vector_store is None:
        return "Knowledge base not initialized."

    # Get all documents and extract unique categories
    results = vector_store.similarity_search("product", k=100)
    categories = set()
    for doc in results:
        cat = doc.metadata.get("categories", "")
        if cat:
            categories.add(cat)

    return "Available categories:\n" + "\n".join(f"- {cat}" for cat in sorted(categories))


def create_product_agent():
    """Create the RAG agent with product search capabilities."""
    tools = [search_products, get_product_by_code, search_in_stock, list_categories]

    agent = create_agent(
        model="openai:gpt-4o",
        tools=tools,
        system_prompt="""You are a product assistant for a watersports equipment store. You ONLY answer questions about products in the catalog.

IMPORTANT RULES:
1. ALWAYS use a search tool before answering ANY question
2. ONLY provide information that comes from the search results
3. If a question is NOT about products (e.g., general knowledge, celebrities, etc.), say: "I can only help with product questions. Try asking about our SUPs, windsurfing equipment, or accessories."
4. NEVER make up product information - only use what the tools return

Tools:
- search_products: Search by name, description, category
- search_in_stock: Find available products only
- get_product_by_code: Look up by product code or EAN
- list_categories: Show all categories

When answering:
- Include product codes and prices
- Mention stock availability
- Suggest alternatives if something is out of stock"""
    )
    return agent


# ============================================
# Main Execution
# ============================================

def main():
    global vector_store

    API_URL = "https://api.time-4-action.com/api/export/product"
    PERSIST_DIR = "./chroma_db"

    # Check if we need to rebuild the index
    rebuild = not os.path.exists(PERSIST_DIR) or os.environ.get("REBUILD_INDEX", "false").lower() == "true"

    if rebuild:
        print("Fetching products from API...")
        products = fetch_products(API_URL)
        print(f"Fetched {len(products)} products")

        print("Processing products into documents...")
        documents = process_products(products)
        print(f"Created {len(documents)} documents")

        print("Creating vector store...")
        vector_store = create_vector_store(documents, PERSIST_DIR)
        print("Vector store created!")
    else:
        print("Loading existing vector store...")
        vector_store = load_vector_store(PERSIST_DIR)
        print("Vector store loaded!")

    # Create and run the agent
    agent = create_product_agent()

    print("\n" + "="*50)
    print("Product Knowledge Base Ready!")
    print("Type 'quit' to exit")
    print("="*50 + "\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        if not user_input:
            continue

        response = agent.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        # Extract the last message content
        last_message = response["messages"][-1]
        print(f"\nAssistant: {last_message.content}\n")


if __name__ == "__main__":
    main()
