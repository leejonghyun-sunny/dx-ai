import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 v7.6.2 강력 UI 고정 ---
st.set_page_config(page_title="HSG 조립1라인 스마트작업일보 (v7.6.2)", layout="wide")

# v7.6.2 전용 CSS: 화살표 제거 및 비상 바 상단 고정
st.markdown("""
<style>
    /* 🚨 [개선] 비상 알람 바 상단 강제 고정 */
    .emergency-sticky-bar {
        position: fixed; top: 50px; left: 0; width: 100%;
        background-color: #d32f2f; color: white;
        padding: 15px; text-align: center; font-size: 24px;
        font-weight: 900; z-index: 9999; border-bottom: 3px solid white;
    }
    
    /* 🚫 [개선] 숫자 입력창 +/- 버튼 물리적 삭제 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; margin: 0 !important; }
    input[type=number] { -moz-appearance: textfield !important; font-size: 1.2rem !important; }

    .section-title { font-size: 18px; font-weight: bold; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; margin: 20px 0; }
    .total-stat-box { background-color: #161b22; padding: 20px; border-radius: 10px; border: 2px solid #58a6ff; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. 표준 데이터베이스 (기존 유지) ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
FIXED_WORKER_NAME = "안희선, 강선혜"

# --- 3. 세션 관리 ---
if 'rows' not in st.session_state:
    slots = [("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50), ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60)]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "m": float(m), "start_h": int(s.split(':')[0])} for i, (s, e, m) in enumerate(slots)]
    st.session_state.issue_state = None

# [개선 1] 비상 알람 시각화 (상단 고정)
if st.session_state.issue_state:
    st.markdown(f"<div class='emergency-sticky-bar'>🚨 현재 상태: [{st.session_state.issue_state}] 보고 중 🚨</div>", unsafe_allow_html=True)
    st.write(" ") # 레이아웃 간격 확보

st.title("조립1라인 스마트작업일보 v7.6.2")

# [개선 2] 비상 버튼 (상황 종료 기능 포함)
st.markdown("<div class='section-title'>🚨 현장 비상 호출 제어</div>", unsafe_allow_html=True)
ic = st.columns(5)
btns = ["자재결품", "품질문제", "장비문제", "기타사항", "상황종료"]
for i, label in enumerate(btns):
    if ic[i].button(label, use_container_width=True):
        st.session_state.issue_state = label if label != "상황종료" else None
        st.rerun()

# [생산 기록 영역]
st.markdown("<div class='section-title'>📊 시간대별 생산 실적</div>", unsafe_allow_html=True)
st.info(f"👤 메인 작업자: **{FIXED_WORKER_NAME}** (고정)")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns([1.5, 2, 1, 1, 1, 1.5])
    
    c[0].write(f"**{row['time']}** ({row['m']}분)")
    p_sel = c[1].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    
    # [개선 3] 숫자패드 강제 및 +/- 버튼 제거 반영된 입력란
    act_qty = c[2].number_input("실적", min_value=0, step=1, key=f"a_{rid}", label_visibility="collapsed")
    bad_qty = c[3].number_input("불량", min_value=0, step=1, key=f"dq_{rid}", label_visibility="collapsed")
    
    uph = PRODUCT_DB.get(p_sel, 0)
    target = round((uph / 60) * row['m']) if p_sel != "선택" else 0
    c[4].write(f"목표: **{target}**")
    
    # 토크 NG 시각화 로직
    torque = c[5].text_input("토크", key=f"t_{rid}", placeholder="Nm", label_visibility="collapsed")
    if torque:
        try:
            if not (2.2 <= float(torque) <= 2.8): st.toast(f"{row['time']} 토크 NG!", icon="🚨")
        except: pass

# [7. 구글 시트 전송 엔진 - v7.6.2 정밀 로직]
st.divider()
if st.button("🚀 v7.6.2 데이터 최종 전송 및 시트 박제", type="primary", use_container_width=True):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        current_hour = datetime.now().hour
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        final_data = []
        for r in st.session_state.rows:
            p = st.session_state.get(f"p_{r['id']}", "선택")
            if p != "선택":
                # [개선 2 반영] 현재 시각과 일치하는 행에만 비상 상태 기록
                is_this_time_issue = "NORMAL"
                issue_detail = "None"
                
                if st.session_state.issue_state:
                    # 현재 실제 시간(hour)이 해당 슬롯의 시작 시간과 일치할 때만 기록
                    if current_hour == r['start_h']:
                        is_this_time_issue = "[CRITICAL]"
                        issue_detail = st.session_state.issue_state

                final_data.append({
                    "Timestamp": ts,
                    "Worker": FIXED_WORKER_NAME,
                    "Time_Slot": r['time'],
                    "Item": p,
                    "Actual": st.session_state.get(f"a_{r['id']}", 0),
                    "Defect": st.session_state.get(f"dq_{r['id']}", 0),
                    "Issue_Status": is_this_time_issue,
                    "Issue_Type": issue_detail
                })
        
        if final_data:
            df_old = conn.read(worksheet="sheet1")
            conn.update(worksheet="sheet1", data=pd.concat([df_old, pd.DataFrame(final_data)], ignore_index=True))
            st.success("✅ v7.6.2 정밀 데이터 전송 완료!"); st.balloons()
            
    except Exception as e:
        st.error(f"❌ 전송 오류: {e}")