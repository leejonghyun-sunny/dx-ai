import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보 (시범운영)", layout="wide", page_icon="📝")

# --- CSS 주입 ---
st.markdown("""
<style>
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    input[type=number] {
        -moz-appearance: textfield;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 내부 데이터 하드코딩 ---
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

PRODUCT_LIST = ["[기종 선택]"] + list(PRODUCT_DB.keys())
DEFECT_OUT_LIST = ["[없음]", "이음", "감소음", "찍힘", "파형"]
DOWNTIME_OUT_LIST = ["[없음]", "셋업", "부품", "품질", "기타"]

TIME_SLOTS = [
    {"time": "08:30~09:30", "duration": 60},
    {"time": "09:30~10:30", "duration": 60},
    {"time": "10:40~11:40", "duration": 60},
    {"time": "11:40~12:30", "duration": 50},
    {"time": "13:20~14:30", "duration": 70},
    {"time": "14:30~15:30", "duration": 60},
    {"time": "15:40~16:30", "duration": 50},
    {"time": "16:30~17:30", "duration": 60},
    {"time": "18:00~19:00", "duration": 60},
    {"time": "19:00~20:00", "duration": 60},
]

# --- 3. 타이틀 영역 ---
st.title("조립 1라인 실시간 작업일보 (시범운영)")

# --- 4. 기본 정보 ---
col1, col2 = st.columns(2)
with col1:
    work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col2:
    worker_name = st.text_input("👤 메인 작업자명", placeholder="이름 입력")

st.divider()

if 'row_data' not in st.session_state:
    st.session_state.row_data = []
    for i, slot in enumerate(TIME_SLOTS):
        st.session_state.row_data.append({"id": i, "time": slot["time"], "default_duration": slot["duration"], "is_added": False})
    st.session_state.next_id = len(TIME_SLOTS)

def cb_add_row(idx, time_str, default_dur):
    st.session_state.row_data.insert(idx + 1, {"id": st.session_state.next_id, "time": time_str, "default_duration": default_dur, "is_added": True})
    st.session_state.next_id += 1

def cb_delete_row(idx):
    st.session_state.row_data.pop(idx)

# --- 5. 그리드 헤더 ---
cols_ratio = [1.3, 0.7, 1.8, 0.8, 0.8, 1.0, 0.8, 1.0, 0.8, 1.0, 0.8]
h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11 = st.columns(cols_ratio)
h1.markdown("**시간대**"); h2.markdown("**투입분**"); h3.markdown("**기종명**")
h4.markdown("**목표**"); h5.markdown("**실적**"); h6.markdown("**불량명**")
h7.markdown("**불량**"); h8.markdown("**비가동사유**"); h9.markdown("**비가동분**")
h10.markdown("**지원자**"); h11.markdown("**관리**")

# --- 6. 데이터 행 생성 ---
for idx, slot in enumerate(st.session_state.row_data):
    row_id = slot['id']
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = st.columns(cols_ratio)
    
    # 1. 시간대
    if not slot['is_added']:
        c1.markdown(f"<div style='margin-top:5px;'>{slot['time']}<br><span style='font-size:0.8em; color:gray'>({slot['default_duration']}분)</span></div>", unsafe_allow_html=True)
    else:
        c1.markdown("<div style='margin-top:5px; color:blue;'>↳ (추가)</div>", unsafe_allow_html=True)
        
    # 2. 투입분
    invested_time = c2.number_input("투입분", value=slot['default_duration'] if not slot['is_added'] else 0, key=f"inv_time_{row_id}", label_visibility="collapsed")
    
    # 3. 기종선택
    row_product = c3.selectbox("기종", options=PRODUCT_LIST, key=f"prod_{row_id}", label_visibility="collapsed")

    # 4. 목표수량 자동계산
    target_qty = 0
    if row_product != "[기종 선택]":
        if invested_time in [50, 60, 70]:
            target_qty = PRODUCT_DB[row_product].get(invested_time, 0)
        else:
            base_60 = PRODUCT_DB[row_product].get(60, 0)
            target_qty = round((base_60 / 60.0) * invested_time)
            
    c4.markdown(f"<div style='margin-top:5px; font-weight:bold; text-align:center;'>{target_qty}</div>", unsafe_allow_html=True)
    
    # 5. 실적 등 입력
    actual = c5.number_input("실적", min_value=0, key=f"actual_{row_id}", label_visibility="collapsed")
    defect_name = c6.selectbox("불량명", options=DEFECT_OUT_LIST, key=f"defect_name_{row_id}", label_visibility="collapsed")
    defect_qty = c7.number_input("불량", min_value=0, key=f"defect_qty_{row_id}", label_visibility="collapsed")
    downtime_reason = c8.selectbox("비가동", options=DOWNTIME_OUT_LIST, key=f"down_name_{row_id}", label_visibility="collapsed")
    downtime_qty = c9.number_input("비가동분", min_value=0, key=f"down_qty_{row_id}", label_visibility="collapsed")
    supporter_name = c10.text_input("지원자", key=f"supporter_{row_id}", label_visibility="collapsed")

    # 11. 관리 버튼
    if not slot['is_added']:
        c11.button("➕", key=f"add_{row_id}", on_click=cb_add_row, args=(idx, slot['time'], slot['default_duration']))
    else:
        c11.button("❌", key=f"del_{row_id}", on_click=cb_delete_row, args=(idx,))

# --- 7. 전송 로직 (중요! 누락된 데이터 수정됨) ---
st.divider()
conn = st.connection("gsheets", type=GSheetsConnection)

if st.button("🚀 오늘의 작업일보 구글 시트로 최종 전송하기", use_container_width=True):
    data_to_send = []
    curr_t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = work_date.strftime("%Y-%m-%d")

    for s in st.session_state.row_data:
        r_id = s['id']
        # 기종명 가져오기
        p = st.session_state.get(f"prod_{r_id}", "[기종 선택]")
        
        # 기종이 선택된 행만 전송
        if p != "[기종 선택]":
            # 목표수량 재계산 (전송용)
            i_time = st.session_state.get(f"inv_time_{r_id}", 0)
            t_qty = 0
            if i_time in [50, 60, 70]:
                t_qty = PRODUCT_DB[p].get(i_time, 0)
            else:
                base_60 = PRODUCT_DB[p].get(60, 0)
                t_qty = round((base_60 / 60.0) * i_time)
            
            # 데이터 포장 (모든 항목 포함!)
            data_to_send.append({
                "Timestamp": curr_t,
                "Work_Date": date_str,
                "Worker_Name": worker_name,
                "Time_Slot": s['time'],
                "Invested_Min": i_time,
                "Item_Name": p,
                "Target_UPH": t_qty,  # 추가됨!
                "Actual_Qty": st.session_state.get(f"actual_{r_id}", 0),
                "Defect_Type": st.session_state.get(f"defect_name_{r_id}", "[없음]"), # 추가됨!
                "Defect_Qty": st.session_state.get(f"defect_qty_{r_id}", 0),
                "Downtime_Reason": st.session_state.get(f"down_name_{r_id}", "[없음]"), # 추가됨!
                "Downtime_Min": st.session_state.get(f"down_qty_{r_id}", 0),
                "Supporter": st.session_state.get(f"supporter_{r_id}", "")
            })

    if data_to_send:
        try:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(data_to_send)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            st.success(f"✅ 전송 완료! 총 {len(data_to_send)}건이 기록되었습니다."); st.balloons()
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {e}")
    else:
        st.warning("⚠️ 전송할 데이터가 없습니다. 기종을 선택해주세요.")