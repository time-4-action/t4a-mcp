from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
import app.config as settings


@dataclass
class Chunk:
    id: str
    text: str
    parent_id: str | None
    is_parent: bool
    index: int
    metadata: dict


def build_parent_child_chunks(
    text: str,
    source_id: str,
    source_label: str,
    source_type: str,
    source_url: str = None,
) -> tuple[list[Chunk], list[Chunk]]:
    """
    Returns (parent_chunks, child_chunks).
    Each child knows its parent_id.
    Parents are for context expansion; children are embedded for retrieval.
    """
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.PARENT_CHUNK_SIZE,
        chunk_overlap=settings.PARENT_CHUNK_OVERLAP,
        length_function=len,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHILD_CHUNK_SIZE,
        chunk_overlap=settings.CHILD_CHUNK_OVERLAP,
        length_function=len,
    )

    parent_texts = parent_splitter.split_text(text)
    parents = []
    children = []

    base_meta = {
        "source_id": source_id,
        "source_label": source_label,
        "source_type": source_type,
    }
    if source_url:
        base_meta["source_url"] = source_url

    for p_idx, p_text in enumerate(parent_texts):
        p_id = f"{source_id}_p{p_idx}"
        parents.append(Chunk(
            id=p_id,
            text=p_text,
            parent_id=None,
            is_parent=True,
            index=p_idx,
            metadata={**base_meta, "chunk_type": "parent", "parent_index": p_idx},
        ))

        child_texts = child_splitter.split_text(p_text)
        for c_idx, c_text in enumerate(child_texts):
            c_id = f"{source_id}_p{p_idx}_c{c_idx}"
            children.append(Chunk(
                id=c_id,
                text=c_text,
                parent_id=p_id,
                is_parent=False,
                index=c_idx,
                metadata={
                    **base_meta,
                    "chunk_type": "child",
                    "parent_id": p_id,
                    "parent_index": p_idx,
                    "child_index": c_idx,
                },
            ))

    return parents, children
