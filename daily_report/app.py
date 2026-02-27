import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 (이사님 취향의 다크/와이드 레이아웃) ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide")

# UI 복구를 위한 맞춤형 CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 20px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; color: #58a6ff; }
    .stButton>button { width: 100%; height: 50px; font-weight: bold; background-color: #238636; color: white; }
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

TIME_SLOTS = ["08:30~09:30", "09:30~10:30", "10:40~11:40", "11:40~12:30", "13:20~14:30", "14:30~15:30", "15:40~16:30", "16:30~17:30", "18:00~19:00", "19:00~20:00"]

# --- 3. 헤더 영역 ---
st.title("⚙️ 조립 1라인 실시간 스마트 작업일보")

col_top1, col_top2 = st.columns(2)
with col_top1:
    work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col_top2:
    worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 메인 작업 테이블 ---
st.markdown("<div class='section-title'>📊 시간대별 생산 실적 기록</div>", unsafe_allow_html=True)
cols_r = [1.2, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8]
headers = ["시간대", "투입분", "기종명", "목표", "실적", "불량명", "불량", "비가동사유", "비가동분", "지원자"]
h_cols = st.columns(cols_r)
for i, h in enumerate(headers):
    h_cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#8b949e;'>{h}</div>", unsafe_allow_html=True)

total_actual, total_target = 0, 0

for i, slot in enumerate(TIME_SLOTS):
    c = st.columns(cols_r)
    c[0].write(f"**{slot}**")
    
    # 투입분 (기본값 설정)
    default_min = 60 if i not in [3, 6] else 50
    inv_m = c[1].number_input("분", value=default_min, key=f"m_{i}", label_visibility="collapsed")
    
    # 기종 및 목표
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{i}", label_visibility="collapsed")
    target = 0
    if p_sel != "선택":
        base_60 = PRODUCT_DB[p_sel].get(60, 0)
        target = PRODUCT_DB[p_sel].get(inv_m, round((base_60/60)*inv_m))
    c[3].markdown(f"<div style='text-align:center;'>{target}</div>", unsafe_allow_html=True)
    total_target += target

    # 실적 및 부가정보
    actual = c[4].number_input("실적", min_value=0, key=f"a_{i}", label_visibility="collapsed")
    total_actual += actual
    
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형", "기타"], key=f"dt_{i}", label_visibility="collapsed")
    c[6].number_input("불량", key=f"dq_{i}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질", "설비"], key=f"dr_{i}", label_visibility="collapsed")
    c[8].number_input("비가", key=f"dm_{i}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"sup_{i}", label_visibility="collapsed")

# --- 5. 실적 집계 지표 ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("생산 목표", f"{total_target} EA")
m2.metric("생산 실적", f"{total_actual} EA")
diff = total_actual - total_target
m3.metric("목표 대비", f"{diff} EA", delta=int(diff))
achieve = (total_actual / total_target * 100) if total_target > 0 else 0
m4.metric("종합 달성률", f"{achieve:.1f}%")

# --- 6. 품질 및 부가 정보 (이사님 요청 사항 - 하단 배치) ---
st.markdown("<div class='section-title'>🔍 품질 점검 및 부가 정보</div>", unsafe_allow_html=True)
q_col1, q_col2 = st.columns(2)

with q_col1:
    st.subheader("📦 자재 확인 (Material Check)")
    mat_check = st.checkbox("금일 투입 자재 이상 없음 (OK)", value=True)
    mat_memo = st.text_input("자재 관련 특이사항", placeholder="LOT 번호 등 입력")

with q_col2:
    st.subheader("🔧 전동 드라이버 토크 점검")
    torque_val = st.text_input("측정된 토크 값 (N.m)", placeholder="예: 3.5 / 3.4 / 3.5")

# --- 7. 최종 구글 시트 전송 로직 ---
st.markdown("---")
if st.button("📊 오늘의 실적 데이터 최종 전송 및 저장", type="primary"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    final_data = []
    # 시트 헤더 'Timestamp'와 일치 (이사님 수정 반영)
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for i, slot in enumerate(TIME_SLOTS):
        p = st.session_state.get(f"p_{i}", "선택")
        if p != "선택":
            # 이사님의 구글 시트 헤더 명칭과 100% 일치
            final_data.append({
                "Timestamp": now_ts,
                "Work_Date": work_date.strftime("%Y-%m-%d"),
                "Worker_Name": worker_name,
                "Time_Slot": slot,
                "Invested_Min": st.session_state.get(f"m_{i}", 0),
                "Item_Name": p,
                "Target_UPH": 0, # 필요 시 자동 계산 로직 추가 가능
                "Actual_Qty": st.session_state.get(f"a_{i}", 0),
                "Defect_Type": st.session_state.get(f"dt_{i}", "없음"),
                "Defect_Qty": st.session_state.get(f"dq_{i}", 0),
                "Downtime_Reas": st.session_state.get(f"dr_{i}", "없음"),
                "Downtime_Min": st.session_state.get(f"dm_{i}", 0),
                "Supporter": st.session_state.get(f"sup_{i}", ""),
                "Material_Check": "OK" if mat_check else "NG",
                "Torque_Value": torque_val
            })
    
    if final_data:
        try:
            # 기존 데이터 읽기 및 병합
            df = conn.read(worksheet="Sheet1")
            new_df = pd.DataFrame(final_data)
            updated_df = pd.concat([df, new_df], ignore_index=True)
            
            # 시트 업데이트
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("✅ 실적 및 품질 데이터가 구글 시트에 성공적으로 저장되었습니다!"); st.balloons()
        except Exception as e:
            st.error(f"❌ 전송 실패: {e}\n\n시트의 헤더 명칭과 코드의 항목명이 일치하는지 확인해 주세요.")
    else:
        st.warning("⚠️ 입력된 데이터가 없습니다. 기종을 먼저 선택해 주세요.")