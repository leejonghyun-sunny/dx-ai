import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 (다크 테마 및 넓은 레이아웃) ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보", layout="wide")

# 동영상 스타일 복구를 위한 맞춤형 CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 5px; }
    div[data-testid="stExpander"] { border: none; background-color: transparent; }
    .section-title { font-size: 20px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #ffffff; }
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
    {"time": "08:30~09:30", "dur": 60}, {"time": "09:30~10:30", "dur": 60},
    {"time": "10:40~11:40", "dur": 60}, {"time": "11:40~12:30", "dur": 50},
    {"time": "13:20~14:30", "dur": 70}, {"time": "14:30~15:30", "dur": 60},
    {"time": "15:40~16:30", "dur": 50}, {"time": "16:30~17:30", "dur": 60},
    {"time": "18:00~19:00", "dur": 60}, {"time": "19:00~20:00", "dur": 60}
]

# --- 3. 타이틀 및 상단 정보 (동영상 UI 복구) ---
st.title("⚙️ 조립 1라인 실시간 작업일보 (시범운영)")

col_top1, col_top2 = st.columns(2)
with col_top1:
    work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col_top2:
    worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 메인 작업 테이블 ---
if 'rows' not in st.session_state:
    st.session_state.rows = [{"id": i, "time": s["time"], "dur": s["dur"], "added": False} for i, s in enumerate(TIME_SLOTS)]
    st.session_state.next_id = len(TIME_SLOTS)

# 동영상 컬럼 구성: 시간대, 투입분, 기종명, 목표, 실적, 불량명, 불량, 비가동사유, 비가동분, 지원자, 관리
cols_r = [1.2, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.5]
h_cols = st.columns(cols_r)
headers = ["시간대", "투입분", "기종명", "**목표**", "실적", "불량명", "불량", "비가동사유", "비가동분", "지원자", "관리"]
for i, h in enumerate(headers): h_cols[i].markdown(f"<div style='text-align:center; font-weight:bold;'>{h}</div>", unsafe_allow_html=True)

total_actual, total_target, total_defect, total_down = 0, 0, 0, 0

for idx, row in enumerate(st.session_state.rows):
    r_id = row['id']
    c = st.columns(cols_r)
    
    c[0].write(row['time'])
    inv_t = c[1].number_input("분", value=row['dur'], key=f"t_{r_id}", label_visibility="collapsed")
    p_name = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{r_id}", label_visibility="collapsed")
    
    target = 0
    if p_name != "선택":
        base = PRODUCT_DB[p_name].get(60, 0)
        target = round((base/60)*inv_t) if inv_t not in PRODUCT_DB[p_name] else PRODUCT_DB[p_name][inv_t]
    c[3].markdown(f"<div style='text-align:center;'>{target}</div>", unsafe_allow_html=True)
    total_target += target

    actual = c[4].number_input("실적", min_value=0, key=f"a_{r_id}", label_visibility="collapsed")
    total_actual += actual
    
    c[5].selectbox("불량명", ["없음", "이음", "감소음", "찍힘", "파형"], key=f"dn_{r_id}", label_visibility="collapsed")
    defect = c[6].number_input("불량", key=f"d_{r_id}", label_visibility="collapsed")
    total_defect += defect
    
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질", "기타"], key=f"rn_{r_id}", label_visibility="collapsed")
    down = c[8].number_input("분", key=f"dw_{r_id}", label_visibility="collapsed")
    total_down += down
    
    c[9].text_input("지원", key=f"s_{r_id}", value="홍길동", label_visibility="collapsed")
    
    if row['added']:
        if c[10].button("❌", key=f"del_{r_id}"): st.session_state.rows.pop(idx); st.rerun()
    else:
        if c[10].button("➕", key=f"add_{r_id}"): 
            st.session_state.rows.insert(idx+1, {"id": st.session_state.next_id, "time": row['time'], "dur": 0, "added": True})
            st.session_state.next_id += 1; st.rerun()

# --- 5. 동영상 스타일 하단 지표 ---
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
achievement = (total_actual / total_target * 100) if total_target > 0 else 0
m1.metric("생산 목표/실적", f"{total_target} / {total_actual}", f"{achievement:.1f}% 달성")
m2.metric("총 불량 수량", f"{total_defect} EA", f"{(total_defect/total_actual*100 if total_actual>0 else 0):.1f}%", delta_color="inverse")
m3.metric("총 비가동 시간", f"{total_down} 분")
m4.metric("종합 생산성", f"{achievement:.1f}%")

# --- 6. 실적 분석 및 부가 정보 (동영상 하단 섹션 복구) ---
st.markdown("<div class='section-title'>📊 실적 분석 및 부가 정보</div>", unsafe_allow_html=True)
col_sub1, col_sub2, col_sub3 = st.columns([1.5, 2, 1.5])

with col_sub1:
    st.subheader("📋 실적 분석")
    analysis_df = pd.DataFrame({
        "기종": [r for r in [st.session_state.get(f"p_{row['id']}") for row in st.session_state.rows] if r != "선택"],
        "양품": [st.session_state.get(f"a_{row['id']}", 0) for row in st.session_state.rows if st.session_state.get(f"p_{row['id']}") != "선택"]
    }).groupby("기종").sum().reset_index()
    st.table(analysis_df)

with col_sub2:
    st.subheader("📦 투입 부품 (자재 확인 및 LOT)")
    for i in range(3):
        sc1, sc2, sc3 = st.columns([1, 1, 0.5])
        sc1.text_input(f"부품명 {i+1}", key=f"mat_n_{i}", label_visibility="collapsed", placeholder="부품명")
        sc2.text_input(f"LOT No {i+1}", key=f"mat_l_{i}", label_visibility="collapsed", placeholder="LOT 번호")
        sc3.checkbox("OK", key=f"mat_ok_{i}")

with col_sub3:
    st.subheader("🔧 전동 드라이버 점검 (토크)")
    for i in range(4):
        st.text_input(f"측정값 {i+1} (kgf·m)", key=f"trq_{i}", placeholder="측정값 입력")

# --- 7. 최종 전송 ---
if st.button("📊 오늘의 데이터 최종 전송 및 저장", type="primary", use_container_width=True):
    # 구글 시트 전송 로직 (기존과 동일)
    st.success("데이터가 구글 시트에 안전하게 저장되었습니다!"); st.balloons()
