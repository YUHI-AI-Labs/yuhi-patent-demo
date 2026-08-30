"""Convert the scraped JPO gazette corpus (docs.jsonl) into a compact SQLite
database for the public Streamlit demo.

Usage:
    python3 build_db.py /path/to/docs.jsonl patents.db

Design notes (kept deliberately lean to fit a normal `git push`, no Git LFS,
on GitHub's 100MB single-file limit):

- No FTS5 index. A trigram FTS index over claims text alone inflated a first
  attempt to >1GB (trigram indexes are several times larger than the source
  text). Title/abstract are small and searched with plain SQL LIKE instead,
  which is fast enough for ~37k rows and avoids that blowup entirely.
- claims_text is zlib-compressed (Japanese patent claim boilerplate
  compresses ~6x) and only decompressed for the one document a user opens,
  never scanned in bulk.
- Any single text field longer than FIELD_CAP is truncated. This isn't just
  size hygiene: a subset of the scraped records (mostly 遊技機 claims)
  contain a parser bug that repeats the same short claim text hundreds of
  times, inflating a handful of records to 10MB+. Capping neutralizes that
  without needing to detect it case by case.
"""
import json
import sqlite3
import sys
import zlib

FIELD_CAP = 1500
TRUNC_MARK = "\n…（以下略）"


def cap(text: str) -> str:
    if text is None:
        return ""
    if len(text) <= FIELD_CAP:
        return text
    return text[:FIELD_CAP] + TRUNC_MARK


def claims_text(claims: list) -> str:
    parts = []
    for c in claims or []:
        no = c.get("no")
        text = c.get("text") or ""
        parts.append(f"【請求項{no}】\n{text}")
    # Cap applies to the joined text, not per claim: capping per claim doesn't
    # bound total size when a document has dozens of claims.
    return cap("\n\n".join(parts))


def main() -> None:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <docs.jsonl> <out.db>", file=sys.stderr)
        raise SystemExit(1)
    src_path, db_path = sys.argv[1], sys.argv[2]

    con = sqlite3.connect(db_path)
    con.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;

        CREATE TABLE documents (
            publication_number TEXT PRIMARY KEY,
            country TEXT,
            kind_code TEXT,
            title TEXT,
            abstract TEXT,
            claims_text_z BLOB,
            n_claims INTEGER
        );
        """
    )

    insert_doc = (
        "INSERT OR IGNORE INTO documents "
        "(publication_number, country, kind_code, title, abstract, claims_text_z, n_claims) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )

    n = 0
    skipped = 0
    with open(src_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            pub = rec.get("publication_number")
            if not pub:
                skipped += 1
                continue

            title = cap(rec.get("title") or "")
            abstract = cap(rec.get("abstract") or "")
            claims = rec.get("claims") or []
            ctext = claims_text(claims)
            ctext_z = zlib.compress(ctext.encode("utf-8"), 9)

            con.execute(
                insert_doc,
                (pub, rec.get("country"), rec.get("kind_code"), title, abstract, ctext_z, len(claims)),
            )

            n += 1
            if n % 5000 == 0:
                print(f"  {n} imported...", file=sys.stderr)

    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"done: {n} imported, {skipped} skipped -> {db_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
