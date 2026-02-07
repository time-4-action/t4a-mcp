from ingestion.loader import get_products
from ingestion.flattener import flatten_products
from ingestion.cleaner import clean_products
from ingestion.embedding_formatter import create_embeddings_text

products = get_products()
flat = flatten_products(products)
clean = clean_products(flat)
embeding_texts = create_embeddings_text(clean)