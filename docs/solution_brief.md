# SOP Assistant for MediCare Clinics - Solution brief
*For: Head of Operations. Proof of concept; all figures are estimates to be confirmed in a pilot.*

**The problem.** Staff lose time searching a shared drive where old and new SOP copies sit side by side, and sometimes act on outdated rules.

**What we propose.** A question-and-answer assistant that answers **only from the current SOPs**, shows exactly where the answer comes from
(SOP, version, section, page), and says **"I don't know"** instead of guessing. It respects who may read what (front desk, clinical, HR/managers),
never accepts patient identifiers, and updates itself when the document team drops a new library snapshot.

**How it works (plain language).** Each SOP is read once and split by section. When someone asks a question, the system first checks who is asking and
shows the assistant *only* the SOPs that person is allowed to read. If nothing relevant exists it refuses; otherwise a language model writes a short
answer from those passages and the system attaches the citations. When SOPs change, only changed documents are re-processed, withdrawn ones disappear,
and previously saved answers are discarded automatically so nobody sees an old rule.

**Results so far (offline test harness, not yet with a live model).** All 23 evaluation questions run; 22 passed the pack's criteria - including all
"I don't know" questions, both conflicting-SOP questions, the post-update checks (new refund limit Rs 1,500, walk-in reserve 25%, withdrawn tele-consultation SOP
not cited, HR-only salary-advance SOP hidden from nurses) and 5/5 patient-data inputs blocked. One question (vaccine fridge at 10 degrees) was missed by the
simple offline search; a real language-model search is expected to fix it and will be measured before go-live.

| Trade-off | Choice | Effect |
|---|---|---|
| Accuracy vs. safety | Refuse when unsure | Some valid questions get "I don't know" (about 2 in 12 paraphrases in our check); never a made-up clinical answer |
| Security | Access applied before the AI sees anything; patient data blocked, not cleaned | Restricted SOP text cannot leak through a clever question; staff must rephrase without names/IDs |
| Latency | Cached answer: well under 1 s. New question: roughly 2-4 s (search + model) | Repeated questions are instant and free |
| Data governance | Index and answers stay in your cloud project; only SOP excerpts and the question go to the model provider; audit log with request ids | Confirm provider data-use terms in a pilot |

**Rough monthly cost at 300 staff / 2,000 questions per day** (assumptions: 40% answered from cache, ~1,800 input + 150 output tokens per model call,
a low-cost "flash"-class model at about USD 0.10 / 0.40 per million input / output tokens - *please verify current prices*):
model usage about **USD 10**, embeddings under USD 1, hosting (one small serverless container + storage) about **USD 20-40**.
**Total roughly USD 30-50 per month.** With a premium model priced ~30x higher the model line would be ~USD 250-300; we would pilot the cheap model first.

**Risks and mitigations.** (1) Wrong or missing answers -> citations on every answer, refusal path, weekly review of "I don't know" logs. (2) Patient data in questions ->
blocking guard today; add a dedicated detection service before wide rollout (names are the weak spot). (3) Wrong folder uploaded -> the system rejects empty/partial snapshots
and applies updates all-or-nothing. (4) No login yet -> must sit behind your single sign-on before staff use.

**Next steps (4-6 weeks).** 1) Run the evaluation against the live model and tune. 2) Add single sign-on and a simple chat page. 3) Pilot with 2 clinics and collect "was this helpful" feedback.
4) Add alerts when new SOPs contradict existing ones. 5) Move to a managed database when the library passes ~200 SOPs or multiple servers are needed.
