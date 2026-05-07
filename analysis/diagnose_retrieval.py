import sys, json, numpy as np
sys.path.insert(0, '.')
from src.rag.embedder import load_embeddings, embed_query, MODEL_NAME
from sentence_transformers import SentenceTransformer

query = (
    "Job titles: Senior Software Engineer, Software Developer\n"
    "Duties: Designed and developed scalable backend services using Python and Go; "
    "Led migration of monolithic application to microservices architecture; "
    "Implemented CI/CD pipelines using Jenkins and GitHub Actions; "
    "Mentored junior developers; Built RESTful APIs\n"
    "Skills: Python, Go, Java, PostgreSQL, Redis, AWS, Docker, Kubernetes, REST APIs, Microservices\n"
    "Industries: Software / Technology"
)

print('Loading model and embeddings...')
model = SentenceTransformer(MODEL_NAME)
embeddings, metadata = load_embeddings()
query_vec = embed_query(query, model)
scores = embeddings @ query_vec
ranked = np.argsort(scores)[::-1]

print('\nTop 25 by cosine similarity:')
for rank, i in enumerate(ranked[:25], 1):
    m = metadata[i]
    marker = ' <-- TARGET' if m['code'] == '261313' else ''
    print(f'  {rank:2d}. [{m["code"]}] {m["title"]:45s} score={scores[i]:.4f}{marker}')

for rank, i in enumerate(ranked, 1):
    if metadata[i]['code'] == '261313':
        print(f'\n261313 ranks at position {rank}, score={scores[i]:.4f}')
        break

print('\nEmbedding text for 261313:')
for m in metadata:
    if m['code'] == '261313':
        print(m['embedding_text'])
        break

print('\nEmbedding text for 261316 (DevOps):')
for m in metadata:
    if m['code'] == '261316':
        print(m['embedding_text'])
        break
