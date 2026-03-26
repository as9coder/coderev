# CodeRev

Private AI pull request reviews: comment **`@coderev`** on a PR. Only **your** GitHub account can trigger it.

You can run it in two ways:

1. **GitHub App (recommended, Claude-style)** — install the app on any repo you choose; **no workflow files** in those repos. You host a small HTTPS webhook (Docker-friendly).
2. **GitHub Actions** — workflows in this repo or a [reusable workflow](examples/coderev-in-any-repo.yml) in other repos.

---

## Option A — GitHub App (install once, use on many repos)

This matches how [Claude’s GitHub App](https://github.com/apps/claude) works: you **register an app**, **deploy** the webhook, then **install** it on your account or on selected repositories.

### 1. Deploy the webhook

You need a **public HTTPS URL** (Railway, Render, Fly.io, a VPS, or `ngrok` for testing).

```bash
# copy env
cp .env.example .env
# fill in values (see below), then:
docker compose up --build
```

Health check: `GET /health` → `{"status":"ok"}`. Webhook path: **`POST /webhook`**.

### 2. Create the GitHub App

1. Open **[Register new GitHub App](https://github.com/settings/apps/new)** (personal) or your org’s **Developer settings → GitHub Apps → New**.

2. **Webhook URL:** `https://YOUR_HOST/webhook` (must match your deployment).

3. **Webhook secret:** a long random string — use the **same** value as `GITHUB_WEBHOOK_SECRET` in your server env.

4. **Repository permissions**

   | Permission        | Access   |
   |-------------------|----------|
   | Contents          | Read-only |
   | Issues            | Read-only |
   | Pull requests     | Read and write |
   | Metadata          | Read-only (default) |

5. **Subscribe to events:** **Issue comment** only.

6. **Where can this GitHub App be installed?** — Only on this account, or Any account (your choice).

7. Create the app. Note the **App ID**. Generate and download a **private key** (PEM).

8. Set server environment:

   | Variable | Meaning |
   |----------|---------|
   | `GITHUB_APP_ID` | Numeric App ID from the app settings page |
   | `GITHUB_APP_PRIVATE_KEY` | Full PEM (in `.env` use quoted string with `\n` for newlines) |
   | `GITHUB_WEBHOOK_SECRET` | Same secret you entered in the app’s webhook settings |
   | `OPENROUTER_API_KEY` | From [openrouter.ai/keys](https://openrouter.ai/keys) |
   | `CODEREV_ALLOWED_USER` | Your GitHub username (only this user can trigger reviews) |
   | `MODEL` | Optional; default `minimax/minimax-m2.7` |

9. **Install** the app: app settings → **Install App** → choose **All repositories** or only the ones you want.

10. Open a PR in an installed repo, comment **`@coderev`**. The app receives `issue_comment`, fetches the diff, calls OpenRouter, posts a **PR review**.

Optional: start from [`github-app-manifest.json`](github-app-manifest.json) (replace `YOUR_PUBLIC_URL`) using GitHub’s [manifest flow](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest) if you prefer.

---

## Option B — GitHub Actions (this repo)

1. **Variable** `CODEREV_ALLOWED_USER` = your username.  
2. **Secret** `OPENROUTER_API_KEY`.  
3. PR comment **`@coderev`** here.

---

## Option C — GitHub Actions in *other* repos

Copy [`examples/coderev-in-any-repo.yml`](examples/coderev-in-any-repo.yml) to `YOUR_REPO/.github/workflows/coderev.yml`, then set `CODEREV_ALLOWED_USER` + `OPENROUTER_API_KEY` on **that** repo (or org-level secrets).

---

## Changing the model

- **App:** set env `MODEL` on the server.  
- **Actions:** edit `.github/workflows/coderev-reusable.yml` (`MODEL` env).

---

## Security notes

- Only **`CODEREV_ALLOWED_USER`** may trigger reviews; `@coderev` must appear in the comment.
- Large diffs are truncated (see `MAX_DIFF_CHARS` in [`coderev_lib/core.py`](coderev_lib/core.py)).
- Never commit `.env` or PEM keys.
