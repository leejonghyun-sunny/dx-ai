import streamlit as st
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 및 스타일 ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보", layout="wide")
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 15px; border: 2px solid red; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
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
st.title("⚙️ 조립 1라인 스마트 작업일보 (Ver 3.1)")
c_t1, c_t2 = st.columns(2)
with c_t1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_t2: worker_name = st.text_input("👤 메인 작업자명", placeholder="성함을 입력하세요")

# --- 4. 실시간 생산 기록 ---
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
header_cols = st.columns(cols_h)
for i, h in enumerate(["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "기종변경"]):
    header_cols[i].markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns(cols_h)
    c[0].write(row['display_time'])
    
    # [수정] 실적 입력 시 CT 기반으로 '분' 자동 계산 (이사님 공식)
    act_val = st.session_state.get(f"a_{rid}", 0)
    p_name = st.session_state.get(f"p_{rid}", "선택")
    uph_base = PRODUCT_DB.get(p_name, 65)
    
    # 실적이 있으면 자동 계산, 없으면 기존 분 유지
    calculated_m = round((act_val / uph_base) * 60, 1) if p_name != "선택" and act_val > 0 else row['m']
    
    inv_m = c[1].number_input("분", value=float(calculated_m), key=f"m_{rid}", label_visibility="collapsed")
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    
    target = round((PRODUCT_DB.get(p_sel, 0) / 60) * inv_m) if p_sel != "선택" else 0
    c[3].write(f"{target}")

    c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("불량", key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    down_m = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕ 기종변경", key=f"add_{rid}"):
        # 이사님 공식: 시작시간 + 생산분 + 비가동분
        total_offset = inv_m + down_m
        new_start_dt = row['start'] + timedelta(minutes=total_offset)
        
        # 시간대 슬롯의 끝시간을 넘지 않는지 확인
        if new_start_dt < row['end']:
            rem_m = int((row['end'] - new_start_dt).total_seconds() / 60)
            st.session_state.rows.insert(idx + 1, {
                "id": st.session_state.next_id,
                "display_time": f"{new_start_dt.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}",
                "start": new_start_dt, "end": row['end'], "m": float(rem_m)
            })
            st.session_state.next_id += 1
            st.rerun()
        else:
            st.error(f"⚠️ 시간 초과! (총 {total_offset}분 소요). 60분 이내로 조정이 필요합니다.")
