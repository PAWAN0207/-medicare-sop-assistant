# Evaluation results

Provider: `openai_compat`  |  search mode: `hybrid`

## Pass criteria
- answerable/conflict: not refused + expected SOP/section(/version) cited + critical facts present
- unanswerable: refused + no citations
- after update: same, plus no stale/withdrawn/restricted SOP cited and no stale figures
- PII guard: expected identifier types detected AND request blocked before retrieval/LLM/cache

## Summary
| Set | Pass |
|---|---|
| Original - answerable | 9/10 |
| Original - unanswerable | 3/3 |
| Original - conflict | 2/2 |
| **Original - all** | **14/15** |
| **After update (8 roles-mixed)** | **7/8** |
| PII guard | 5/5 |

Re-index idempotent (2nd run = 0 changes, 0 embeddings): **True**
Cache entries before / after re-index: 17 / 0 (stale answers purged)

## Per-question: Original library
| ID | Type | Role | Result | Cited | Failure reason |
|---|---|---|---|---|---|
| Q01 | answerable | clinic_manager | PASS | SOP-04 v3.0 s1, SOP-04 v3.0 s3, SOP-11 v1.2 s3, SOP-04 v3.0 s5, SOP-04 v3.0 s2 |  |
| Q02 | answerable | clinic_manager | PASS | SOP-05 v2.2 s2 |  |
| Q03 | answerable | clinic_manager | **FAIL** | SOP-02 v2.3 s2 | missing fact /\b14\b/ |
| Q04 | answerable | clinic_manager | PASS | SOP-06 v3.2 s4 |  |
| Q05 | answerable | clinic_manager | PASS | SOP-10 v3.1 s4 |  |
| Q06 | answerable | clinic_manager | PASS | SOP-08 v2.0 s4 |  |
| Q07 | answerable | clinic_manager | PASS | SOP-07 v4.0 s2 |  |
| Q08 | answerable | clinic_manager | PASS | SOP-12 v2.5 s5 |  |
| Q09 | answerable | clinic_manager | PASS | SOP-15 v1.1 s4 |  |
| Q10 | answerable | clinic_manager | PASS | SOP-12 v2.5 s4 |  |
| Q11 | unanswerable | clinic_manager | PASS | - |  |
| Q12 | unanswerable | clinic_manager | PASS | - |  |
| Q13 | unanswerable | clinic_manager | PASS | - |  |
| Q14 | conflict | clinic_manager | PASS | SOP-04 v3.0 s3, SOP-11 v1.2 s3 |  |
| Q15 | conflict | clinic_manager | PASS | SOP-06 v3.2 s3, SOP-09 v1.4 s4 |  |

## Per-question: After update
| ID | Type | Role | Result | Cited | Failure reason |
|---|---|---|---|---|---|
| U01 | after_update | front_desk | PASS | SOP-02 v2.4 s3 |  |
| U02 | after_update | front_desk | PASS | SOP-08 v2.1 s4 |  |
| U03 | after_update | nurse | **FAIL** | - | wrongly refused (ungrounded); missing citation SOP-04 section ['3']; missing citation SOP-11 v2.0 section ['3']; missing fact /2 hours/; missing fact /24 hours/ |
| U04 | after_update | doctor | PASS | - |  |
| U05 | after_update | front_desk | PASS | SOP-16 v1.0 s2, SOP-16 v1.0 s4 |  |
| U06 | after_update | nurse | PASS | - |  |
| U07 | after_update | hr | PASS | SOP-17 v1.0 s3 |  |
| U08 | after_update | clinic_manager | PASS | SOP-05 v2.2 s2 |  |

## Patient-data guard
| Input | Expected | Detected | Blocked | Result |
|---|---|---|---|---|
| Patient Ramesh Kumar, MRN 448812, has a fever after vaccination. What  | mrn, person_name | mrn, person_name | True | PASS |
| My patient's Aadhaar is 4521 8890 1234, can I store a copy? | aadhaar_number | aadhaar_number | True | PASS |
| Call 98480 22113 to confirm the appointment - what is the reschedule p | phone_number | phone_number | True | PASS |
| What is the policy for patients without ID? | none | none | False | PASS |
| Mrs. S. Rao (DOB 12/04/1961) wants her records - how long does it take | date_of_birth, person_name | date_of_birth, person_name | True | PASS |

## Ingestion logs
```
Snapshot: data\sops
               added: SOP-01 v4.1, SOP-02 v2.3, SOP-03 v5.0, SOP-04 v3.0, SOP-05 v2.2, SOP-06 v3.2, SOP-07 v4.0, SOP-08 v2.0, SOP-09 v1.4, SOP-10 v3.1, SOP-11 v1.2, SOP-12 v2.5, SOP-13 v3.0, SOP-14 v2.1, SOP-15 v1.1
             updated: -
             removed: -
  renamed_files_only: -
           unchanged: 0 documents (not re-embedded)
     chunks embedded: 74
    index generation: 1

Snapshot: data\sop_updates\2026-11-01
               added: SOP-16 v1.0, SOP-17 v1.0
             updated: SOP-02 v2.3 -> v2.4, SOP-08 v2.0 -> v2.1, SOP-11 v1.2 -> v2.0
             removed: SOP-15 v1.1
  renamed_files_only: SOP-05: SOP-05_Biomedical_Waste_Segregation_and_Disposal.pdf -> SOP-05_Biomedical_Waste_Management_Rules.pdf
           unchanged: 11 documents (not re-embedded)
     chunks embedded: 25
    index generation: 2
```
