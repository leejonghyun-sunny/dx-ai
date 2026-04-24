import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
try:
    print('Connecting...')
    conn = st.connection('gsheets', type=GSheetsConnection)
    url = 'https://docs.google.com/spreadsheets/d/1wQQiJ2j2Bl7tOkdt9-_IKXsNDtdvUqlXqtgcrWWj6Rs/edit?usp=sharing'
    
    print('Testing READ...')
    df = conn.read(spreadsheet=url, worksheet='임시저장', ttl=0)
    print(f'READ successful! Loaded {len(df)} rows.')
except Exception as e:
    print("ERROR:", type(e).__name__, "-", str(e))

