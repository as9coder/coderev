# CodeRev

Private AI pull request reviews on GitHub: comment **`@coderev`** on a PR thread. Only your GitHub account can trigger it.

---

## Why it is not “@claude on any repo” with zero setup

GitHub only runs **Actions workflows that exist in that repository** (or that you **call** from that repo). There is no way for `as9coder/coderev` alone to listen to comments on **every** repo on GitHub — that is why [Claude on GitHub](https://github.com/apps/claude) is a **GitHub App** you install per account/repo.

CodeRev’s equivalent is: **each repo you care about** either contains a workflow, or **reuses** the workflow from this repo (one small file to add).

---

## OpenRouter key: repository secret

Use **Repository secrets** (Secrets tab), **not** environment secrets, unless you already use GitHub Environments and attach this workflow to one.

- Add **`OPENROUTER_API_KEY`** under **Settings → Secrets and variables → Actions → Secrets**.

---

## Use CodeRev in *this* repo (`as9coder/coderev`)

1. **Variable** `CODEREV_ALLOWED_USER` = your GitHub username (Variables tab).  
2. **Secret** `OPENROUTER_API_KEY`.  
3. Open a PR here, comment **`@coderev`**.

---

## Use CodeRev in *any other* repo (what you actually wanted)

For each project repo (e.g. `you/cool-app`):

1. Copy [`examples/coderev-in-any-repo.yml`](examples/coderev-in-any-repo.yml) to:

   `cool-app/.github/workflows/coderev.yml`

2. In **that** repo’s settings, add the same **variable** and **secret** (`CODEREV_ALLOWED_USER`, `OPENROUTER_API_KEY`).  
   - Or use **organization** secrets/variables if everything lives under one org.

3. Open a PR **in that repo**, comment **`@coderev`**.

The thin workflow calls **`as9coder/coderev/.github/workflows/coderev-reusable.yml@main`**, which checks out the scripts from this repo and reviews **that** repo’s PR (not the coderev repo).

---

## Changing the model

Edit **`.github/workflows/coderev-reusable.yml`** (`MODEL` env), push to `main`, and consumers pick it up on `@main`.

---

## Security notes

- Triggers only when **`github.actor`** matches `CODEREV_ALLOWED_USER` and the comment contains `@coderev`.
- The Python script enforces the same allowed user check.
- Very large diffs are truncated (see `MAX_DIFF_CHARS` in `scripts/coderev_review.py`).
