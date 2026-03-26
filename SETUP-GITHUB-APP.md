# Guided setup: create the CodeRev GitHub App

Follow these in order. Use your real paths: your CodeRev folder is probably `d:\coderev`.

---

## Before you start (pick one path)

**Path A — You already have a public HTTPS URL** (tunnel or VPS): you can enter the final webhook URL in one go:  
`https://YOUR_HOST/webhook`

**Path B — You do not have a tunnel yet:** you can still create the app now. Use a **temporary** webhook URL, then change it later:

- Example placeholder: `https://example.com/webhook` (GitHub accepts it for registration; deliveries will fail until you fix the URL).
- Or: start **`cloudflared tunnel --url http://127.0.0.1:8080`** first, copy the `https://….trycloudflare.com` URL, and use `https://THAT_HOST/webhook` as the real URL from the beginning.

---

## Step 1 — Open the registration form

1. Sign in to GitHub in your browser.
2. Open: **[Register a new GitHub App](https://github.com/settings/apps/new)**  
   (Profile picture → **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App** is the same place.)

---

## Step 2 — Fill in “About”

| Field | What to enter |
|--------|----------------|
| **GitHub App name** | Something unique, e.g. `CodeRev-as9coder` (names must be unique across GitHub). |
| **Description** | Optional, e.g. `Private @coderev PR reviews`. |
| **Homepage URL** | Your repo is fine: `https://github.com/as9coder/coderev` |
| **Webhook** | Leave **Active** checked. |
| **Webhook URL** | `https://YOUR_PUBLIC_HOST/webhook` — must be **HTTPS**. Use your tunnel/VPS URL, or a placeholder you will update later (see above). |
| **Webhook secret** | Create a long random secret (see below). You will paste the **same** value into `.env` as `WEBHOOK_SECRET`. |

### Generate a webhook secret (PowerShell)

```powershell
-join ((48..57 + 65..90 + 97..122 | Get-Random -Count 48 | ForEach-Object { [char]$_ }))
```

Copy the output and save it in a temporary note. Example shape: `kQ7x...` (48 chars).  
**Do not** commit this string to git.

---

## Step 3 — Permissions (Repository permissions)

Scroll to **Repository permissions** and set:

| Permission | Level |
|------------|--------|
| **Contents** | Read-only |
| **Issues** | Read-only |
| **Pull requests** | Read and write |
| **Metadata** | Read-only (often default) |

Leave other permissions as **No access** unless you know you need them.

---

## Step 4 — Subscribe to events

Under **Subscribe to events**, check **only**:

- **Issue comment**

Uncheck everything else unless you have a reason.

---

## Step 5 — Where the app can be installed

Under **Where can this GitHub App be installed?** choose one:

- **Only on this account** — good default for personal use.
- **Any account** — only if you want others to install it later.

---

## Step 6 — Create the app

1. Click **Create GitHub App** at the bottom.
2. You are now on the app’s settings page.

---

## Step 7 — Copy the App ID (`APP_ID`)

1. On the left, click **General** (if you are not already there).
2. At the top, under the app name, find **App ID** — a number like `1234567`.
3. Copy that number. In `.env` you will set:

   ```env
   APP_ID=1234567
   ```

   (Use your real number.)

---

## Step 8 — Generate and save the private key (`github-app.pem`)

1. On the same **General** page, find **Private keys**.
2. Click **Generate a private key**.
3. Your browser downloads a `.pem` file (name like `your-app-name.YYYY-MM-DD.private-key.pem`).
4. Move or copy that file into your CodeRev project folder and rename it to **`github-app.pem`**.

   Example (adjust paths):

   ```powershell
   Copy-Item "$env:USERPROFILE\Downloads\*.private-key.pem" "d:\coderev\github-app.pem"
   ```

   If you already have multiple `.pem` downloads, pick the one you just generated.

5. Confirm **`github-app.pem`** is listed in `.gitignore` (this repo already ignores it).

6. In `.env` set:

   ```env
   PRIVATE_KEY_FILE=./github-app.pem
   ```

---

## Step 9 — Put the webhook secret in `.env`

You already generated the secret in Step 2. In `.env`:

```env
WEBHOOK_SECRET=paste-the-exact-same-string-as-in-github
```

No quotes unless your secret contains spaces (avoid spaces).

---

## Step 10 — Finish `.env`

In your `coderev` folder:

1. Copy `.env.example` to `.env` if you have not already.
2. Set:

   ```env
   APP_ID=...           # from Step 7
   PRIVATE_KEY_FILE=./github-app.pem
   WEBHOOK_SECRET=...   # from Step 2 / GitHub form
   OPENROUTER_KEY=...   # from https://openrouter.ai/keys
   ALLOWED_USER=as9coder   # your GitHub username (lowercase is fine for login match)
   ```

3. Save the file.

---

## Step 11 — Point the webhook at your real URL (if you used a placeholder)

1. Start your tunnel and get `https://YOUR_HOST` (see main README).
2. GitHub App → **General** → **Webhook** → **Webhook URL** = `https://YOUR_HOST/webhook`
3. Click **Save changes**.
4. Optional: use **Redeliver** on a recent delivery in the **Advanced** / webhook delivery log to test (after your server is running).

---

## Step 12 — Install the app on your repos

1. Left sidebar → **Install App**.
2. Choose your user or org → **Only select repositories** or **All repositories** → select repos → **Install**.

---

## Step 13 — Run CodeRev and test

1. `.\scripts\run-local.ps1`
2. Tunnel: `cloudflared tunnel --url http://127.0.0.1:8080`
3. Confirm webhook URL matches the tunnel + `/webhook`.
4. Open a PR in an installed repo, comment **`@coderev`**.

---

## If something fails

| Symptom | What to check |
|---------|----------------|
| Webhook deliveries show **401** | `WEBHOOK_SECRET` in `.env` does not match GitHub (must be identical). |
| **404** on `/webhook` | Wrong URL path — must end with `/webhook`; server must be running. |
| **TLS / connection errors** | Tunnel not running or HTTPS URL wrong. |
| Review never posts | `ALLOWED_USER` must match the GitHub user who commented; comment must include `@coderev`. |
| **Bad JWT / installation** | Wrong `APP_ID` or bad/corrupt `github-app.pem`. |

---

## Official docs (extra reading)

- [Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
- [Securing webhooks](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
