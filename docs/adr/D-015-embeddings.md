# D-015: No Embeddings Until P9-Semantic Trigger

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** —

## Context

~13 sample items; no retrieval problem today. Vector DB would be padding.

## Decision

No embeddings/vector DB in the locked spine. If a later **P9-semantic** trigger appears (real corpus size), use **local** embeddings first.

## Alternatives considered

Qdrant/Pinecone now; OpenAI embeddings by default.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) No embeddings until P9 trigger | Avoids padding |
| (b) Vector DB now | Overkill for ~13 items |

## Acceptance criteria

- No vector DB in B0–B7 spine; if P9 triggers, local embeddings first.

## Consequences

Keeps B0–B7 thin; backlog only.
