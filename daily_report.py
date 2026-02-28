import streamlit as st
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 및 시각적 알람 스타일 ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 15px; border: 2px solid red; font-size: 18px; }
    .ok-label { background-color: #28a745; color: #004085; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; border: 1px solid white; }
    .stButton>button { width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (전 기종 UPH 고정) ---
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
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 4.1)")
c_info1, c_info2 = st.columns(2)
with c_info1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_info2: worker_name = st.text_input("👤 메인 작업자명", placeholder="작업자 성함 입력")

# --- 4. 1. 실시간 생산 기록 ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)

if 'rows' not in st.session_state:
    st.session_state.rows = []
    for i, (s, e) in enumerate(TIME_SLOTS_BASE):
        st.session_state.rows.append({
            "id": i, "display_time": f"{s}~{e}",
            "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"),
            "m": 60.0 if i not in [3, 6] else 50.0,
            "is_split": False, "fixed_target": 0
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
    
    p_sel = st.session_state.get(f"p_{rid}", "선택")
    act_val = st.session_state.get(f"a_{rid}", 0)
    uph_base = PRODUCT_DB.get(p_sel, 65)

    # [이사님 개선사항 핵심 로직]
    # 1. 원본 슬롯(is_split=False)은 기존처럼 실적에 따라 분이 변함
    # 2. 기종변경 슬롯(is_split=True)은 분과 목표가 'Lock' 되어 실적 입력에 영향받지 않음
    if row['is_split']:
        inv_m = c[1].number_input("분", value=float(row['m']), key=f"m_{rid}", disabled=True, label_visibility="collapsed")
        target = row['fixed_target']
    else:
        if p_sel != "선택" and act_val > 0:
            calc_m = round((act_val * (3600 / uph_base)) / 60, 1)
            st.session_state[f"m_{rid}"] = float(calc_m)
        inv_m = c[1].number_input("분", key=f"m_{rid}", label_visibility="collapsed")
        target = round((uph_base / 60) * inv_m) if p_sel != "선택" else 0

    c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    c[3].write(f"**{target}**") # 고정된 목표 수량 표시

    c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed", min_value=0)
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    down_m = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed", min_value=0)
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    # 기종변경 버튼 클릭 시 "목표 수량"을 계산하여 고정(Lock)
    if c[10].button("➕ 기종변경", key=f"add_{rid}"):
        total_used = inv_m + down_m
        new_start_dt = row['start'] + timedelta(minutes=total_used)
        
        if new_start_dt < row['end']:
            rem_m = round((row['end'] - new_start_dt).total_seconds() / 60, 1)
            # 이사님 지시: 다음 슬롯 기종은 선택 전이라도 현재 UPH 기준으로 가목표 설정(이후 기종 선택 시 갱신 가능하게 하거나 현재값 고정)
            # 여기서는 이사님의 7번 항목 "12.2개 목표" 처럼 다음 행 생성 시 '분'에 따른 목표를 고정합니다.
            st.session_state.rows.insert(idx + 1, {
                "id": st.session_state.next_id,
                "display_time": f"{new_start_dt.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}",
                "start": new_start_dt, "end": row['end'], 
                "m": rem_m,
                "is_split": True, # 목표 수량 고정 모드 활성화
                "fixed_target": round((uph_base / 60) * rem_m, 1) # CT 기반 목표 수량 고정
            })
            st.session_state.next_id += 1
            st.rerun()
        else:
            st.error(f"⚠️ 시간 초과: 현재 슬롯의 잔여 시간이 없습니다.")

# (이하 분석 및 토크 알람 로직은 이전과 동일하게 유지)
# ... [중합 로직 생략] ...
