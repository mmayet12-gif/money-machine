# OAuth Setup for YouTube Uploader

You need a Google Cloud project with YouTube Data API v3 enabled and an OAuth
Desktop credential. This takes about 10 minutes the first time.

---

## Step 1 — Open Google Cloud Console

Go to <https://console.cloud.google.com/>

Sign in with the Google account that **owns** the YouTube channel you want to
upload to.

## Step 2 — Select or create a project

If you already created a project during the YouTube Data API research phase,
use that one. Otherwise:

- Click the project selector at the top of the page.
- Click **New Project**.
- Name it **Money Machine** (any name works).
- Click **Create**, then select it.

## Step 3 — Enable the YouTube Data API v3

1. In the left sidebar, go to **APIs & Services > Library**.
2. Search for **YouTube Data API v3**.
3. Click it, then click **Enable**.
4. Wait a few seconds for it to activate.

## Step 4 — Configure the OAuth Consent Screen

You only need to do this once per project.

1. Go to **APIs & Services > OAuth consent screen**.
2. Select **External** as the user type. Click **Create**.
3. Fill in:
   - **App name**: `Money Machine Uploader`
   - **User support email**: your own email address
   - **Developer contact**: same email
4. Click **Save and Continue**.
5. On the **Scopes** page, click **Add or Remove Scopes** and add:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
6. Click **Update**, then **Save and Continue**.
7. On the **Test users** page, click **Add Users** and enter the Gmail
   address that owns the YouTube channel.
8. Click **Save and Continue**, then **Back to Dashboard**.

> **Note**: The app stays in "Testing" mode. This is fine for personal use.
> The only downside is your OAuth token expires every 7 days, and you need
> to re-run `--authorize` (takes 30 seconds). Going through Google
> verification is unnecessary unless you plan to share this with other
> people.

## Step 5 — Create an OAuth Client ID

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. **Application type**: select **Desktop app**.
4. **Name**: `Money Machine Desktop`
5. Click **Create**.
6. On the confirmation dialog, click **Download JSON**.
7. Save the downloaded file to:
   ```
   C:\money-machine\config\client_secret.json
   ```

## Step 6 — First-time Authorization

Open a terminal and run:

```
cd C:\money-machine
python youtube_uploader.py --authorize
```

What happens:
- Your default browser opens to a Google sign-in page.
- Log in with the Google account that owns the channel.
- Grant the requested permissions (upload, read-only).
- The browser shows "The authentication flow has completed."
- The terminal prints "Authorization successful. Token saved."
- Token file saved at: `C:\money-machine\config\token.json`

**Do not share or commit `token.json`.** It grants upload access to your
channel.

## Step 7 — Verify

```
python youtube_uploader.py --whoami
```

Expected output:
```
Channel: Your Channel Name
Subscribers: 123
Videos: 45
```

If the wrong channel shows up, you authorized with the wrong Google account.
Delete `config\token.json` and re-run `--authorize` with the correct account.

---

## If You Get Stuck

### "Access blocked: This app's request is invalid" or "app not verified"

Your email is not listed as a test user.

1. Go to **APIs & Services > OAuth consent screen**.
2. Under **Test users**, click **Add Users**.
3. Enter the exact Gmail address you're trying to sign in with.
4. Try `--authorize` again.

### "Error 400: redirect_uri_mismatch"

You created a **Web application** credential instead of a **Desktop app**.

1. Go to **APIs & Services > Credentials**.
2. Delete the Web credential.
3. Create a new one with type **Desktop app**.
4. Download the new JSON and replace `config\client_secret.json`.

### "Token has been expired or revoked" (after ~7 days)

This is normal in Testing mode. Your token expires weekly.

```
python youtube_uploader.py --authorize
```

Takes 30 seconds. Browser opens, you click through, done.

---

## File Locations

| File | Path | Sensitive? |
|------|------|-----------|
| Client secret | `C:\money-machine\config\client_secret.json` | Yes - identifies your app |
| OAuth token | `C:\money-machine\config\token.json` | **Very** - grants upload access |
| Upload log | `C:\money-machine\logs\uploads.log` | No |
