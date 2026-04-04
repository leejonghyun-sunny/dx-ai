import streamlit as st
from streamlit_gsheets import GSheetsConnection

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="sheet1", ttl=0)
    print("Read successful. Rows:", len(df))
except Exception as e:
    print("Error during read:", type(e).__name__, "-", e)
