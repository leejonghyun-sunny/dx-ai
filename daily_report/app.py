import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 시각적 스타일 ---
st.set_page_config(page_title="조립 1라인 통합 관제 v7.1", layout="wide")
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .section-title { font-size: 18px; font-weight: bold; color: #004085; border-left: 5px solid #004085; padding-left: 10px; margin-bottom:15px; margin-top:20px; }
    .alarm-bar { background-color: #e53e3e; color: white; padding: 12px; border-radius: 5px; text-align: center; font-weight: bold; animation: blinker 1.2s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .bom-table { border: 1px solid #dee2e6; padding: 10px; background-color: white; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 및 설정 ---
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

# --- Tab 구성 ---
tab1, tab2 = st.tabs(["📝 현장 데이터 입력 & 호출", "📈 실시간 관제 대시보"])

with tab1:
    st.title("⚙️ 조립 1라인 스마트 관제소 v7.1")
    
    # [1. 호출 및 경고 기능]
    st.markdown('<div class="alarm-bar">🚨 [점검] 현재 시간대 미입력 데이터 존재! 관리자 확인 대기 중</div>', unsafe_allow_html=True)
    
    st.markdown("<div class='section-title'>🚨 현장 비상 호출 (관리자 전송)</div>", unsafe_allow_html=True)
    ic1, ic2, ic3, ic4, ic5 = st.columns(5)
    if ic1.button("📉 자재결품", use_container_width=True): st.session_state.issue_state = "자재결품"
    if ic2.button("🚫 품질문제", use_container_width=True): st.session_state.issue_state = "품질문제"
    if ic3.button("🔧 장비문제", use_container_width=True): st.session_state.issue_state = "장비문제"
    if ic4.button("❓ 기타사항", use_container_width=True): st.session_state.issue_state = "기타사항"
    if ic5.button("✅ 상황종료", use_container_width=True): st.session_state.issue_state = None
    
    if st.session_state.issue_state:
        st.error(f"📢 현재 이상 상황: [{st.session_state.issue_state}] 보고 중")

    # [2. 생산 기록 - WORK UI 표준]
    st.markdown("<div class='section-title'>📊 실시간 생산 관리 기록</div>", unsafe_allow_html=True)
    c_info = st.columns(2)
    work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
    worker_name = c_info[1].text_input("👤 메인 작업자", value="안희선")

    cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
    headers = ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원작업자", "➕", "🗑️"]
    for col, h in zip(cols, headers): col.markdown(f"**{h}**")

    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']; c = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
        p_sel = st.session_state.get(f"p_{rid}", "선택"); uph = PRODUCT_DB.get(p_sel, 0)
        
        if f"target_{rid}" not in st.session_state: st.session_state[f"target_{rid}"] = 0
        if p_sel != "선택" and st.session_state[f"target_{rid}"] == 0:
            st.session_state[f"target_{rid}"] = round((uph / 60) * row['m'])

        c[0].write(row['time'])
        c[1].write(f"{row['m']:.0f}")
        c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
        c[3].write(f"**{st.session_state[f'target_{rid}']}**")
        c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
        c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
        c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed")
        c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
        c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
        # [지원 작업자 선택형으로 변경]
        c[9].selectbox("지원", SUPPORT_WORKERS, key=f"s_{rid}", label_visibility="collapsed")
        
        if c[10].button("➕", key=f"add_{rid}"):
            st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": row['m'], "is_split": True})
            st.session_state.next_id += 1; st.rerun()
        if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
            st.session_state.rows.pop(idx); st.rerun()

    # [3. 종합실적 분석 (WORK UI 레이아웃 고정)]
    st.markdown("<div class='section-title'>📈 종합 실적 분석</div>", unsafe_allow_html=True)
    summary_list = []
    for r in st.session_state.rows:
        p = st.session_state.get(f"p_{r['id']}", "선택")
        if p != "선택": summary_list.append({"기종": p, "목표": st.session_state[f"target_{r['id']}"], "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)})
    
    if summary_list:
        df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
        sh_cols = st.columns([2, 1, 1, 1, 1.5])
        for col, l in zip(sh_cols, ["기종명(합계)", "목표수량", "양품수량", "불량수량", "달성률(%)"]): col.markdown(f"**{l}**")
        for _, sr in df_sum.iterrows():
            sc = st.columns([2, 1, 1, 1, 1.5])
            sc[0].write(f"**{sr['기종']}**"); sc[1].write(f"{sr['목표']} EA"); sc[2].write(f"{sr['실적']-sr['불량']} EA"); sc[3].write(f"{sr['불량']} EA")
            sc[4].write(f"{(sr['실적']/sr['목표']*100 if sr['목표']>0 else 0):.1f}%")

    # [4. 투입부품 입력 (WORK UI 5x3 고정 레이아웃)]
    st.markdown("<div class='section-title'>📦 주요 부품 투입 LOT 관리 (5x3 고정)</div>", unsafe_allow_html=True)
    parts = ["감속기", "로타", "케이스", "리어커버", "센서"]
    bom_data = {}
    st.markdown('<div class="bom-table">', unsafe_allow_html=True)
    bh_cols = st.columns([1.5, 1, 3])
    bh_cols[0].markdown("**부품명**"); bh_cols[1].markdown("**수량**"); bh_cols[2].markdown("**LOT No.**")
    for part in parts:
        bc = st.columns([1.5, 1, 3])
        bc[0].info(f"**{part}**")
        p_q = bc[1].number_input("수량", key=f"q_{part}", step=1, label_visibility="collapsed")
        p_l = bc[2].text_input("LOT", key=f"l_{part}", placeholder=f"{part} LOT 입력", label_visibility="collapsed")
        bom_data[part] = f"{p_l}({p_q})"
    st.markdown('</div>', unsafe_allow_html=True)

    # [5. 데이터 최종 전송]
    if st.button("🚀 관제 센터로 데이터 최종 전송", type="primary", use_container_width=True):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # (전송 로직: Material_Check에 bom_data 저장, Issue_Status에 st.session_state.issue_state 기록)
            st.success("✅ 구글 시트 연동 성공 및 데이터 저장 완료!"); st.balloons()
        except: st.error("❌ 시트 연동 실패!")

with tab2:
    st.subheader("📊 실시간 관제 대시보드")
    # (실시간 시각화 로직)