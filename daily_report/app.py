import streamlit as st
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 및 스타일 ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 15px; border: 2px solid red; font-size: 18px; }
    .ok-label { background-color: #28a745; color: #004085; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; border: 1px solid white; }
    .stButton>button { width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}

TIME_SLOTS_BASE = [
    ("08:30", "09:30"), ("09:30", "10:30"), ("10:40", "11:40"), ("11:40", "12:30"),
    ("13:20", "14:30"), ("14:30", "15:30"), ("15:40", "16:30"), ("16:30", "17:30"),
    ("18:00", "19:00"), ("19:00", "20:00")
]

# --- 3. 기본 정보 입력 ---
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 3.5)")
c_info1, c_info2 = st.columns(2)
with c_info1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_info2: worker_name = st.text_input("👤 메인 작업자명", value="안희선")

# --- 4. 1. 실시간 생산 기록 ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)

if 'rows' not in st.session_state:
    st.session_state.rows = []
    for i, (s, e) in enumerate(TIME_SLOTS_BASE):
        st.session_state.rows.append({
            "id": i, "display_time": f"{s}~{e}",
            "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"),
            "m": 60.0 if i not in [3, 6] else 50.0
        })
    st.session_state.next_id = len(TIME_SLOTS_BASE)

cols_h = [1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.9]
h_cols = st.columns(cols_h)
for i, h in enumerate(["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "기종변경"]):
    h_cols[i].markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns(cols_h)
    c[0].write(row['display_time'])
    
    # ------------------------------------------------------------------
    # [핵심 수술 부위: 스트림릿 캐시 무력화 및 이사님 계산식 강제 주입]
    p_sel = st.session_state.get(f"p_{rid}", "선택")
    act_val = st.session_state.get(f"a_{rid}", 0)
    uph_base = PRODUCT_DB.get(p_sel, 65)
    
    if p_sel != "선택" and act_val > 0:
        # 이사님 공식: 생산분 = (실적 * (3600 / UPH)) / 60
        calc_m = round((act_val * (3600 / uph_base)) / 60, 1)
        st.session_state[f"m_{rid}"] = float(calc_m) # 화면에 무조건 덮어쓰기
    elif f"m_{rid}" not in st.session_state:
        st.session_state[f"m_{rid}"] = float(row['m'])
    # ------------------------------------------------------------------

    inv_m = c[1].number_input("분", key=f"m_{rid}", label_visibility="collapsed")
    c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    
    target = round((PRODUCT_DB.get(p_sel, 0) / 60) * inv_m) if p_sel != "선택" else 0
    c[3].write(f"{target}")

    c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed", min_value=0)
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    down_m = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed", min_value=0)
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕ 기종변경", key=f"add_{rid}"):
        total_used = inv_m + down_m
        new_start_dt = row['start'] + timedelta(minutes=total_used)
        
        if new_start_dt < row['end']:
            rem_m = (row['end'] - new_start_dt).total_seconds() / 60
            st.session_state.rows.insert(idx + 1, {
                "id": st.session_state.next_id,
                "display_time": f"{new_start_dt.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}",
                "start": new_start_dt, "end": row['end'], "m": round(rem_m, 1)
            })
            st.session_state.next_id += 1
            st.rerun()
        else:
            st.error(f"⚠️ 시간 초과: 현재 슬롯에서 {total_used}분(생산 {inv_m}분+셋업 {down_m}분)을 사용하여 잔여 시간이 없습니다.")

# --- 5. 2. 실적 분석 및 품질 추적 ---
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
else:
    st.info("실적 입력 시 기종별 합계 데이터가 투입 순서대로 자동 생성됩니다.")

# --- 6. 3. 전동 드라이버 토크 측정 기록 ---
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
        t_val = tr[1].text_input(