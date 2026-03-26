# CodeRev

Private AI pull request reviews: comment **`@coderev`** on a PR. Only **your** GitHub account can trigger it.

---

## Easiest path (no app, no tunnel, no PEM)

If you do not want to register a GitHub App or run a server, use **GitHub Actions only**:

1. In each repo you care about, add [examples/coderev-in-any-repo.yml](examples/coderev-in-any-repo.yml) as `.github/workflows/coderev.yml`.
2. In that repo: **Variable** `CODEREV_ALLOWED_USER` = your username, **Secret** `OPENROUTER_API_KEY`.
3. Comment **`@coderev`** on a PR.

That is it. No local hosting, no webhook setup.

---

## Optional: GitHub App (install on many repos without a workflow file per repo)

Only use this if you want Claude-style “install app once” and are okay hosting a small HTTPS service. Otherwise skip entirely.

---

## Option A — GitHub App (install once, use on many repos)

This matches how [Claude’s GitHub App](https://github.com/apps/claude) works: you **register an app**, **deploy** the webhook, then **install** it on your account or on selected repositories.

**→ Step-by-step with field names:** **[SETUP-GITHUB-APP.md](SETUP-GITHUB-APP.md)** (create app, App ID, PEM, webhook secret, `.env`).

### Why “so many parameters”?

GitHub’s App model needs **three** values from them (app id, private key, webhook secret). OpenRouter needs **one** API key. You need **one** username so random people cannot burn your credits. That is **five** lines in `.env` — not optional on GitHub’s side. Short names: `APP_ID`, `PRIVATE_KEY_FILE`, `WEBHOOK_SECRET`, `OPENROUTER_KEY`, `ALLOWED_USER` (old long names still work).

---

### Create the GitHub App (first)

1. Open **[Register new GitHub App](https://github.com/settings/apps/new)**.

2. **Webhook URL:** use a tunnel URL when you have it (`https://…/webhook`). It must be **HTTPS** (you can update this after you start `cloudflared` / `ngrok`).

3. **Webhook secret:** a long random string — same value as **`WEBHOOK_SECRET`** in `.env`.

4. **Repository permissions:** Contents **Read**, Issues **Read**, Pull requests **Read and write**, Metadata **Read**.

5. **Subscribe to events:** **Issue comment** only.

6. **Where can this GitHub App be installed?** — your choice (often “Only on this account”).

7. **Create** the app. Copy the numeric **App ID**. **Generate a private key** and save the `.pem` as **`github-app.pem`** in your `coderev` folder (gitignored).

---

### `.env` (five fields)

| Variable | Meaning |
|----------|---------|
| `APP_ID` | App’s **About** page |
| `PRIVATE_KEY_FILE` | e.g. `./github-app.pem` |
| `WEBHOOK_SECRET` | Same as in GitHub App webhook settings |
| `OPENROUTER_KEY` | From [openrouter.ai/keys](https://openrouter.ai/keys) |
| `ALLOWED_USER` | Your GitHub username |

Optional: `MODEL` (default `minimax/minimax-m2.7`). Aliases: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`, `OPENROUTER_API_KEY`, `CODEREV_ALLOWED_USER`.

Copy **`.env.example`** → **`.env`** and fill in.

---

### Run on this laptop (then VPS later)

GitHub only delivers webhooks to **public HTTPS**. Run the app locally, then tunnel it.

1. **Start the API**

   ```powershell
   .\scripts\run-local.ps1
   ```

2. **Tunnel** (pick one):

   - [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/): `cloudflared tunnel --url http://127.0.0.1:8080` — use the `https://….trycloudflare.com` URL.

   - **ngrok:** `ngrok http 8080` — use the `https` URL.

3. In the GitHub App → **General**, set **Webhook URL** to `https://YOUR_HOST/webhook` and **Save**.

4. **Install** the app (**Install App** in the sidebar) on your repos.

5. Open a PR, comment **`@coderev`**.

**Checks:** `GET https://YOUR_HOST/health` → `{"status":"ok"}`. Webhook: **`POST /webhook`**.

**VPS later:** same `.env`, run `docker compose up -d` (or `uvicorn` behind Caddy/nginx), point the app’s webhook at `https://your-domain/webhook`.

---

### Deploy with Docker (server / VPS)

```bash
cp .env.example .env
# edit .env, then:
docker compose up --build -d
```

Optional: [`github-app-manifest.json`](github-app-manifest.json) + [manifest flow](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest).

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

- Only **`ALLOWED_USER`** (GitHub App) or **`CODEREV_ALLOWED_USER`** (Actions) may trigger reviews; `@coderev` must appear in the comment.
- Large diffs are truncated (see `MAX_DIFF_CHARS` in [`coderev_lib/core.py`](coderev_lib/core.py)).
- Never commit `.env` or PEM keys.
