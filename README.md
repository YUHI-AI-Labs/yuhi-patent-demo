# Yuhi Patent — Streamlit Demo

Public search demo over the JPO gazette corpus (real published patent
gazettes), separate from the Yuhi Patent desktop app. The desktop app is
local-first and does not ship JPO data — users import their own corpus. This
demo exists so people can try full-text search without installing anything.

## Local run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Rebuilding `patents.db`

```bash
python3 build_db.py /path/to/docs.jsonl patents.db
```

`docs.jsonl` is produced by `corpus-tools/fetch-gazette.mjs` (one JSON object
per line: `publication_number`, `title`, `abstract`, `claims`).

## Deploying

Push this repo to GitHub, then deploy on
[Streamlit Community Cloud](https://share.streamlit.io) pointing at
`demo-streamlit/streamlit_app.py`.
