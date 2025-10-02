# streamlit_app.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# Optional: fall back to st.secrets if env not set
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY.")
    st.stop()

from supabase import create_client

st.set_page_config(page_title="Quotes Dashboard", layout="wide")

@st.cache_data(ttl=60)
def fetch_latest(limit=200):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # adjust table name / columns to your schema
    resp = client.table("quotes").select("*").order("updated_at", desc=True).limit(limit).execute()
    rows = resp.data or []
    df = pd.DataFrame(rows)
    if not df.empty and "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
        df["updated_date"] = df["updated_at"].dt.date
    return df

st.title("📚 Quotes — Latest Records")

limit = st.sidebar.number_input("Rows to load", min_value=10, max_value=5000, value=200, step=50)
df = fetch_latest(limit)

if df.empty:
    st.info("No records found in `quotes`.")
    st.stop()

# Reorder columns (put updated_at/id first if present)
cols = [c for c in ["updated_at", "id", "author", "quote", "source_url"] if c in df.columns]
cols += [c for c in df.columns if c not in cols]
st.dataframe(df[cols], use_container_width=True, hide_index=True)

st.subheader("Quick visuals")

# 1) Count by author (top 15)
if "author" in df.columns:
    top_authors = df["author"].fillna("(unknown)").value_counts().head(15).reset_index()
    top_authors.columns = ["author", "count"]
    st.bar_chart(top_authors.set_index("author"))

# 2) New items per day
if "updated_date" in df.columns:
    per_day = df.groupby("updated_date").size().reset_index(name="count").sort_values("updated_date")
    st.line_chart(per_day.set_index("updated_date"))

# 3) Quote length distribution (if quote column exists)
if "quote" in df.columns:
    lengths = df["quote"].fillna("").map(len)
    st.write("Quote length summary:", lengths.describe())
    st.histogram(lengths, bins=20)