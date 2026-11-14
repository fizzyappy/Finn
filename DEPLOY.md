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

## 1b. No card? Use a Hugging Face Space instead of Render (free, no card)

Render now asks new accounts for a card. A Hugging Face Space does the same job for free without one.
Use **either** Render **or** this, not both. Wherever these steps say "the Render address", use the Space address instead.

1. Go to **huggingface.co** → **Sign up** (email + password) → confirm the email they send you.
2. Top right, your picture → **New Space**.
   - Space name: `finn-api` · License: leave blank · **Space SDK: Docker** → template **Blank**
   - Hardware: **CPU basic · Free** · Visibility: **Public**
   - **Create Space**.
3. On the new Space page: **Files** tab → **+ Add file** → **Create a new file**.
   - File name: `Dockerfile`. Paste everything from `hf-space/Dockerfile` in the GitHub repo
     (open it on github.com → **Raw** → select all → copy). **Commit new file to main**.
4. Same again for `README.md`: **Files** → click `README.md` → **edit** (pencil) → replace everything with the contents
   of `hf-space/README.md` from GitHub → **Commit changes to main**. (Keep the lines between the `---` marks exactly.)
5. **Settings** tab → **Variables and secrets** → **New secret** → Name `GEMINI_API_KEY`, Value: your **new** Gemini key
   → **Save**. (A *secret*, not a variable, so nobody can see it.)
6. Click **App** at the top. It builds for 5–10 minutes, then says **Running**.
7. Your address is `https://<your-username>-finn-api.hf.space` (also under the ⋮ menu → **Embed this Space** → "Direct URL").
   Check it: open that address + `/health` in a browser. It should show `{"ok":true}`.
8. Use this address for `VITE_API_BASE` on Vercel and `FINN_API_URL` on GitHub (sections 2 and 3).

To load newer code from GitHub later: Space → **Settings** → **Factory rebuild**.

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
