# Putting FINN online (about 20 minutes of clicks, in this order)

Three free services, all signed in with GitHub as **fizzyappy**:

| Piece | Where | Why |
|---|---|---|
| Research engine (backend) | Render | Reads companies the app hasn't seen (ENAM may pick one) |
| The app | Vercel | The link you submit; works on any phone, installable |
| Daily data refresh + keep-warm | GitHub (already set up) | Fresh filings every weekday without your PC |

## 1. Research engine on Render (do this first)

1. Go to **render.com** → **Get Started** → **GitHub** → sign in as fizzyappy → allow Render to see the **Finn** repo.
2. Click **New +** → **Blueprint** → pick **Finn** → **Connect**. Render reads `render.yaml` (free plan).
3. It asks for **GEMINI_API_KEY**: paste a Gemini key. Best: make a fresh one at aistudio.google.com → Get API key
   (the old one was shared in chat). Click **Apply**.
4. Wait until it says **Live** (5–10 minutes the first time). Copy its address, e.g. `https://finn-api.onrender.com`.
5. Check it: open `https://finn-api.onrender.com/sources` in a browser. Each line should say `"ok": true`.
   If one says it was refused, the app still works and says which source is missing; tell me what it shows.

## 2. The app on Vercel

1. Go to **vercel.com** → **Sign Up / Log In** → **Continue with GitHub** → fizzyappy.
2. **Add New…** → **Project** → **Finn** → **Import**.
3. **Root Directory** → **Edit** → choose **frontend**.
4. Open **Environment Variables** and add: Name `VITE_API_BASE`, Value = the Render address from step 1.4
   (no slash at the end).
5. Click **Deploy**. Copy the link (e.g. `https://finn-xxxx.vercel.app`). On your phone: open it → **Add to Home Screen**.

## 3. Two GitHub settings (for fresh data and a warm server)

On github.com/fizzyappy/Finn → **Settings** → **Secrets and variables** → **Actions**:

1. Tab **Secrets** → **New repository secret** → Name `GEMINI_API_KEY` → paste the same key → **Add secret**.
2. Tab **Variables** → **New repository variable** → Name `FINN_API_URL` → the Render address → **Add variable**.
3. Optional first run: tab **Actions** → **refresh-data** → **Run workflow** → **Run workflow**.

What then happens on its own:
- Every weekday at 4:45 pm IST, GitHub rebuilds the app's data and Vercel republishes the app.
- Every 10 minutes GitHub pings the research engine so reviewers rarely wait for it to wake up.

## Good to know
- Render's free server sleeps after 15 minutes idle; the app shows "Waking up the research engine (up to 50 s)".
- Its disk is temporary; it starts from a small seed of saved answers, so restarts do not cost new AI calls.
- If any data source refuses the cloud server, answers say which source is missing instead of failing.
