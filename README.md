# SQLi Comment Box Challenge

## Run

```powershell
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Render

Add an environment variable named `FLAG` in Render before deploying. The app uses
`UITCTF{local_flag_placeholder}` only when `FLAG` is not set.

## Vercel

1. Push this repository to GitHub.
2. In Vercel, choose Add New Project and import the GitHub repository.
3. Leave Framework Preset as Other if Vercel does not auto-detect Flask.
4. Do not set a Start Command. Vercel loads `app.py` automatically.
5. Add an environment variable named `FLAG`.
6. Deploy.
