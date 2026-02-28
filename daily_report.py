import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 (다크/와이드 레이아웃) ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .stButton>button { width: 100%; height: 40px; font-weight: bold; }
    .send-button>div>button { background-color: #238636 !important; color: white !important; height: 55px !important; font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (이사님 지시대로 기종명 완전 개별화) ---
PRODUCT_DB = {
    "VE (태양)": {50: 54, 60: 65, 70: 76},
    "100바 (태양)": {50: 54, 60: 65, 70: 76},
    "6*14 (태양)": {50: 54, 60: 65, 70: 76},
    "황동 (태양)": {50: 34, 60: 40, 70: 46},
    "80각 (태양)": {50: 35, 60: 42, 70: 49},
    "방화 (태양)": {50: 54, 60: 65, 70: 76},
    "MC (태성)": {50: 36, 60: 45, 70: 54},
    "90W (태성)": {50: 36, 60: 45, 70: 54},
    "60W B/K (태성)": {50: 25, 60: 30, 70: 35},
    "90W B/K (태성)": {50: 25, 60: 30, 70: 35},
    "60W (동명)": {50: 45, 60: 53, 70: 62},
    "90W (동명)": {50: 33, 60: 40, 70: 47},
    "60W (신일)": {50: 38, 60: 44, 70: 50},
    "90W (신일)": {50: 26, 60: 32, 70: 37},
    "윈스터 (중문)": {50: 46, 60: 54, 70: 62},
    "펜타포스 (중문)": {50: 46, 60: 54, 70: 62},
    "코르텍 (중문)": {50: 46, 60: 54, 70: 62},
    "태광": {50: 47, 60: 55, 70: 62},
    "펜타포스(단독)": {50: 65, 60: 80, 70: 92},
    "씨넷": {50: 80, 60: 88, 70: 95},
    "현대": {50: 50, 60: 58, 70: 65},
    "H&T": {50: 54, 60: 60, 70: 66}
}

TIME_SLOTS = ["08:30~09:30", "09:30~10:30", "10:40~11:40", "11:40~12:30", "13:20~14:30", "14:30~15:30", "15:40~16:30", "16:30~17:30", "18:00~19:00", "19:00~20:00"]

# --- 3. 기본 정보 입력 ---
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 2.5)")

c_top1, c_top2 = st.columns(2)
with c_top1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_top2: worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 실시간 생산 기록 (다기종 입력 기능 추가) ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록 (기종 추가 기능 활성화)</div>", unsafe_allow_html=True)

if 'rows' not in st.session_state:
    st.session_state.rows = [{"id": i, "time": slot, "m": 60 if i not in [3, 6] else 50} for i, slot in enumerate(TIME_SLOTS)]
    st.session_state.next_id = len(TIME_SLOTS)

cols_h = [1.2, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.5]
h_titles = ["시간대", "분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "추가"]
h_cols = st.columns(cols_h)
for i, h in enumerate(h_titles): h_cols[i].markdown(f"**{h}**")

total_actual, total_target = 0, 0

# 데이터 입력을 위한 루프
new_rows = []
for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns(cols_h)
    
    c[0].write(row['time'])
    inv_m = c[1].number_input("분", value=row['m'], key=f"m_{rid}", label_visibility="collapsed")
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    
    target = 0
    if p_sel != "선택":
        base = PRODUCT_DB[p_sel].get(60, 0)
        target = PRODUCT_DB[p_sel].get(inv_m, round((base/60)*inv_m))
    c[3].write(f"{target}")
    total_target += target

    actual = c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    total_actual += actual
    
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    defect = c[6].number_input("불량", key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    # [행 추가 버튼] - 동일 시간대 다기종 생산 대응
    if c[10].button("➕", key=f"add_{rid}"):
        st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": 0})
        st.session_state.next_id += 1
        st.rerun()

# --- 5. 실적 분석 및 품질 추적 (불량률 자동 계산) ---
st.markdown("<div class='section-title'>📋 2. 실적 분석 및 품질 추적 (기종별 LOT 관리)</div>", unsafe_allow_html=True)

sum_data = []
for r in st.session_state.rows:
    rid = r['id']
    p = st.session_state.get(f"p_{rid}", "선택")
    if p != "선택":
        sum_data.append({"기종": p, "실적": st.session_state.get(f"a_{rid}", 0), "불량": st.session_state.get(f"dq_{rid}", 0)})

if sum_data:
    df_sum = pd.DataFrame(sum_data).groupby("기종").sum().reset_index()
    ah_cols = st.columns([1.5, 1, 1, 1, 2.5])
    for i, h in enumerate(["기종명", "양품수량", "불량수량", "불량율(%)", "LOT 넘버 입력"]): ah_cols[i].markdown(f"**{h}**")
    
    for idx, row in df_sum.iterrows():
        ac = st.columns([1.5, 1, 1, 1, 2.5])
        good = row['실적'] - row['불량']
        rate = (row['불량'] / row['실적'] * 100) if row['실적'] > 0 else 0
        ac[0].write(f"**{row['기종']}**")
        ac[1].write(f"{good} EA")
        ac[2].write(f"{row['불량']} EA")
        ac[3].write(f"{rate:.1f}%")
        st.session_state[f"lot_{row['기종']}"] = ac[4].text_input(f"LOT ({row['기종']})", key=f"li_{idx}", label_visibility="collapsed", placeholder="LOT 번호 직접입력")
else:
    st.info("상단 테이블에 실적을 입력하면 분석창이 자동 생성됩니다.")

# --- 6. 전동 드라이버 토크 측정 (단위: Kgf/cm) ---
st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정 기록</div>", unsafe_allow_html=True)

t_col1, t_col2 = st.columns([1, 2])
with t_col1:
    torque_vals = []
    for j in range(1, 6):
        tr = st.columns([0.4, 1.6])
        tr[0].markdown(f"<div style='padding-top:10px;'>{j}번</div>", unsafe_allow_html=True)
        t_val = tr[1].text_input(f"측정 {j}", key=f"tq_{j}", label_visibility="collapsed", placeholder="Kgf/cm 실측값 입력")
        torque_vals.append(t_val)

with t_col2:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.warning("⚠️ 전동 드라이버 토크 실측값을 Kgf/cm 단위로 1번부터 5번까지 순서대로 입력해 주세요.")

# --- 7. 데이터 최종 전송 ---
st.markdown("---")
st.markdown("<div class='send-button'>", unsafe_allow_html=True)
if st.button("📊 오늘의 실적 데이터 최종 전송 및 저장", use_container_width=True):
    conn = st.connection("gsheets", type=GSheetsConnection)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_rows = []
    
    for r in st.session_state.rows:
        rid = r['id']
        p = st.session_state.get(f"p_{rid}", "선택")
        if p != "선택":
            final_rows.append({
                "Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": worker_name,
                "Time_Slot": r['time'], "Item_Name": p, "Actual_Qty": st.session_state.get(f"a_{rid}", 0),
                "Defect_Qty": st.session_state.get(f"dq_{rid}", 0),
                "Material_Check": st.session_state.get(f"lot_{p}", ""), 
                "Torque_Value": " / ".join([v for v in torque_vals if v])
            })
            
    if final_rows:
        try:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(final_rows)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            st.success("✅ 대성공! 본사 벤치마킹용 구글 시트에 데이터가 안전하게 저장되었습니다!"); st.balloons()
        except Exception as e: st.error(f"오류 발생: {e}")
st.markdown("</div>", unsafe_allow_html=True)
