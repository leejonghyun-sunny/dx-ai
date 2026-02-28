import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 (다크 테마 유지) ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 10px; color: #58a6ff; border-left: 4px solid #58a6ff; padding-left: 10px; }
    .stButton>button { width: 100%; height: 50px; background-color: #238636; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (기종별 단독 선택형으로 완전 분리) ---
# UPH가 같더라도 기종명을 각각의 키로 분리하여 선택 시 혼선 제거
PRODUCT_DB = {
    "VE, 100바, 6*14, 방화": {50: 54, 60: 65, 70: 76},
    "황동": {50: 34, 60: 40, 70: 46},
    "80각": {50: 35, 60: 42, 70: 49},
    "MC, 90W(태성)": {50: 36, 60: 45, 70: 54},
    "60W B/K": {50: 25, 60: 30, 70: 35},
    "90W B/K": {50: 25, 60: 30, 70: 35},
    "태광": {50: 47, 60: 55, 70: 62},
    "펜타포스(단독)": {50: 65, 60: 80, 70: 92},
    "코르텍": {50: 46, 60: 54, 70: 62},
    "펜타포스(중문)": {50: 46, 60: 54, 70: 62},
    "윈스터": {50: 46, 60: 54, 70: 62},
    "60W(동명)": {50: 45, 60: 53, 70: 62},
    "90W(동명)": {50: 33, 60: 40, 70: 47},
    "씨넷": {50: 80, 60: 88, 70: 95},
    "현대": {50: 50, 60: 58, 70: 65},
    "H&T": {50: 54, 60: 60, 70: 66},
    "60W(신일)": {50: 38, 60: 44, 70: 50},
    "90W(신일)": {50: 26, 60: 32, 70: 37}
}

TIME_SLOTS = ["08:30~09:30", "09:30~10:30", "10:40~11:40", "11:40~12:30", "13:20~14:30", "14:30~15:30", "15:40~16:30", "16:30~17:30", "18:00~19:00", "19:00~20:00"]

# --- 3. 기본 정보 ---
st.title("⚙️ 조립 1라인 실시간 작업일보")

c1, c2 = st.columns(2)
with c1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c2: worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 메인 실적 테이블 (동영상 레이아웃 복구) ---
st.markdown("<div class='section-title'>📊 실시간 생산 기록</div>", unsafe_allow_html=True)
cols_r = [1.2, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8]
headers = ["시간대", "투입분", "기종명", "목표", "실적", "불량명", "불량", "비가동사유", "비가동분", "지원자"]
h_cols = st.columns(cols_r)
for i, h in enumerate(headers): h_cols[i].markdown(f"**{h}**")

total_actual, total_target, total_defect = 0, 0, 0

for i, slot in enumerate(TIME_SLOTS):
    c = st.columns(cols_r)
    c[0].write(slot)
    def_m = 60 if i not in [3, 6] else 50
    inv_m = c[1].number_input("분", value=def_m, key=f"m_{i}", label_visibility="collapsed")
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{i}", label_visibility="collapsed")
    
    target = 0
    if p_sel != "선택":
        base = PRODUCT_DB[p_sel].get(60, 0)
        target = PRODUCT_DB[p_sel].get(inv_m, round((base/60)*inv_m))
    c[3].write(f"{target}")
    total_target += target

    actual = c[4].number_input("실적", min_value=0, key=f"a_{i}", label_visibility="collapsed")
    total_actual += actual
    
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{i}", label_visibility="collapsed")
    defect = c[6].number_input("불량", key=f"dq_{i}", label_visibility="collapsed")
    total_defect += defect
    
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{i}", label_visibility="collapsed")
    c[8].number_input("비가", key=f"dm_{i}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"s_{i}", label_visibility="collapsed")

# --- 5. 실적 분석 및 부가정보 (이사님 요청 사항 1번 완벽 반영) ---
st.markdown("<div class='section-title'>📋 실적 분석 및 품질 추적 (LOT)</div>", unsafe_allow_html=True)
# 실적 입력 시 기종별 자동 집계 및 양품/불량/LOT 입력란 구성
summary_data = []
for i in range(len(TIME_SLOTS)):
    p = st.session_state.get(f"p_{i}", "선택")
    if p != "선택":
        summary_data.append({
            "기종": p,
            "실적": st.session_state.get(f"a_{i}", 0),
            "불량": st.session_state.get(f"dq_{i}", 0)
        })

if summary_data:
    df_sum = pd.DataFrame(summary_data).groupby("기종").sum().reset_index()
    for idx, row in df_sum.iterrows():
        sc1, sc2, sc3, sc4 = st.columns([1.5, 1, 1, 2])
        sc1.write(f"**[{row['기종']}]**")
        sc2.write(f"양품: {row['실적'] - row['불량']} EA")
        sc3.write(f"불량: {row['불량']} EA")
        st.session_state[f"lot_{row['기종']}"] = sc4.text_input(f"LOT 번호 입력 ({row['기종']})", key=f"lot_in_{idx}", placeholder="LOT No. 입력")
else:
    st.info("상단 테이블에 기종을 선택하고 실적을 입력하면 분석창이 자동 생성됩니다.")

# --- 6. 투입부품 및 토크 기록 (이사님 요청 사항 2, 3번 반영) ---
col_sub1, col_sub2 = st.columns(2)

with col_sub1:
    st.markdown("<div class='section-title'>📦 투입부품 (LOT)</div>")
    # OK 란 제거, 부품명과 LOT만 기입하도록 수정
    for i in range(3):
        mat_c1, mat_c2 = st.columns([1, 1])
        mat_c1.text_input(f"부품명 {i+1}", key=f"mat_n_{i}", label_visibility="collapsed", placeholder="부품명")
        mat_c2.text_input(f"부품 LOT {i+1}", key=f"mat_l_{i}", label_visibility="collapsed", placeholder="LOT 번호")

with col_sub2:
    st.markdown("<div class='section-title'>🔧 전동드라이버 토크 (최초 성공 버전 UI)</div>")
    # 최초 성공 버전의 2x2 또는 리스트 형태 UI 복구
    t_c1, t_c2 = st.columns(2)
    t_c1.text_input("측정 1 (N.m)", key="trq_1")
    t_c2.text_input("측정 2 (N.m)", key="trq_2")
    t_c1.text_input("측정 3 (N.m)", key="trq_3")
    t_c2.text_input("측정 4 (N.m)", key="trq_4")

# --- 7. 최종 전송 ---
st.markdown("---")
if st.button("📊 데이터 최종 전송 및 구글 시트 저장"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_rows = []
    
    for i in range(len(TIME_SLOTS)):
        p = st.session_state.get(f"p_{i}", "선택")
        if p != "선택":
            final_rows.append({
                "Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": worker_name,
                "Time_Slot": TIME_SLOTS[i], "Invested_Min": st.session_state.get(f"m_{i}", 0),
                "Item_Name": p, "Actual_Qty": st.session_state.get(f"a_{i}", 0),
                "Defect_Qty": st.session_state.get(f"dq_{i}", 0),
                "Material_Check": st.session_state.get(f"lot_{p}", ""), # 분석란에서 입력한 LOT 자동 연동
                "Torque_Value": f"{st.session_state.get('trq_1','')} / {st.session_state.get('trq_2','')}"
            })
    
    if final_rows:
        try:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(final_rows)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            st.success("✅ 성공! 구글 시트에 데이터가 정확히 저장되었습니다."); st.balloons()
        except Exception as e: st.error(f"오류: {e}")
