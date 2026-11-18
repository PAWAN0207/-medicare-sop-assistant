# Test report

- Command: `make test`  (= `PROVIDER=fake DB_PATH=:memory: python -m pytest tests -q`)
- Runs fully offline: fake LLM + hash embedder, no network, no API key.
- Date: 2026-11-18  |  Python 3.12.3 on Linux
- Result: **72 passed, 1 warning in 7.17s**

## What the tests cover
| File | Focus |
|---|---|
| test_pii.py | patient-data guard: the 5 pack inputs, each identifier type, false-positive guards, no values echoed |
| test_access_and_parser.py | role->level policy (fail closed), header metadata from the PDF (not file name), tables kept as rows, revision history never indexed, rename keeps identity+hash, corrupt PDF rejected |
| test_indexer.py | add/update/remove diff, idempotent 2nd run (0 embeddings), no stale chunks, rename not re-embedded, **crash after embed / mid-apply leaves index untouched**, **concurrent readers never see old+new mix**, duplicate SOP id / empty folder / mass-withdrawal / bad PDF abort the whole snapshot, embedder change needs --rebuild, dry-run |
| test_qa_access_cache.py | restricted text never reaches the LLM prompt, per-role retrieval bounds, unknown user, role not spoofable via question text, PII blocked before LLM/cache, refusal without LLM call, NOT_COVERED/ungrounded -> refusal, citations (SOP, version, section, page), cache hit/normalisation, **no cross-role cache leak**, cache-key dimensions, **no superseded answer after re-index**, withdrawn SOP never cited |
| test_api.py | response shape, correlation id, error envelope for 403/422/502/504/500, PII 422 without echo, failures never cached |
| test_adapters.py | retry on 429/5xx with backoff, no retry on 4xx, timeout mapping, timeout passed on every call, malformed response, embedding batching/order |
| test_eval_gate.py | offline eval pass rates as a regression guard; held-out paraphrase set for the refusal gate |

