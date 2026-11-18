# Semantic Retrieval Evaluation

- Embedding model: `gemini-embedding-001`
- Database generation: `4`
- Existing chunks: `74`
- Questions evaluated: `15`
- Top K: `6`
- Embedding strategy: single batch
- LLM calls: 0
- Re-indexing: No

| ID | Type | Result | Expected section rank(s) |
|---|---|---|---|
| Q01 | answerable | PASS | 2 |
| Q02 | answerable | PASS | 1 |
| Q03 | answerable | PASS | 1 |
| Q04 | answerable | PASS | 3 |
| Q05 | answerable | PASS | 1 |
| Q06 | answerable | PASS | 1 |
| Q07 | answerable | PASS | 1 |
| Q08 | answerable | PASS | 1 |
| Q09 | answerable | PASS | 1 |
| Q10 | answerable | PASS | 1 |
| Q11 | unanswerable | N/A - REFUSAL TESTED OFFLINE | - |
| Q12 | unanswerable | N/A - REFUSAL TESTED OFFLINE | - |
| Q13 | unanswerable | N/A - REFUSAL TESTED OFFLINE | - |
| Q14 | conflict | PASS | 1, 2 |
| Q15 | conflict | PASS | 1, 2 |

## Interpretation

- PASS means every expected SOP section appeared within top K.
- FAIL means at least one expected section was outside top K.
- N/A means the question is unanswerable; retrieval ranking alone cannot establish whether the assistant correctly refused.
- This test evaluates retrieval, not generated answer quality or final citation validation.
