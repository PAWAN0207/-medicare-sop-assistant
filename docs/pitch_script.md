# Pitch script - 4 minutes, for the Head of Operations (non-technical)
**Rules from the brief:** no code on screen for the first 2 minutes. Show slides (or just talk to camera) until 2:00, then a short live demo in the Swagger page (`/docs`) or a terminal.

**0:00-0:30 - The problem.** "Your staff lose time in a shared drive where old and new SOPs sit next to each other. The risk isn't only time - it's someone following an outdated rule, for example a needle-stick reporting window or a refund limit."

**0:30-1:15 - What you get.** "An assistant that answers staff questions only from today's SOPs. Every answer shows the SOP, version, section and page. If the SOPs don't cover it, it says 'I don't know' - it will not guess a drug dose or invent a policy."

**1:15-2:00 - Trust, in three promises.** (1) "Right people see the right documents: a nurse never gets an answer from an HR-only SOP - the assistant never even sees that text." (2) "Patient names, phone numbers, Aadhaar are blocked before anything is processed." (3) "When you publish a new SOP library, only what changed is updated; withdrawn SOPs vanish and old saved answers are thrown away automatically."

**2:00-3:15 - Demo (screen share, Swagger page).**
1. As a nurse (U2001): "What is the procedure for a needle-stick injury?" -> point at the citations (SOP-04, version, section, page).
2. Paste a question with a patient name + MRN -> it is blocked with a clear message.
3. Run the update snapshot in the terminal -> show the change report (2 added, 3 updated, 1 withdrawn, 1 renamed, 11 untouched). Ask the refund question as front desk (U1001): now Rs 1,500.
4. Ask "What is the maximum salary advance I can take?" as a nurse (U2001) -> "I don't know" (HR-only SOP is invisible to her); ask it as HR (U6001) -> answer with citation.

**3:15-3:45 - Numbers.** "Tested on 23 questions: all 'I don't know' cases and both conflicting-SOP cases pass, all 5 patient-data inputs blocked. [Say the live-model number once you have run `make eval-live`.] Rough running cost for 300 staff and 2,000 questions a day: about USD 30-50 a month."

**3:45-4:15 - Risks and next steps.** "Today it's a proof of concept: it needs your single sign-on, a pilot in two clinics, and a live-model test before rollout. It errs on the side of 'I don't know'. Ask me about any of it - thank you."

**Before recording:** run `make run`, open `http://localhost:8000/docs`, check your mic, keep it under 5 minutes, upload to Loom/Drive/unlisted YouTube and test the link in a private window.
