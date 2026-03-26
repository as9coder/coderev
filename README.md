# CodeRev

Private AI pull request reviews on GitHub: comment **`@coderev`** on a PR thread to run a review. Only your GitHub account can trigger it.

---

## When you can actually use it

You are **ready to use CodeRev** as soon as **all** of these are true:

| # | Done? | What |
|---|--------|------|
| 1 | ☐ | This code is on GitHub (you pushed this repo, or pasted the workflow + script into a repo you own). |
| 2 | ☐ | Repo variable **`CODEREV_ALLOWED_USER`** is set to **your** GitHub username (Settings → Secrets and variables → Actions → **Variables**). |
| 3 | ☐ | Secret **`OPENROUTER_API_KEY`** is set (Settings → Secrets and variables → Actions → **Secrets**). |

**Then:** open any pull request in that repo, leave a comment that includes **`@coderev`**, and wait for the Actions run to finish — your review appears on the PR.

If something fails, check **Actions** → latest **CodeRev** run for logs.

---

## Setup (step by step)

1. **Push to GitHub**  
   Create an empty repo on GitHub (no README needed), then:

   ```bash
   cd d:\coderev
   git remote add origin https://github.com/YOU/YOUR-REPO.git
   git push -u origin main
   ```

   (Use `master` instead of `main` if that is your default branch.)

2. **Variable** — `CODEREV_ALLOWED_USER` = your username exactly as on [github.com/settings/profile](https://github.com/settings/profile).

3. **Secret** — `OPENROUTER_API_KEY` from [openrouter.ai/keys](https://openrouter.ai/keys).

4. **Try it** — `@coderev` on a PR comment.

---

## Changing the model

Edit `.github/workflows/coderev.yml` (`MODEL` env).

---

## Security notes

- Triggers only when **`github.actor`** matches `CODEREV_ALLOWED_USER` and the comment contains `@coderev`.
- The Python script enforces the same allowed user check.
- Very large diffs are truncated (see `MAX_DIFF_CHARS` in `scripts/coderev_review.py`).
