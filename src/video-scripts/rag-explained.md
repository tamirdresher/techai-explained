---
title: "RAG Explained: Retrieval-Augmented Generation in 10 Minutes"
description: "A video script breaking down how RAG works — vector embeddings, chunking strategies, retrieval pipelines, and building a RAG system that actually gives accurate answers."
date: 2026-03-11
tags: ["Video Script"]
---

## Video Metadata

- **Target Duration:** 10 minutes
- **Format:** Animated diagrams + code walkthrough + live demo
- **Audience:** Developers building LLM-powered applications who need their AI to use private data
- **Thumbnail Concept:** Brain icon with arrows pointing to document icons and a database — text "RAG: How AI Reads YOUR Data"

---

## Script Outline

### INTRO (0:00 - 1:00)

**Hook (0:00 - 0:25)**

> "You ask ChatGPT about your company's internal docs and it makes things up. You ask it about last quarter's revenue and it hallucinates a number. RAG — Retrieval-Augmented Generation — is how you fix this. It lets AI answer questions using YOUR data, accurately. In 10 minutes, you'll understand exactly how it works and how to build one."

**Visual:** Side-by-side — left: LLM without RAG giving a wrong answer; right: LLM with RAG giving correct answer with source citations.

**Agenda (0:25 - 1:00)**

> "We'll cover: what RAG actually is in one sentence. How vector embeddings turn documents into searchable math. The retrieval pipeline step by step. Chunking strategies that make or break accuracy. And a working code example you can run today."

---

### SECTION 1: What Is RAG? (1:00 - 2:00)

**One-sentence definition:**

> "RAG is a pattern where you RETRIEVE relevant documents from your data, then AUGMENT the LLM's prompt with those documents, so it can GENERATE an answer grounded in real information."

**Visual — the three steps:**

```
1. RETRIEVE                2. AUGMENT               3. GENERATE
─────────                  ───────                   ────────

User asks:                 System prompt +           LLM generates
"What's our               retrieved docs +           answer using
 refund policy?"          user question               the context

      │                         │                         │
      ▼                         ▼                         ▼
┌──────────┐            ┌──────────────┐         ┌──────────────┐
│ Search   │            │ "Context:    │         │ "Our refund  │
│ vector   │────────►   │  [doc1]      │────►    │  policy      │
│ database │            │  [doc2]      │         │  allows      │
│ for top  │            │              │         │  returns     │
│ matches  │            │ Question:    │         │  within 30   │
└──────────┘            │  What's our  │         │  days..."    │
                        │  refund...?" │         └──────────────┘
                        └──────────────┘
```

**Why not just fine-tune?**

> "Fine-tuning bakes knowledge INTO the model. RAG FETCHES knowledge at query time. Fine-tuning is expensive, slow to update, and can't cite sources. RAG is cheap, instantly updatable, and always tells you WHERE the answer came from."

| | Fine-Tuning | RAG |
|---|---|---|
| Update data | Retrain model (hours/days) | Update database (seconds) |
| Cost | High (GPU training) | Low (embedding + search) |
| Citations | Cannot cite sources | Can cite exact documents |
| Accuracy | Can hallucinate trained data | Grounded in retrieved docs |

---

### SECTION 2: Vector Embeddings — The Magic (2:00 - 3:30)

**Concept (2:00 - 2:45):**

> "An embedding model converts text into a list of numbers — a vector — that captures the MEANING of the text. Similar meanings produce similar vectors. 'How to return a product' and 'refund policy for items' have very different words but very similar vectors."

**Visual:** 3D space showing document vectors clustered by topic. Query vector landing near the relevant cluster.

```
Vector space (simplified to 2D):

    ▲
    │    • "refund policy"
    │    • "return items"         • "shipping rates"
    │    • "money back"           • "delivery times"
    │  ★ QUERY                    • "tracking order"
    │  "how to get a refund"
    │
    │         • "product specs"
    │         • "item dimensions"
    └──────────────────────────────────────►

★ = query vector (closest to refund cluster)
```

**How embedding works (2:45 - 3:30):**

> "You send your text to an embedding model — like OpenAI's text-embedding-3-small or an open-source model like BGE — and get back a vector of 256 to 3072 numbers. You store these vectors in a vector database. When a user asks a question, you embed the question, find the closest vectors, and retrieve those documents."

**Code snippet:**

```python
# Embedding a document
response = openai.embeddings.create(
    input="Our refund policy allows returns within 30 days",
    model="text-embedding-3-small"
)
vector = response.data[0].embedding  # [0.023, -0.041, 0.078, ...]
# 1536 dimensions of meaning
```

---

### SECTION 3: The RAG Pipeline Step by Step (3:30 - 5:30)

**Visual — full pipeline animated:**

