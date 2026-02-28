import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 (다크/와이드 레이아웃) ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .stButton>button { width: 100%; height: 50px; background-color: #238636; color: white; font-weight: bold; font-size: 16px; }
    .torque-table { background-color: #1a1c24; border: 1px solid #30363d; border-radius: 5px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (모든 기종 완전 분리) ---
# 이사님 지시대로 동일 제조사/UPH라도 각각 별개 기종으로 리스팅함
PRODUCT_DB = {
    "VE (태양)": {50: 54, 60: 65, 70: 76},
    "100바 (태양)": {50: 54, 60: 65, 70: 76},
    "6*14 (태양)": {50: 54, 60: 65, 70: 76},
    "방화 (태양)": {50: 54, 60: 65, 70: 76},
    "MC (태양)": {50: 54, 60: 65, 70: 76},
    "90W(태성)": {50: 36, 60: 45, 70: 54},
    "황동": {50: 34, 60: 40, 70: 46},
    "80각": {50: 35, 60: 42, 70: 49},
    "60W B/K": {50: 25, 60: 30, 70: 35},
    "90W B/K": {50: 25, 60: 30, 70: 35},
    "태광": {50: 47, 60: 55, 70: 62},
    "펜타포스(단독)": {50: 65, 60: 80, 70: 92},
    "코르텍": {50: 46, 60: 54, 70: 62},
    "펜타포스(중문)": {50: 46, 60: 54, 70: 62},
    "윈스터": {50: 46, 60: 54, 70: 62},
    "60W(동명)": {50: 45, 60: 53, 70: 62},
    "90W(동명)": {50: 33, 60: 40, 70: 47},
    "60W(신일)": {50: 38, 60: 44, 70: 50},
    "90W(신일)": {50: 26, 60: 32, 70: 37}
}

TIME_SLOTS = ["08:30~09:30", "09:30~10:30", "10:40~11:40", "11:40~12:30", "13:20~14:30", "14:30~15:30", "15:40~16:30", "16:30~17:30", "18:00~19:00", "19:00~20:00"]

# --- 3. 기본 정보 입력 ---
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 2.0)")

col_info1, col_info2 = st.columns(2)
with col_info1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col_info2: worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 실시간 생산 기록 테이블 ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)
cols_h = [1.2, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8]
h_titles = ["시간대", "투입분", "기종명", "목표", "실적", "불량명", "불량", "비가동사유", "비가동분", "지원자"]
h_cols = st.columns(cols_h)
for i, h in enumerate(h_titles): h_cols[i].markdown(f"**{h}**")

# 실시간 계산을 위한 변수
total_actual, total_target, total_defect = 0, 0, 0