## Full output
```
tests/test_access_and_parser.py::test_role_levels PASSED                 [  1%]
tests/test_access_and_parser.py::test_unknown_role_sees_nothing PASSED   [  2%]
tests/test_access_and_parser.py::test_unknown_access_field_fails_closed PASSED [  4%]
tests/test_access_and_parser.py::test_unknown_user PASSED                [  5%]
tests/test_access_and_parser.py::test_header_metadata_comes_from_document PASSED [  6%]
tests/test_access_and_parser.py::test_table_rows_stay_whole PASSED       [  8%]
tests/test_access_and_parser.py::test_revision_history_is_not_indexed PASSED [  9%]
tests/test_access_and_parser.py::test_renamed_file_same_identity_and_hash PASSED [ 11%]
tests/test_access_and_parser.py::test_changed_version_changes_hash PASSED [ 12%]
tests/test_access_and_parser.py::test_corrupt_pdf_rejected PASSED        [ 13%]
tests/test_adapters.py::test_retries_5xx_then_succeeds PASSED            [ 15%]
tests/test_adapters.py::test_4xx_not_retried PASSED                      [ 16%]
tests/test_adapters.py::test_timeout_after_retries PASSED                [ 18%]
tests/test_adapters.py::test_timeout_is_passed_to_every_call PASSED      [ 19%]
tests/test_adapters.py::test_malformed_response PASSED                   [ 20%]
tests/test_adapters.py::test_embedder_batches_and_orders PASSED          [ 22%]
tests/test_api.py::test_ask_ok_shape_and_request_id PASSED               [ 23%]
tests/test_api.py::test_error_envelope_unknown_user PASSED               [ 25%]
tests/test_api.py::test_validation_error_envelope PASSED                 [ 26%]
tests/test_api.py::test_pii_blocked_422_without_echo PASSED              [ 27%]
tests/test_api.py::test_upstream_failures_map_to_clean_errors[exc0-504-UPSTREAM_TIMEOUT] PASSED [ 29%]
tests/test_api.py::test_upstream_failures_map_to_clean_errors[exc1-502-UPSTREAM_ERROR] PASSED [ 30%]
tests/test_api.py::test_upstream_failures_map_to_clean_errors[exc2-500-INTERNAL] PASSED [ 31%]
tests/test_api.py::test_healthz PASSED                                   [ 33%]
tests/test_eval_gate.py::test_offline_eval_pass_rates PASSED             [ 34%]
tests/test_eval_gate.py::test_gate_generalises_beyond_eval_questions PASSED [ 36%]
tests/test_indexer.py::test_first_run_adds_all PASSED                    [ 37%]
tests/test_indexer.py::test_second_run_is_noop_and_free PASSED           [ 38%]
tests/test_indexer.py::test_update_snapshot_diff PASSED                  [ 40%]
tests/test_indexer.py::test_no_stale_chunks_after_update PASSED          [ 41%]
tests/test_indexer.py::test_update_is_idempotent PASSED                  [ 43%]
tests/test_indexer.py::test_crash_leaves_index_untouched[after_embed] PASSED [ 44%]
tests/test_indexer.py::test_crash_leaves_index_untouched[mid_apply] PASSED [ 45%]
tests/test_indexer.py::test_readers_never_see_a_mix PASSED               [ 47%]
tests/test_indexer.py::test_duplicate_sop_id_rejects_snapshot PASSED     [ 48%]
tests/test_indexer.py::test_empty_or_wrong_folder_never_withdraws_everything PASSED [ 50%]
tests/test_indexer.py::test_one_bad_pdf_aborts_whole_snapshot PASSED     [ 51%]
tests/test_indexer.py::test_embedder_change_requires_rebuild PASSED      [ 52%]
tests/test_indexer.py::test_dry_run_writes_nothing PASSED                [ 54%]
tests/test_pii.py::test_pack_inputs PASSED                               [ 55%]
tests/test_pii.py::test_detects_each_type[Patient Ramesh Kumar has fever-person_name] PASSED [ 56%]
tests/test_pii.py::test_detects_each_type[MRN 448812 needs a retest-mrn] PASSED [ 58%]
tests/test_pii.py::test_detects_each_type[Aadhaar 452188901234 on file-aadhaar_number] PASSED [ 59%]
tests/test_pii.py::test_detects_each_type[call +91 98480 22113-phone_number] PASSED [ 61%]
tests/test_pii.py::test_detects_each_type[patient DOB 12/04/1961-date_of_birth] PASSED [ 62%]
tests/test_pii.py::test_detects_each_type[email her at asha.k@example.com-email] PASSED [ 63%]
tests/test_pii.py::test_no_false_positives[What is the procedure for a needle-stick injury?] PASSED [ 65%]
tests/test_pii.py::test_no_false_positives[Patient Registration steps for walk-in patients?] PASSED [ 66%]
tests/test_pii.py::test_no_false_positives[What does SOP-04 v3.0 say about OH-05?] PASSED [ 68%]
tests/test_pii.py::test_no_false_positives[Refund up to Rs 1,500 for billing errors?] PASSED [ 69%]
tests/test_pii.py::test_no_false_positives[Slots are 15 minutes, max 14 per session] PASSED [ 70%]
tests/test_pii.py::test_no_false_positives[What is the policy for patients without ID?] PASSED [ 72%]
tests/test_pii.py::test_returns_types_never_values PASSED                [ 73%]
tests/test_qa_access_cache.py::test_restricted_text_never_reaches_llm_for_front_desk PASSED [ 75%]
tests/test_qa_access_cache.py::test_clinical_sops_hidden_from_front_desk_but_visible_to_nurse PASSED [ 76%]
tests/test_qa_access_cache.py::test_every_retrieved_chunk_is_within_role[U1001-allowed0] PASSED [ 77%]
tests/test_qa_access_cache.py::test_every_retrieved_chunk_is_within_role[U2001-allowed1] PASSED [ 79%]
tests/test_qa_access_cache.py::test_every_retrieved_chunk_is_within_role[U6001-allowed2] PASSED [ 80%]
tests/test_qa_access_cache.py::test_every_retrieved_chunk_is_within_role[U5001-allowed3] PASSED [ 81%]
tests/test_qa_access_cache.py::test_hr_sees_hr_sop_nurse_does_not PASSED [ 83%]
tests/test_qa_access_cache.py::test_unknown_user_and_prompt_does_not_choose_role PASSED [ 84%]
tests/test_qa_access_cache.py::test_pii_blocked_before_llm_cache_and_retrieval PASSED [ 86%]
tests/test_qa_access_cache.py::test_unanswerable_refuses_without_calling_llm PASSED [ 87%]
tests/test_qa_access_cache.py::test_llm_not_covered_and_ungrounded_become_refusals PASSED [ 88%]
tests/test_qa_access_cache.py::test_citations_have_sop_version_section_page PASSED [ 90%]
tests/test_qa_access_cache.py::test_empty_index_is_a_clear_error PASSED  [ 91%]
tests/test_qa_access_cache.py::test_repeat_question_served_from_cache PASSED [ 93%]
tests/test_qa_access_cache.py::test_cache_never_leaks_across_roles PASSED [ 94%]
tests/test_qa_access_cache.py::test_cache_key_dimensions PASSED          [ 95%]
tests/test_qa_access_cache.py::test_reindex_never_serves_superseded_answer PASSED [ 97%]
tests/test_qa_access_cache.py::test_withdrawn_sop_never_cited_after_update PASSED [ 98%]
tests/test_qa_access_cache.py::test_stale_race_entry_is_harmless PASSED  [100%]
```
