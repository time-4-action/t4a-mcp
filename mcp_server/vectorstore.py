from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from mcp_server.config import CHROMA_DB_PATH


def initialize_vectorstore() -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    return Chroma(
        collection_name="products",
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings,
    )


vectorstore = initialize_vectorstore()
