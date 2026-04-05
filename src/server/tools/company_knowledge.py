from src.server import mcp
from src.server.permissions import require_permission, with_permission_check


@mcp.tool()
async def company_knowledge(
    question: str,
    top_k: int = 5,
) -> str:
    """
    Search the T4A company knowledge base.

    Use this tool to answer any questions about:
    - Company products, services, and features
    - Pricing, terms, and policies
    - Internal processes and documentation
    - Technical specifications
    - Contact information and team structure

    Args:
        question: The question or topic to look up
        top_k: Number of relevant passages to return (default 5, max 10)

    Returns:
        Relevant passages from company documents with source attribution.
        Always cite the source when using this information.
    """
    require_permission("company_knowledge")

    from app.retrieval import retrieve

    top_k = min(top_k, 10)
    results = await retrieve(question, top_k=top_k)

    if not results:
        return "No relevant information found in the company knowledge base."

    lines = [f"Found {len(results)} relevant passages:\n"]
    for r in results:
        source = r["source_label"]
        if r.get("source_url"):
            source = f"{source} ({r['source_url']})"
        lines.append(f"[{r['rank']}] Source: {source}")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)
