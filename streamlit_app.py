import sqlite3
import zlib
from pathlib import Path

import streamlit as st

DB_PATH = Path(__file__).parent / "patents.db"

st.set_page_config(page_title="Yuhi Patent Demo", page_icon="🔍", layout="wide")


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


@st.cache_data
def count_documents() -> int:
    con = get_connection()
    return con.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]


def search(query: str, limit: int = 30):
    con = get_connection()
    terms = [t for t in query.split() if t]
    if not terms:
        return []
    clauses = []
    params: list[str] = []
    for t in terms:
        clauses.append("(title LIKE ? OR abstract LIKE ?)")
        like = f"%{t}%"
        params.extend([like, like])
    sql = f"""
        SELECT publication_number, title, abstract, n_claims
        FROM documents
        WHERE {' AND '.join(clauses)}
        LIMIT ?
    """
    params.append(limit)
    return con.execute(sql, params).fetchall()


def get_claims_text(pub: str) -> str:
    con = get_connection()
    row = con.execute("SELECT claims_text_z FROM documents WHERE publication_number = ?", (pub,)).fetchone()
    if row is None or row["claims_text_z"] is None:
        return ""
    return zlib.decompress(row["claims_text_z"]).decode("utf-8")


st.title("🔍 Yuhi Patent — 先行技術検索デモ")
st.caption(
    f"特許庁 公報発行サイトから取得した実際の公開公報 {count_documents():,} 件を対象にした検索デモです。"
    "本番の Yuhi Patent デスクトップアプリは、CAD設計データから技術要素を抽出して自動でこの検索を行います。"
    "ここではキーワード検索のみを体験できます。"
)

with st.sidebar:
    st.header("このデモについて")
    st.markdown(
        "- データ元: 特許庁 公報発行サイト（公開特許公報）\n"
        "- 検索対象: 発明の名称・要約（スペース区切りキーワードのAND検索）\n"
        "- 請求項全文は各文献を開くと表示されます\n"
        "\n"
        "本デモは技術検証・研究目的の非商用デモです。"
    )

query = st.text_input("検索キーワード（発明の内容・技術用語など、スペース区切りで複数可）", placeholder="例: スマートシティ AIエージェント")

if query.strip():
    results = search(query)
    st.write(f"**{len(results)} 件** ヒット")
    for row in results:
        with st.expander(f"{row['title']} — {row['publication_number']}"):
            st.markdown(f"**要約:** {row['abstract']}")
            if st.button("請求項を全文表示", key=f"show_{row['publication_number']}"):
                st.text(get_claims_text(row["publication_number"]))
else:
    st.info("キーワードを入力すると検索結果が表示されます。")