for i, slot in enumerate(TIME_SLOTS):
    c = st.columns(cols_h)
    c[0].write(slot)
    
    # 시간별 투입분 (11시, 15시 슬롯은 50분 기본값)
    def_m = 60 if i not in [3, 6] else 50
    inv_m = c[1].number_input("분", value=def_m, key=f"m_{i}", label_visibility="collapsed")
    
    # 기종 선택 (완전 분리된 리스트)
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{i}", label_visibility="collapsed")
    
    target = 0
    if p_sel != "선택":
        base_60 = PRODUCT_DB[p_sel].get(60, 0)
        target = PRODUCT_DB[p_sel].get(inv_m, round((base_60/60)*inv_m))
    c[3].write(f"{target}")
    total_target += target

    actual = c[4].number_input("실적", min_value=0, key=f"a_{i}", label_visibility="collapsed")
    total_actual += actual
    
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형", "기타"], key=f"dt_{i}", label_visibility="collapsed")
    defect = c[6].number_input("불량", key=f"dq_{i}", label_visibility="collapsed")
    total_defect += defect
    
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질", "기타"], key=f"dr_{i}", label_visibility="collapsed")
    c[8].number_input("비가", key=f"dm_{i}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"s_{i}", label_visibility="collapsed")

# --- 5. 실적 분석 및 품질 추적 UI (요청사항 2번 반영) ---
st.markdown("<div class='section-title'>📋 2. 실적 분석 및 품질 추적 (LOT)</div>", unsafe_allow_html=True)

# 기종별 데이터 집계
summary_list = []
for i in range(len(TIME_SLOTS)):
    p = st.session_state.get(f"p_{i}", "선택")
    if p != "선택":
        summary_list.append({
            "기종": p,
            "실적": st.session_state.get(f"a_{i}", 0),
            "불량": st.session_state.get(f"dq_{i}", 0)
        })

if summary_list:
    df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
    
    # 분석용 헤더
    ah_cols = st.columns([1.5, 1, 1, 1, 2])
    ah_titles = ["기종명", "양품수량", "불량수량", "불량율(%)", "LOT 넘버 직접입력"]
    for i, h in enumerate(ah_titles): ah_cols[i].markdown(f"**{h}**")
    
    for idx, row in df_sum.iterrows():
        ac = st.columns([1.5, 1, 1, 1, 2])
        good_qty = row['실적'] - row['불량']
        defect_rate = (row['불량'] / row['실적'] * 100) if row['실적'] > 0 else 0
        
        ac[0].write(f"**{row['기종']}**")
        ac[1].write(f"{good_qty} EA")
        ac[2].write(f"{row['불량']} EA")
        ac[3].write(f"{defect_rate:.1f} %")
        # LOT 넘버 입력창 (기종별로 세션 저장)
        st.session_state[f"final_lot_{row['기종']}"] = ac[4].text_input(f"LOT 입력", key=f"lot_in_{idx}", label_visibility="collapsed")
else:
    st.info("상단 테이블에서 기종을 선택하고 실적을 입력하면 분석 데이터가 자동 생성됩니다.")

# --- 6. 전동 드라이버 토크 측정창 (요청사항 3번 반영) ---
st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정 기록</div>", unsafe_allow_html=True)

tc1, tc2 = st.columns([1, 2])
with tc1:
    st.write("가로 2줄 세로 5줄 구성")
    torque_data = []
    for j in range(1, 6):
        t_row = st.columns([0.5, 1.5])
        t_row[0].markdown(f"<div style='padding-top:10px;'>{j}번</div>", unsafe_allow_html=True)
        t_val = t_row[1].text_input(f"측정값 {j}", key=f"tq_val_{j}", label_visibility="collapsed", placeholder="N.m 입력")
        torque_data.append(t_val)

with tc2:
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
    st.info("지정된 5회 측정을 원칙으로 하며, 측정된 실측값을 왼쪽 칸에 순서대로 입력해 주세요.")

# --- 7. 최종 전송 ---
st.markdown("---")
if st.button("📊 오늘의 실적 데이터 최종 전송 및 저장"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    all_push_data = []
    for i in range(len(TIME_SLOTS)):
        p = st.session_state.get(f"p_{i}", "선택")
        if p != "선택":
            all_push_data.append({
                "Timestamp": ts,
                "Work_Date": work_date.strftime("%Y-%m-%d"),
                "Worker_Name": worker_name,
                "Time_Slot": TIME_SLOTS[i],
                "Item_Name": p,
                "Actual_Qty": st.session_state.get(f"a_{i}", 0),
                "Defect_Qty": st.session_state.get(f"dq_{i}", 0),
                "Material_Check": st.session_state.get(f"final_lot_{p}", ""), # 기종별 입력한 LOT 연동
                "Torque_Value": " / ".join([v for v in torque_data if v]) # 5개 측정값 통합 저장
            })
            
    if all_push_data:
        try:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(all_push_data)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            st.success("✅ 구글 시트에 모든 데이터가 성공적으로 저장되었습니다!"); st.balloons()
        except Exception as e: st.error(f"오류: {e}")
