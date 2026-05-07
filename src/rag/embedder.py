"""
Embedding layer.

Loads the 1,076 composite ANZSCO documents, embeds them with
sentence-transformers (all-MiniLM-L6-v2), and persists the vectors
to disk as a numpy array so they only need to be computed once.

On re-run it checks whether anzsco_documents.json has changed
(via SHA-256) and only re-embeds if it has.
"""

import hashlib
import json
import pathlib
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_PROC     = pathlib.Path('data/processed')
DOCS_FILE     = DATA_PROC / 'anzsco_documents.json'
EMBEDDINGS_FILE = DATA_PROC / 'anzsco_embeddings.npy'
METADATA_FILE = DATA_PROC / 'anzsco_metadata.json'   # codes + titles in index order
EMBED_HASH_FILE = DATA_PROC / 'embeddings_hash.txt'

MODEL_NAME = 'all-MiniLM-L6-v2'


def _docs_hash() -> str:
    return hashlib.sha256(DOCS_FILE.read_bytes()).hexdigest()


def build_embeddings(force: bool = False) -> tuple[np.ndarray, list[dict]]:
    """
    Embed all ANZSCO documents. Skips if embeddings are already current.
    Returns (embeddings array, metadata list).
    """
    current_hash = _docs_hash()
    stored_hash  = EMBED_HASH_FILE.read_text().strip() if EMBED_HASH_FILE.exists() else ''

    if not force and stored_hash == current_hash and EMBEDDINGS_FILE.exists():
        print('Embeddings up to date — loading from disk.')
        return load_embeddings()

    print(f'Building embeddings with {MODEL_NAME}...')
    docs = json.loads(DOCS_FILE.read_text())
    model = SentenceTransformer(MODEL_NAME)

    texts = [d['embedding_text'] for d in docs]
    print(f'  Embedding {len(texts)} documents...')
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True,
                              normalize_embeddings=True)

    metadata = [{
        'code':            d['code'],
        'title':           d['title'],
        'unit_code':       d['unit_code'],
        'unit_title':      d['unit_title'],
        'minor_title':     d['minor_title'],
        'sub_major_title': d['sub_major_title'],
        'major_title':     d['major_title'],
        'skill_level':     d['skill_level'],
        'alt_titles':      d['alt_titles'],
        'specialisations': d['specialisations'],
        'embedding_text':  d['embedding_text'],
    } for d in docs]

    np.save(EMBEDDINGS_FILE, embeddings)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))
    EMBED_HASH_FILE.write_text(current_hash)

    print(f'  Saved {len(embeddings)} embeddings -> {EMBEDDINGS_FILE}')
    print(f'  Embedding shape: {embeddings.shape}')
    return embeddings, metadata


def load_embeddings() -> tuple[np.ndarray, list[dict]]:
    """Load pre-built embeddings and metadata from disk."""
    embeddings = np.load(EMBEDDINGS_FILE)
    metadata   = json.loads(METADATA_FILE.read_text())
    return embeddings, metadata


def embed_query(text: str, model: SentenceTransformer | None = None) -> np.ndarray:
    """Embed a single query string. Loads model if not provided."""
    if model is None:
        model = SentenceTransformer(MODEL_NAME)
    return model.encode([text], normalize_embeddings=True)[0]


if __name__ == '__main__':
    embeddings, metadata = build_embeddings()
    print(f'Done. Shape: {embeddings.shape}')