```
INDEXING (one-time)                    QUERYING (per question)
───────────────────                    ─────────────────────

Documents ──► Chunking ──► Embedding   User question
                              │            │
                              ▼            ▼
                        ┌──────────┐  Embed question
                        │ Vector   │       │
                        │ Database │◄──────┘
                        └────┬─────┘  Similarity search
                             │
                             ▼
                        Top K chunks
                             │
                             ▼
                     ┌──────────────┐
                     │ LLM Prompt:  │
                     │ Context +    │
                     │ Question     │──► Answer with citations
                     └──────────────┘
```

**Step-by-step walkthrough (3:30 - 5:00):**

> "Step 1: CHUNK your documents. A 50-page PDF needs to be split into smaller pieces. Step 2: EMBED each chunk into a vector. Step 3: STORE vectors in a vector database like Pinecone, Weaviate, or pgvector. That's the indexing phase — you do this once."

> "Step 4: When a user asks a question, EMBED the question. Step 5: SEARCH the vector database for the most similar chunks — typically the top 3-5. Step 6: BUILD the prompt with the retrieved chunks as context. Step 7: Send to the LLM and get a grounded answer."

**Code walkthrough (5:00 - 5:30):**

```python
# Complete RAG pipeline in 20 lines
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Index documents (one-time)
documents = SimpleDirectoryReader("./company-docs").load_data()
index = VectorStoreIndex.from_documents(documents)

# Query (per question)
query_engine = index.as_query_engine(similarity_top_k=3)
response = query_engine.query("What is our refund policy?")

print(response.response)    # The answer
print(response.source_nodes) # The source documents
```

---

### SECTION 4: Chunking — Where Most RAG Systems Fail (5:30 - 7:00)

> "Chunking is the most underrated part of RAG. Get it wrong and your system retrieves the wrong context. Get it right and accuracy jumps dramatically."

**Strategy comparison (5:30 - 6:15):**

```
FIXED SIZE CHUNKING           SEMANTIC CHUNKING
───────────────────           ─────────────────
Split every 500 tokens        Split at paragraph/section boundaries

"...end of section A.        "Section A: Refund Policy
Section B: Shipping..."      Our refund policy allows..."
     ↑ splits mid-topic           ↑ splits at natural boundary

Problem: loses context        Better: preserves meaning

RECURSIVE CHUNKING            PARENT-CHILD CHUNKING
───────────────────           ─────────────────────
Split by paragraph,           Embed small chunks (child)
then by sentence,             but retrieve the parent
then by token                 (larger context)

Adapts to document            Best accuracy
structure                     (search precision + full context)
```

**Key advice (6:15 - 7:00):**

> "Three rules for chunking: First, keep chunk sizes between 256 and 1024 tokens. Too small and you lose context. Too large and you dilute relevance. Second, add overlap — 10-20% — so information at chunk boundaries isn't lost. Third, preserve document structure. Headers, sections, and paragraphs are natural boundaries."

---

### SECTION 5: Production Considerations (7:00 - 8:30)

**Hybrid search (7:00 - 7:30):**

> "Vector search alone misses exact matches. If someone searches for 'error code E-4521', vector similarity might not find it. Hybrid search combines vector search with keyword search — the best of both worlds."

**Re-ranking (7:30 - 8:00):**

> "Retrieve 20 chunks with vector search, then re-rank the top 20 with a cross-encoder model to find the true top 5. This two-stage approach dramatically improves accuracy."

```
Stage 1: Vector search → 20 candidates (fast, approximate)
Stage 2: Cross-encoder rerank → 5 best matches (slow, precise)
```

**Evaluation (8:00 - 8:30):**

> "You MUST evaluate your RAG system. Create a test set of 50-100 questions with known correct answers. Measure retrieval accuracy (did we find the right chunks?) and generation accuracy (did the LLM produce the right answer?). Without eval, you're guessing."

---

### SECTION 6: Live Demo (8:30 - 9:30)

> "Let me show you a working RAG system in 60 seconds."

**Demo:** Screen recording showing:
1. Loading 10 PDF documents
2. Creating the vector index (show progress bar)
3. Asking three questions and getting accurate, cited answers
4. Showing the source documents for each answer

---

### OUTRO (9:30 - 10:00)

> "That's RAG — the pattern that makes AI actually useful with your own data. Retrieval, augmentation, generation. The hard parts are chunking and evaluation. Get those right and you have a system that answers questions accurately with citations. Subscribe for more AI engineering deep dives."

**End Screen:** Two suggested videos.

---

## Production Notes

- **B-Roll:** Vector space visualizations, document being chunked animation, code IDE
- **Graphics:** Pipeline diagrams, comparison tables, 3D vector space visualization
- **Demo:** Use a pre-built Jupyter notebook for the live demo — keep it snappy
- **Music:** Curious, exploratory tone — this is educational content
- **SEO Tags:** RAG, retrieval augmented generation, vector embeddings, LLM, AI engineering, vector database, LlamaIndex, LangChain, embeddings, chunking

*Script by the TechAI Explained Team.*
