# Deploying FINN (not done yet: needs your sign-ins)

Two pieces. The **app** alone is enough for the submission link: it ships a snapshot of real
data and works without the backend. The **backend** adds live research for companies that
are not in the snapshot.

## 1. The app on Vercel (about 5 minutes)

1. Go to vercel.com → **Sign up / Log in** → **Continue with GitHub** → sign in as **fizzyappy**.
2. Click **Add New… → Project**.
3. Find **Finn** in the list → **Import**. (If it isn't listed: **Adjust GitHub App Permissions** → allow the Finn repo.)
4. On the configure screen, set **Root Directory** to `frontend` (click **Edit** next to it).
   Framework should show **Vite** automatically. Leave the build settings as they are.
5. Click **Deploy**. When it finishes, copy the link (like `https://finn-xxxx.vercel.app`).
6. Open the link on your phone → browser menu → **Add to Home Screen** to install it as an app.

## 2. The backend on Render (optional, about 10 minutes)

1. Go to render.com → **Get Started** → **GitHub** → sign in as **fizzyappy**.
2. Click **New + → Blueprint** → choose the **Finn** repo → **Connect**. Render reads `render.yaml`.
3. It asks for **GEMINI_API_KEY**: paste a Gemini key (make a fresh one at aistudio.google.com;
   the one shared in chat should be replaced). Click **Apply**.
4. Wait for the deploy to show **Live**, then copy the URL (like `https://finn-api.onrender.com`).
5. In the FINN app → **Settings → Live backend**, paste that URL → **Connect**.

Notes
- Render's free plan sleeps after 15 minutes idle; the first request after that takes ~1 minute.
- Its disk is temporary, so the backend's cache starts empty after a restart (it refills as it works).
- BSE/NSE may treat a cloud server differently from this PC; the app always shows which sources answered.
