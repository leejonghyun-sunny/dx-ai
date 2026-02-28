import streamlit as st
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 및 다크 테마 ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; border: 2px solid red; font-size: 18px; }
    .ok-label { background-color: #d4edda; color: #004085; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; border: 1px solid red; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (이사님 UPH 자료 100% 일치) ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54,
    "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}

TIME_SLOTS_BASE = [
    ("08:30", "09:30"), ("09:30", "10:30"), ("10:40", "11:40"), ("11:40", "12:30"),
    ("13:20", "14:30"), ("14:30", "15:30"), ("15:40", "16:30"), ("16:30", "17:30"),
    ("18:00", "19:00"), ("19:00", "20:00")
]

# --- 3. 기본 정보 ---
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 3.0)")
c_t1, c_t2 = st.columns(2)
with c_t1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_t2: worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 1. 실시간 생산 기록 ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)

if 'rows' not in st.session_state:
    st.session_state.rows = []
    for i, (s, e) in enumerate(TIME_SLOTS_BASE):
        st.session_state.rows.append({
            "id": i, "display_time": f"{s}~{e}",
            "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"),
            "m": 60 if i not in [3, 6] else 50
        })
    st.session_state.next_id = len(TIME_SLOTS_BASE)

# [수정] 헤더 정렬 오류 해결 - 컬럼을 한 번만 생성하여 한 줄로 나열
cols_h = [1.3, 0.6, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.8]
header_cols = st.columns(cols_h)
titles = ["시간대", "분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "기종변경"]
for i, h in enumerate(titles):
    header_cols[i].markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns(cols_h)
    c[0].write(row['display_time'])
    
    # 이사님 지시 사항: 실적에 따른 생산 소요 분 자동 계산
    act_val = st.session_state.get(f"a_{rid}", 0)
    p_sel = st.session_state.get(f"p_{rid}", "선택")
    uph_base = PRODUCT_DB.get(p_sel, 65)
    
    # CT 기반 자동 분 계산: (실적 / UPH) * 60
    auto_m = round((act_val / uph_base) * 60, 1) if p_sel != "선택" and act_val > 0 else row['m']
    
    inv_m = c[1].number_input("분", value=float(auto_m), key=f"m_{rid}", label_visibility="collapsed")
    p_name = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    
    target = round((PRODUCT_DB.get(p_name, 0) / 60) * inv_m) if p_name != "선택" else 0
    c[3].write(f"{target}")

    c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("불량", key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    down_m = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕ 기종변경", key=f"add_{rid}"):
        # 이사님 공식: 시작시간 + 생산소요분 + 셋업분
        total_offset = inv_m + down_m
        new_start_dt = row['start'] + timedelta(minutes=total_offset)
        rem_m = int((row['end'] - new_start_dt).total_seconds() / 60)
        
        if new_start_dt < row['end']:
            st.session_state.rows.insert(idx + 1, {
                "id": st.session_state.next_id,
                "display_time": f"{new_start_dt.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}",
                "start": new_start_dt, "end": row['end'], "m": max(0, rem_m)
            })
            st.session_state.next_id += 1
            st.rerun()

# --- 5. 2. 실적 분석 및 품질 추적 (통합 관리) ---
st.markdown("<div class='section-title'>📋 2. 실적 분석 및 품질 추적 (기종별 통합 관리)</div>", unsafe_allow_html=True)
summary_data = []
first_appearance = {}
for idx, r in enumerate(st.session_state.rows):
    rid = r['id']
    p_name = st.session_state.get(f"p_{rid}", "선택")
    if p_name != "선택":
        summary_data.append({"p_name": p_name, "actual": st.session_state.get(f"a_{rid}", 0), "defect": st.session_state.get(f"dq_{rid}", 0)})
        if p_name not in first_appearance: first_appearance[p_name] = idx

if summary_data:
    df_sum = pd.DataFrame(summary_data).groupby("p_name").agg({'actual': 'sum', 'defect': 'sum'}).reset_index()
    df_sum['f_idx'] = df_sum['p_name'].map(first_appearance)
    df_sum = df_sum.sort_values(by='f_idx').reset_index(drop=True)
    ah_cols = st.columns([1.5, 1, 1, 1, 2.5])
    for i, h in enumerate(["기종명(합계)", "양품수량", "불량수량", "불량율(%)", "LOT 넘버 입력"]): ah_cols[i].markdown(f"**{h}**")
    for idx, row in df_sum.iterrows():
        ac = st.columns([1.5, 1, 1, 1, 2.5])
        good = row['actual'] - row['defect']
        rate = (row['defect'] / row['actual'] * 100) if row['actual'] > 0 else 0
        ac[0].write(f"**{row['p_name']}**")
        ac[1].write(f"{good} EA"); ac[2].write(f"{row['defect']} EA"); ac[3].write(f"{rate:.1f}%")
        st.session_state[f"lot_total_{row['p_name']}"] = ac[4].text_input(f"LOT", key=f"lot_sum_{idx}", label_visibility="collapsed", placeholder="LOT 직접입력")

# --- 6. 3. 전동 드라이버 토크 측정 기록 (스마트 알람) ---
st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정 기록</div>", unsafe_allow_html=True)
torque_list = [st.session_state.get(f"torque_{k}", "").strip() for k in range(1, 6)]
if all(v == "" for v in torque_list):
    st.markdown('<div class="highlight-box">전동드라이버 토크 측정 하세요</div>', unsafe_allow_html=True)

t_c1, t_c2 = st.columns([1.5, 2.5])
with t_c1:
    valid_torque = True
    for k in range(1, 6):
        tr = st.columns([0.4, 1.6, 1.0])
        tr[0].markdown(f"<div style='padding-top:10px;'>{k}번</div>", unsafe_allow_html=True)
        t_val = tr[1].text_input(f"T_{k}", key=f"torque_{k}", label_visibility="collapsed", placeholder="Kgf/cm")
        if t_val:
            try:
                val = float(t_val)
                if val >= 15: tr[2].markdown('<div class="ok-label">OK</div>', unsafe_allow_html=True)
                else: 
                    tr[2].markdown('<div class="ng-label">NG</div>', unsafe_allow_html=True)
                    st.error(f"{k}번 토크값이 불량입니다"); valid_torque = False
            except: valid_torque = False
        else: valid_torque = False

with t_c2:
    st.markdown('<div style="background-color: yellow; color: red; padding: 10px; border: 2px solid red; font-weight: bold; text-align: center;">전동 드라이버 토크 실측값을 전동드라이버 번호대로 반드시 입력 하세요 !</div>', unsafe_allow_html=True)

# --- 7. 데이터 전송 ---
if st.button("📊 오늘의 실적 데이터 최종 전송 및 저장", type="primary", use_container_width=True):
    if all(torque_list) and valid_torque:
        conn = st.connection("gsheets", type=GSheetsConnection)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_data = []
        for r in st.session_state.rows:
            rid = r['id']; p = st.session_state.get(f"p_{rid}", "선택")
            if p != "선택":
                final_data.append({"Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": worker_name, "Time_Slot": r['display_time'], "Item_Name": p, "Actual_Qty": st.session_state.get(f"a_{rid}", 0), "Defect_Qty": st.session_state.get(f"dq_{rid}", 0), "Material_Check": st.session_state.get(f"lot_total_{p}", ""), "Torque_Value": " / ".join(torque_list)})
        if final_data:
            df = conn.read(worksheet="Sheet1")
            updated = pd.concat([df, pd.DataFrame(final_data)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated); st.success("✅ 전송 완료!"); st.balloons()
