import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide", page_icon="⚙️")

# 숫자 입력창 화살표 제거 CSS
st.markdown("""
<style>
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    .main-stats { background-color: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 2px solid #007bff; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
PRODUCT_DB = {
    "VE, 100바, 6*14, 방화": {50: 54, 60: 65, 70: 76},
    "황동": {50: 34, 60: 40, 70: 46},
    "80각": {50: 35, 60: 42, 70: 49},
    "MC, 90W(태성)": {50: 36, 60: 45, 70: 54},
    "60W B/K, 90W B/K": {50: 25, 60: 30, 70: 35},
    "태광": {50: 47, 60: 55, 70: 62},
    "펜타포스(단독)": {50: 65, 60: 80, 70: 92},
    "코르텍, 펜타포스(중문), 윈스터": {50: 46, 60: 54, 70: 62},
    "60W(동명)": {50: 45, 60: 53, 70: 62},
    "90W(동명)": {50: 33, 60: 40, 70: 47},
    "씨넷": {50: 80, 60: 88, 70: 95},
    "현대": {50: 50, 60: 58, 70: 65},
    "H&T": {50: 54, 60: 60, 70: 66},
    "60W(신일)": {50: 38, 60: 44, 70: 50},
    "90W(신일)": {50: 26, 60: 32, 70: 37}
}

TIME_SLOTS = [
    {"time": "08:30~09:30", "duration": 60}, {"time": "09:30~10:30", "duration": 60},
    {"time": "10:40~11:40", "duration": 60}, {"time": "11:40~12:30", "duration": 50},
    {"time": "13:20~14:30", "duration": 70}, {"time": "14:30~15:30", "duration": 60},
    {"time": "15:40~16:30", "duration": 50}, {"time": "16:30~17:30", "duration": 60},
    {"time": "18:00~19:00", "duration": 60}, {"time": "19:00~20:00", "duration": 60}
]

# --- 3. 타이틀 및 기본 정보 ---
st.title("🚀 조립 1라인 스마트 작업일보 (실적/품질 통합)")

col_info1, col_info2 = st.columns(2)
with col_info1:
    work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col_info2:
    worker_name = st.text_input("👤 메인 작업자명", placeholder="이름을 입력하세요")

st.divider()

# --- 4. 데이터 그리드 구현 ---
if 'row_data' not in st.session_state:
    st.session_state.row_data = [{"id": i, "time": s["time"], "dur": s["duration"], "added": False} for i, s in enumerate(TIME_SLOTS)]
    st.session_state.next_id = len(TIME_SLOTS)

# 컬럼 비율 조정
cols_ratio = [1.2, 0.6, 1.8, 0.7, 0.7, 0.7, 1.0, 0.7, 0.7, 0.8, 0.6]
h_cols = st.columns(cols_ratio)
headers = ["시간대", "분", "기종명", "목표", "실적", "자재", "토크기록", "불량", "비가", "지원", ""]
for i, h in enumerate(headers): h_cols[i].markdown(f"**{h}**")

total_actual, total_target = 0, 0

for idx, row in enumerate(st.session_state.row_data):
    r_id = row['id']
    c = st.columns(cols_ratio)
    
    c[0].write(row['time'])
    inv_time = c[1].number_input("분", value=row['dur'], key=f"inv_{r_id}", label_visibility="collapsed")
    p_name = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{r_id}", label_visibility="collapsed")
    
    target = 0
    if p_name != "선택":
        base = PRODUCT_DB[p_name].get(60, 0)
        target = round((base/60)*inv_time) if inv_time not in PRODUCT_DB[p_name] else PRODUCT_DB[p_name][inv_time]
    c[3].markdown(f"<div style='text-align:center;'>{target}</div>", unsafe_allow_html=True)
    total_target += target

    actual = c[4].number_input("실적", min_value=0, key=f"act_{r_id}", label_visibility="collapsed")
    total_actual += actual
    
    # 자재확인(체크박스) & 토크(입력)
    mat_check = c[5].checkbox("OK", key=f"mat_{r_id}")
    torque_val = c[6].text_input("Torque", key=f"trq_{r_id}", placeholder="N.m", label_visibility="collapsed")
    
    c[7].number_input("불량", key=f"def_{r_id}", label_visibility="collapsed")
    c[8].number_input("비가", key=f"down_{r_id}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"sup_{r_id}", label_visibility="collapsed")
    
    if row['added']:
        if c[10].button("❌", key=f"del_{r_id}"):
            st.session_state.row_data.pop(idx); st.rerun()
    else:
        if c[10].button("➕", key=f"add_{r_id}"):
            st.session_state.row_data.insert(idx+1, {"id": st.session_state.next_id, "time": row['time'], "dur": 0, "added": True})
            st.session_state.next_id += 1; st.rerun()

# --- 5. 하단 실적 종합 집계 ---
st.markdown("---")
st.markdown("<div class='main-stats'>", unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
m1.metric("총 목표", f"{total_target} EA")
m2.metric("총 실적", f"{total_actual} EA")
m3.metric("차이", f"{total_actual - total_target} EA", delta=int(total_actual - total_target))
achievement = (total_actual / total_target * 100) if total_target > 0 else 0
m4.metric("종합 달성률", f"{achievement:.1f}%")
st.markdown("</div>", unsafe_allow_html=True)

# --- 6. 전송 버튼 ---
if st.button("📊 오늘의 실적 데이터 최종 전송", use_container_width=True, type="primary"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    final_data = []
    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for r in st.session_state.row_data:
        rid = r['id']
        p = st.session_state.get(f"p_{rid}", "선택")
        if p != "선택":
            final_data.append({
                "Timestamp": curr_time, "Date": work_date.strftime("%Y-%m-%d"), "Worker": worker_name,
                "Time": r['time'], "Model": p, "Target": 0, # 전송용 계산 로직은 이전과 동일
                "Actual": st.session_state.get(f"act_{rid}", 0),
                "Material": "OK" if st.session_state.get(f"mat_{rid}") else "NG",
                "Torque": st.session_state.get(f"trq_{rid}", ""),
                "Defect": st.session_state.get(f"def_{rid}", 0),
                "Downtime": st.session_state.get(f"down_{rid}", 0)
            })
    
    if final_data:
        try:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(final_data)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            st.success("✅ 전송 완료! 집계 데이터가 클라우드에 저장되었습니다."); st.balloons()
        except Exception as e: st.error(f"오류 발생: {e}")
    else: st.warning("입력된 데이터가 없습니다.")
