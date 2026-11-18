# Setup, testing and publishing guide

Requires Python 3.11+ (3.12 recommended) and Git. Everything below works offline except the "real LLM" part.

## 1. Install (venv + dependencies)

**macOS / Linux / WSL**
```bash
make setup            # creates .venv, installs requirements.txt, copies .env.example to .env
```

**Windows (PowerShell, no `make` needed)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
copy .env.example .env
```
`python --version` must show 3.11 or newer. The prompt shows `(.venv)` once the environment is active.

## 2. Run the offline test suite (no API key)
```bash
make test                                                     # macOS / Linux / WSL
```
```powershell
$env:PROVIDER="fake"; $env:DB_PATH=":memory:"; python -m pytest tests -q     # Windows
```
All tests must pass before anything else. To refresh `docs/test_report.md`, run `make report` (or the pytest command with `-v`)
and paste the real output into that file.

## 3. Run the service offline (fake provider)
```bash
make run                      # indexes data/sops, serves http://localhost:8000 (Swagger: /docs)
make ingest SNAPSHOT=data/sop_updates/2026-11-01      # second terminal: apply the update, prints the change report
```
```powershell
python -m sopassist.ingest.cli data/sops
python -m uvicorn sopassist.main:app --port 8000
python -m sopassist.ingest.cli data/sop_updates/2026-11-01      # second terminal
```

## 4. Add your API key (real LLM)
1. Create a free key at https://aistudio.google.com/apikey (or use any OpenAI-compatible provider).
2. Edit `.env` (never commit it; it is in `.gitignore`):
   ```
   PROVIDER=openai_compat
   LLM_API_KEY=your-key-here
   ```
3. Verify key and model names: `make check-key` (Windows: `python scripts/check_key.py`). A 404 means the model name in `LLM_MODEL`
   or `EMBED_MODEL` is retired or misspelled; pick a current one in AI Studio and update `.env`.
4. Delete the fake-vector index once (`var/sop_index.db`), then `make ingest` and `make eval-live`.
5. Copy the numbers from `docs/eval_results_live.md` into the README/brief/pitch and re-tune `MIN_TERM_COVERAGE` / `MIN_COSINE`
   if the live run shows false refusals. Free tiers are rate-limited: a 429 is retried with backoff; if indexing still fails, wait a minute and re-run (ingestion is idempotent).

## 5. Push to GitHub (private repo)
```bash
git config user.name  "Your Name"
git config user.email "your-github-email@example.com"     # the zip's commits use a placeholder email, see below
git status                                                # .env and var/ must NOT appear
git ls-files | grep -E "^\.env$|\.db$" || echo "clean"    # must print: clean
```
1. On github.com: **New repository**, name `sop-assistant`, visibility **Private**, no README/.gitignore (the repo already has them).
2. Share it with the reviewer: *Settings > Collaborators > Add people* (use the reviewer email / GitHub username HR gives you).
3. ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/sop-assistant.git
   git push -u origin main
   ```
   GitHub asks for a login: use a Personal Access Token (Settings > Developer settings > Tokens, `repo` scope) as the password, or `gh auth login`.
4. Optional: replace the placeholder author email on the existing commits before the first push:
   ```bash
   git rebase -r --root --exec "git commit --amend --reset-author --no-edit"
   ```
5. Open the repo in a private/incognito window while logged out: it must **not** be visible. Then reply to the HR email with the link.

## 6. Before you submit
- [ ] `make test` passes on your machine; `docs/test_report.md` holds that real output
- [ ] `make check-key` OK; `make eval-live` run; live numbers added to README / brief / pitch
- [ ] `AI_USAGE.md`: fill in the "Candidate to complete" section truthfully (what you ran, read, changed)
- [ ] Record the 3-5 minute pitch (`docs/pitch_script.md`), put the link in your reply
- [ ] Reply to the HR email with: repo link, pitch link, and a note on what you left out and why
