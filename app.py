import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. 파일 설정
LOG_FILE = 'inspection_logs.csv'

st.set_page_config(page_title="정류자 가공 점검", page_icon="⚙️")
st.title("⚙️ 정류자 가공 표준화 점검 시스템")
st.info("현장 점검용 앱입니다. 수치를 입력하고 저장을 눌러주세요.")

# --- 2. 입력 구역 ---
with st.form("inspection_form"):
    st.subheader("📋 실시간 점검 항목")
    worker_name = st.text_input("작업자 성함")
    machine_id = st.selectbox("설비 번호", ["가공기 #1", "가공기 #2", "공통"])
    outer_diameter = st.number_input("정류자 외경 측정값 (mm)", format="%.3f", value=8.000)
    status = st.radio("판정", ["정상", "재작업", "폐기"], horizontal=True)
    
    submitted = st.form_submit_button("✅ 점검 결과 저장")
    
    if submitted:
        new_data = {
            "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "작업자": worker_name,
            "설비": machine_id,
            "외경": outer_diameter,
            "상태": status
        }
        df = pd.DataFrame([new_data])
        if not os.path.isfile(LOG_FILE):
            df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
        st.success("데이터가 저장되었습니다!")