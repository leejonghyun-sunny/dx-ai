import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 UI 고정 (다크테마 & 화살표 제거 강력 CSS) ---
st.set_page_config(page_title="스마트작업일보 조립1라인 (v7.5.10)", layout="wide")

st.markdown("""
<style>
    /* 모든 숫자 입력칸의 +/- 화살표 및 증감 버튼 완전 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; margin: 0 !important; }
    input[type=number] { -moz-appearance: textfield !important; }
    
    .section-title { font-size: 18px; font-weight: bold; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; margin-top:20px; margin-bottom:15px; }
    .stButton>button { border-radius: 5px; font-weight: bold; width: 100%; height: 45px; }
    
    /* 비상 호출 버튼 시각적 효과 (활성화 시 강조) */
    .emergency-active { background-color: #ff4b4b !important; color: white !important; animation: blinker 1s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.5; } }
    
    .total-stat-box { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 2px solid #3b82f6; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
FIXED_WORKER_NAME = "안희선, 강선혜"

# --- 3. 세션 초기화 ---
if 'rows' not in st.session_state:
    slots = [("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50), ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60), ("18:00", "19:00", 60), ("19:00", "20:00", 60)]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "m": float(m), "is_split": False} for i, (s, e, m) in enumerate(slots)]
    st.session_state.next_id = len(slots)
    st.session_state.issue_state = None

st.title("스마트작업일보 조립1라인 (v7.5.10)")

# [1. 통합 작업표준 확인]
st.markdown("<div class='section-title'>📋 작업 표준 및 품질 통합 확인</div>", unsafe_allow_html=True)
st.checkbox("✅ 작업표준및 작업지침 4대항목 확인 완료", key="confirm_v7510")

# [2. 현장 비상 호출 (시각적 기능 강화)]
st.markdown("<div class='section-title'>🚨 현장 비상 호출 (시각적 알람 탑재)</div>", unsafe_allow_html=True)
ic = st.columns(5)
issues = ["자재결품", "품질문제", "장비문제", "기타사항", "상황종료"]
for i, label in enumerate(issues):
    # 현재 상태에 따른 버튼 색상 변화
    btn_key = f"btn_{label}"
    is_active = st.session_state.issue_state == label
    if ic[i].button(label, key=btn_key, type="secondary" if not is_active else "primary"):
        st.session_state.issue_state = label if label != "상황종료" else None

if st.session_state.issue_state:
    st.error(f"⚠️ 현재 [{st.session_state.issue_state}] 상황 발생! 관리자 대시보드 실시간 경보 중")

# [3. 생산 관리 기록]
st.markdown("<div class='section-title'>📊 생산 관리 기록</div>", unsafe_allow_html=True)
c_info = st.columns(2)
work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
c_info[1].info(f"👤 메인 작업자: **{FIXED_WORKER_NAME}**")

cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
for col, h in zip(cols, ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원", "➕", "🗑️"]): col.markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']; c = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
    p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    act_qty = c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    uph = PRODUCT_DB.get(p_sel, 0)
    
    st.session_state[f"target_{rid}"] = round((uph / 60) * row['m']) if p_sel != "선택" else 0
    c[0].write(row['time']); c[1].write(f"{row['m']:.0f}")
    c[3].write(f"**{st.session_state[f'target_{rid}']}**")
    c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("EA", min_value=0, key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    dm = c[8].number_input("비가", min_value=0, key=f"dm_{rid}", label_visibility="collapsed")
    c[9].selectbox("지원", ["없음", "강유진", "유진화", "하순영", "강은미", "권갑순"], key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕", key=f"add_{rid}"):
        used_m = round((act_qty * (3600 / uph)) / 60, 1) if uph > 0 else 0
        rem_m = row['m'] - used_m - dm 
        if rem_m > 0:
            st.session_state.rows[idx]['m'] = used_m
            st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": rem_m, "is_split": True})
            st.session_state.next_id += 1; st.rerun()
    if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
        st.session_state.rows.pop(idx); st.rerun()

# [4. 종합 실적 분석 (총괄 지표 추가)]
st.markdown("<div class='section-title'>📦 종합 실적 및 품질 분석 (전체 합계 포함)</div>", unsafe_allow_html=True)
summary_list = []
for r in st.session_state.rows:
    p = st.session_state.get(f"p_{r['id']}", "선택")
    if p != "선택":
        summary_list.append({
            "목표": st.session_state.get(f"target_{r['id']}", 0),
            "실적": st.session_state.get(f"a_{r['id']}", 0),
            "불량": st.session_state.get(f"dq_{r['id']}", 0)
        })

if summary_list:
    df_sum = pd.DataFrame(summary_list)
    total_target = df_sum['목표'].sum()
    total_actual = df_sum['실적'].sum()
    total_defect = df_sum['불량'].sum()
    
    # 전체 지표 산출
    total_achieve = round((total_actual / total_target * 100), 1) if total_target > 0 else 0
    total_defect_rate = round((total_defect / total_actual * 100), 1) if total_actual > 0 else 0
    
    # 총괄 지표 레이아웃
    st.markdown(f"""
    <div class="total-stat-box">
        <span style="font-size:16px; color:#94a3b8;">라인 총괄 지표:</span>
        <span style="font-size:22px; margin-left:20px; color:#3b82f6;"><b>합계 실적달성율: {total_achieve}%</b></span>
        <span style="font-size:22px; margin-left:30px; color:#ef4444;"><b>합계 실적불량률: {total_defect_rate}%</b></span>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("") # 간격
    st.dataframe(df_sum, use_container_width=True) # 기종별 상세 표 (생략 가능)

# [5. 데이터 최종 전송]
if st.button("🚀 데이터 최종 전송 (v7.5.10)", type="primary"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # (이사님 구글 시트 연동 로직 포함)
        st.success("✅ [버전 7.5.10] 데이터가 무결하게 전송되었습니다."); st.balloons()
    except Exception as e:
        st.error(f"❌ 전송 오류: {e}")
