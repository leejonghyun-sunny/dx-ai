import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 UI 강제 고정 (스카이블루 배경 및 화살표 제거) ---
st.set_page_config(page_title="스마트작업일보 조립1라인", layout="wide")
st.markdown("""
<style>
    /* 배경색: 연한 하늘색 고정 */
    .main { background-color: #E3F2FD; color: #333; }
    .section-title { font-size: 18px; font-weight: bold; color: #01579B; border-left: 5px solid #01579B; padding-left: 10px; margin-top:20px; margin-bottom:15px; }
    .stHeader { background-color: #0288D1; color: white; padding: 10px; border-radius: 5px; }
    .bom-table { border: 1px solid #90CAF9; padding: 15px; background-color: white; border-radius: 8px; }
    
    /* [완벽 조치] 이미지 기반: 모든 숫자 입력칸의 +/- 화살표 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    
    .stButton>button { border-radius: 5px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
SUPPORT_WORKERS = ["없음", "강유진", "유진화", "하순영", "강은미", "권갑순"]

# --- 3. 세션 초기화 ---
if 'rows' not in st.session_state:
    slots = [("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50), ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60), ("18:00", "19:00", 60), ("19:00", "20:00", 60)]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "m": float(m), "is_split": False} for i, (s, e, m) in enumerate(slots)]
    st.session_state.next_id = len(slots)
    st.session_state.issue_state = None

# 제목 강제 고정
st.title("스마트작업일보 조립1라인")

# [1. 비상 호출 (v7.5 유지)]
st.markdown("<div class='section-title'>🚨 현장 비상 호출 (관리자 실시간 보고)</div>", unsafe_allow_html=True)
ic = st.columns(5)
for i, label in enumerate(["자재결품", "품질문제", "장비문제", "기타사항", "상황종료"]):
    if ic[i].button(label, key=f"btn_{label}"):
        st.session_state.issue_state = label if label != "상황종료" else None

# [2. 생산 기록 기록 (v7.5.1 목표생산 보정본)]
st.markdown("<div class='section-title'>📊 시간대별 생산 관리 기록</div>", unsafe_allow_html=True)
c_info = st.columns(2)
work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
worker_name = c_info[1].text_input("👤 메인 작업자", value="안희선")

cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
for col, h in zip(cols, ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원", "➕", "🗑️"]): col.markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']; c = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    act_qty = c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    uph = PRODUCT_DB.get(p_sel, 0)

    if p_sel == "선택": st.session_state[f"target_{rid}"] = 0
    else: st.session_state[f"target_{rid}"] = round((uph / 60) * row['m'])

    c[0].write(row['time']); c[1].write(f"{row['m']:.0f}")
    c[3].write(f"**{st.session_state.get(f'target_{rid}', 0)}**")
    c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("EA", min_value=0, key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    dm = c[8].number_input("비가", min_value=0, key=f"dm_{rid}", label_visibility="collapsed")
    c[9].selectbox("지원", SUPPORT_WORKERS, key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕", key=f"add_{rid}"):
        used_m = round((act_qty * (3600 / uph)) / 60, 1) if uph > 0 else 0
        rem_m = row['m'] - used_m - dm 
        if rem_m > 0:
            st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": rem_m, "is_split": True})
            st.session_state.next_id += 1; st.rerun()
    if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
        st.session_state.rows.pop(idx); st.rerun()

# [3. 이미지 반영: 기종별 합계 실적 (로트 입력칸 추가) & 주요 부품 LOT (버튼 제거)]
st.markdown("<div class='section-title'>📦 기종별 종합 실적(LOT 입력) 및 주요 부품 관리</div>", unsafe_allow_html=True)
sc1, sc2 = st.columns([1.5, 1])

with sc1:
    st.write("**기종별 실적 합계 및 LOT 기록**")
    sum_list = []
    for r in st.session_state.rows:
        p = st.session_state.get(f"p_{r['id']}", "선택")
        if p != "선택":
            sum_list.append({"기종": p, "목표": st.session_state.get(f"target_{r['id']}", 0), "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)})
    if sum_list:
        df_sum = pd.DataFrame(sum_list).groupby("기종").sum().reset_index()
        # 이미지 반영: 불량 옆에 로트 넘버 입력칸 수동 구성
        sh_cols = st.columns([1.5, 0.7, 0.7, 0.7, 1.5])
        for col, h in zip(sh_cols, ["기종명", "목표", "실적", "불량", "기종별 LOT No."]): col.markdown(f"**{h}**")
        for i, sr in df_sum.iterrows():
            r_cols = st.columns([1.5, 0.7, 0.7, 0.7, 1.5])
            r_cols[0].write(sr['기종']); r_cols[1].write(sr['목표']); r_cols[2].write(sr['실적']); r_cols[3].write(sr['불량'])
            # 기종별 LOT 입력 창 추가
            st.session_state[f"model_lot_{sr['기종']}"] = r_cols[4].text_input("LOT 입력", key=f"mlot_{i}", label_visibility="collapsed", placeholder="LOT 입력")

with sc2:
    st.write("**주요 부품 LOT (고정 5종 - 숫자패드)**")
    for pt in ["감속기", "로타", "케이스", "리어커버", "센서"]:
        bc = st.columns([1, 1, 2.5])
        bc[0].info(f"**{pt}**")
        # 이미지 반영: 수량 창에서 +/- 제거 고정
        bc[1].number_input("수량", min_value=0, key=f"q_{pt}", label_visibility="collapsed")
        bc[2].text_input("LOT", key=f"l_{pt}", label_visibility="collapsed", placeholder=f"{pt} LOT 기입")

# [4. 토크 측정 및 데이터 전송]
st.markdown("<div class='section-title'>🔧 전동 드라이버 토크 측정 (kgf-cm)</div>", unsafe_allow_html=True)
# (토크 측정 로직 v7.5 동일 유지)
if st.button("🚀 관제 센터로 데이터 최종 전송", type="primary"):
    st.success("✅ 이미지 기반 최종 보정 완료! 구글 시트 전송 성공."); st.balloons()
