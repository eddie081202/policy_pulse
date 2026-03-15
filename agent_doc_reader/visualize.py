"""
RAG Vectorstore Visualization
==============================
Reads all embeddings from the Chroma unified vectorstore, reduces
dimensionality with t-SNE, and renders interactive 2D and 3D Plotly
scatter plots. Dots are colored by insurance contract category.

Usage
-----
    from agent_doc_reader.visualize import visualize
    visualize()          # uses default paths from AgentDocReaderEntity

    # Or call individual plots after loading vectors yourself:
    from agent_doc_reader.visualize import load_vectors, plot_2d, plot_3d
    vectors, documents, metadatas = load_vectors(path, collection_name)
    plot_2d(vectors, documents, metadatas)
    plot_3d(vectors, documents, metadatas)
"""

from __future__ import annotations

import os
import textwrap

import numpy as np
from chromadb import PersistentClient
from sklearn.manifold import TSNE
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Color map: category → Plotly color string
# ---------------------------------------------------------------------------
_CATEGORY_COLORS: dict[str, str] = {
    "auto": "green",
    "health": "red",
    "homeowners": "orange",
    "life_other": "purple",
    "csv": "blue",
}
_DEFAULT_COLOR = "gray"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_vectors(
    vectorstore_path: str,
    collection_name: str,
) -> tuple[np.ndarray, list[str], list[dict]]:
    """Load all embeddings, documents, and metadatas from a Chroma collection.

    Parameters
    ----------
    vectorstore_path:
        Path to the Chroma persistent directory.
    collection_name:
        Name of the Chroma collection to read from.

    Returns
    -------
    vectors:
        2-D numpy array of shape (n_docs, embedding_dim).
    documents:
        Raw text for each document.
    metadatas:
        Metadata dict for each document.
    """
    client = PersistentClient(path=vectorstore_path)
    collection = client.get_collection(collection_name)
    result = collection.get(include=["embeddings", "documents", "metadatas"])

    vectors = np.array(result["embeddings"])
    documents: list[str] = result["documents"]
    metadatas: list[dict] = result["metadatas"]

    print(f"Loaded {len(documents)} documents from '{collection_name}'.")
    return vectors, documents, metadatas


def _make_colors(metadatas: list[dict]) -> list[str]:
    """Return a Plotly color string per document based on its category."""
    colors = []
    for meta in metadatas:
        source_type = (meta.get("source_type") or "").lower()
        category = (meta.get("category") or "").lower()

        if source_type == "csv":
            colors.append(_CATEGORY_COLORS["csv"])
        elif category in _CATEGORY_COLORS:
            colors.append(_CATEGORY_COLORS[category])
        else:
            colors.append(_DEFAULT_COLOR)
    return colors


def _make_hover_text(metadatas: list[dict], documents: list[str]) -> list[str]:
    """Build a hover label for each document."""
    texts = []
    for meta, doc in zip(metadatas, documents):
        source_type = (meta.get("source_type") or "unknown").lower()
        category = meta.get("category") or meta.get("contract_type") or source_type

        # Use just the filename, not the full path
        raw_source = (
            meta.get("source_file")
            or meta.get("source")
            or meta.get("contract_id")
            or "—"
        )
        source = os.path.basename(raw_source)

        # Wrap the snippet at 80 chars per line
        snippet = doc[:200].replace("<", "&lt;").replace(">", "&gt;")
        wrapped = "<br>".join(textwrap.wrap(snippet, width=80))

        texts.append(
            f"<b>Category:</b> {category}<br>"
            f"<b>Source:</b> {source}<br>"
            f"<b>Text:</b><br>{wrapped}…"
        )
    return texts


def plot_2d(
    vectors: np.ndarray,
    documents: list[str],
    metadatas: list[dict],
    title: str = "2D RAG Vectorstore Visualization",
) -> None:
    """Run t-SNE (2-D) on *vectors* and show an interactive Plotly scatter plot."""
    print("Running t-SNE (2D)…")
    tsne = TSNE(n_components=2, random_state=42)
    reduced = tsne.fit_transform(vectors)

    colors = _make_colors(metadatas)
    hover_texts = _make_hover_text(metadatas, documents)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=reduced[:, 0],
                y=reduced[:, 1],
                mode="markers",
                marker=dict(size=6, color=colors, opacity=0.8),
                text=hover_texts,
                hoverlabel=dict(
                    bgcolor=colors,
                    font_size=13,
                    font_color="white",
                    bordercolor="white",
                ),
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="x",
        yaxis_title="y",
        width=800,
        height=600,
        margin=dict(r=20, b=10, l=10, t=40),
    )
    fig.show()


def plot_3d(
    vectors: np.ndarray,
    documents: list[str],
    metadatas: list[dict],
    title: str = "3D RAG Vectorstore Visualization",
) -> None:
    """Run t-SNE (3-D) on *vectors* and show an interactive Plotly 3-D scatter plot."""
    print("Running t-SNE (3D)…")
    tsne = TSNE(n_components=3, random_state=42)
    reduced = tsne.fit_transform(vectors)

    colors = _make_colors(metadatas)
    hover_texts = _make_hover_text(metadatas, documents)

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=reduced[:, 0],
                y=reduced[:, 1],
                z=reduced[:, 2],
                mode="markers",
                marker=dict(size=5, color=colors, opacity=0.8),
                text=hover_texts,
                hoverlabel=dict(
                    bgcolor=colors,
                    font_size=13,
                    font_color="white",
                    bordercolor="white",
                ),
            )
        ]
    )
    fig.update_layout(
        title=title,
        scene=dict(xaxis_title="x", yaxis_title="y", zaxis_title="z"),
        width=900,
        height=700,
        margin=dict(r=10, b=10, l=10, t=40),
    )
    fig.show()


def visualize(
    vectorstore_path: str | None = None,
    collection_name: str | None = None,
) -> None:
    """Load the vectorstore and render both 2-D and 3-D t-SNE scatter plots.

    Parameters
    ----------
    vectorstore_path:
        Override the Chroma persistent directory. Defaults to
        ``AgentDocReaderEntity.vectorstore_path``.
    collection_name:
        Override the Chroma collection name. Defaults to
        ``AgentDocReaderEntity.collection_name``.
    """
    # Resolve defaults lazily to avoid importing Gemini clients at module load time
    if vectorstore_path is None or collection_name is None:
        try:
            from .entities.agent_doc_reader_entity import AgentDocReaderEntity
        except ImportError:
            # Running as a standalone script — fall back to absolute import
            from agent_doc_reader.entities.agent_doc_reader_entity import AgentDocReaderEntity
        _defaults = AgentDocReaderEntity()
        if vectorstore_path is None:
            vectorstore_path = _defaults.vectorstore_path
        if collection_name is None:
            collection_name = _defaults.collection_name

    vectors, documents, metadatas = load_vectors(vectorstore_path, collection_name)

    if len(vectors) == 0:
        print("No documents found in the vectorstore. Nothing to visualize.")
        return

    plot_2d(vectors, documents, metadatas)
    plot_3d(vectors, documents, metadatas)


if __name__ == "__main__":
    import sys
    import os

    # Allow running from either the project root or agent_doc_reader/
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    os.chdir(_root)

    from agent_doc_reader.entities.agent_doc_reader_entity import AgentDocReaderEntity
    _e = AgentDocReaderEntity()
    visualize(vectorstore_path=_e.vectorstore_path, collection_name=_e.collection_name)
