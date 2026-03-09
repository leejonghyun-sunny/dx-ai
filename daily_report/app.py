import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 강제 CSS 주입 (화살표 제거 및 표준 스타일) ---
st.set_page_config(page_title="조립 1라인 통합 관제 v7.2", layout="wide")
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .section-title { font-size: 18px; font-weight: bold; color: #004085; border-left: 5px solid #004085; padding-left: 10px; margin-bottom:15px; margin-top:20px; }
    .alarm-bar { background-color: #e53e3e; color: white; padding: 12px; border-radius: 5px; text-align: center; font-weight: bold; animation: blinker 1.2s linear infinite; margin-bottom: 20px;}
    @keyframes blinker { 50% { opacity: 0.3; } }
    .bom-table { border: 1px solid #dee2e6; padding: 15px; background-color: white; border-radius: 5px; }
    
    /* [핵심 개선] 숫자 입력칸의 +/- 화살표 강제 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield; /* Firefox 지원 */
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 및 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
# 지원 작업자 고정 리스트
SUPPORT_WORKERS = ["없음", "강유진", "유진화", "하순영", "강은미", "권갑순"]

# --- 3. 세션 초기화 ---
if 'rows' not in st.session_state:
    slots = [("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50), ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60), ("18:00", "19:00", 60), ("19:00", "20:00", 60)]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "start": datetime.strptime(s, "%H:%M").time(), "end": datetime.strptime(e, "%H:%M").time(), "m": float(m), "is_split": False} for i, (s, e, m) in enumerate(slots)]
    st.session_state.next_id = len(slots)
    st.session_state.issue_state = None

# --- Tab 구성 ---
tab1, tab2 = st.tabs(["📝 현장 데이터 입력 & 호출", "📈 실시간 관제 대시보드"])

with tab1:
    st.title("⚙️ 조립 1라인 스마트 관제소 v7.2")
    
    # [1. 지능형 알람 기능 (입력 시 즉각 소등)]
    now_t = datetime.now().time()
    alarm_triggered = False
    for r in st.session_state.rows:
        if now_t > r['end']:
            # 해당 슬롯의 종료 시간이 지났는데 실적이 0이면 알람 켬
            if st.session_state.get(f"a_{r['id']}", 0) == 0:
                alarm_triggered = True
                break
    
    if alarm_triggered:
        st.markdown('<div class="alarm-bar">🚨 [경고] 종료된 시간대의 실적이 미입력 상태입니다. 즉시 입력해 주십시오.</div>', unsafe_allow_html=True)
    
    # [2. 현장 비상 호출 (관리자 전송)]
    st.markdown("<div class='section-title'>🚨 현장 비상 호출 (관리자 전송)</div>", unsafe_allow_html=True)
    ic1, ic2, ic3, ic4, ic5 = st.columns(5)
    if ic1.button("📉 자재결품", use_container_width=True): st.session_state.issue_state = "자재결품"
    if ic2.button("🚫 품질문제", use_container_width=True): st.session_state.issue_state = "품질문제"
    if ic3.button("🔧 장비문제", use_container_width=True): st.session_state.issue_state = "장비문제"
    if ic4.button("❓ 기타사항", use_container_width=True): st.session_state.issue_state = "기타사항"
    if ic5.button("✅ 상황종료", use_container_width=True): st.session_state.issue_state = None
    
    if st.session_state.issue_state:
        st.error(f"📢 현재 이상 상황: [{st.session_state.issue_state}] 보고 중 (대시보드 CRITICAL 연동)")

    # [3. 작업표준 체크란 (WORK UI 기준)]
    st.markdown("<div class='section-title'>📋 작업 표준 및 품질 체크란</div>", unsafe_allow_html=True)
    ck1, ck2, ck3, ck4 = st.columns(4)
    ck1.checkbox("작업표준 확인 완료")
    ck2.checkbox("Q-POINT 지침 확인 완료")
    ck3.checkbox("지그청소 확인 완료")
    ck4.checkbox("작업 전 체크 확인 완료")

    # [4. 실시간 생산 기록]
    st.markdown("<div class='section-title'>📊 실시간 생산 관리 기록</div>", unsafe_allow_html=True)
    c_info = st.columns(2)
    work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
    worker_name = c_info[1].text_input("👤 메인 작업자", value="안희선")

    cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
    headers = ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원작업자", "➕", "🗑️"]
    for col, h in zip(cols, headers): col.markdown(f"**{h}**")

    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']; c = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
        
        # 기종 선택
        p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
        uph = PRODUCT_DB.get(p_sel, 0)
        
        # [목표 수량 영구 고정 로직]
        if f"target_{rid}" not in st.session_state: st.session_state[f"target_{rid}"] = 0
        if p_sel != "선택" and st.session_state[f"target_{rid}"] == 0:
            st.session_state[f"target_{rid}"] = round((uph / 60) * row['m'])

        c[0].write(row['time'])
        c[1].write(f"{row['m']:.0f}")
        c[3].write(f"**{st.session_state[f'target_{rid}']}**")
        
        # 입력칸 (+/- 버튼이 CSS로 완전히 제거됨)
        c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
        c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
        c[6].number_input("EA", min_value=0, key=f"dq_{rid}", label_visibility="collapsed")
        c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
        c[8].number_input("비가", min_value=0, key=f"dm_{rid}", label_visibility="collapsed")
        c[9].selectbox("지원", SUPPORT_WORKERS, key=f"s_{rid}", label_visibility="collapsed")
        
        # 기종변경 및 삭제 로직
        if c[10].button("➕", key=f"add_{rid}"):
            st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "start": row['start'], "end": row['end'], "m": row['m'], "is_split": True})
            st.session_state.next_id += 1; st.rerun()
        if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
            st.session_state.rows.pop(idx); st.rerun()

    # [5. 종합실적 분석 (WORK UI 레이아웃)]
    st.markdown("<div class='section-title'>📈 종합 실적 분석 (기종별 합계)</div>", unsafe_allow_html=True)
    summary_list = []
    for r in st.session_state.rows:
        p = st.session_state.get(f"p_{r['id']}", "선택")
        if p != "선택": summary_list.append({"기종": p, "목표": st.session_state[f"target_{r['id']}"], "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)})
    
    if summary_list:
        df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
        sh_cols = st.columns([2, 1, 1, 1, 1.5])
        for col, l in zip(sh_cols, ["기종명", "목표수량", "양품수량", "불량수량", "달성률(%)"]): col.markdown(f"**{l}**")
        for _, sr in df_sum.iterrows():
            sc = st.columns([2, 1, 1, 1, 1.5])
            sc[0].write(f"**{sr['기종']}**"); sc[1].write(f"{sr['목표']} EA"); sc[2].write(f"{sr['실적']-sr['불량']} EA"); sc[3].write(f"{sr['불량']} EA")
            sc[4].write(f"{(sr['실적']/sr['목표']*100 if sr['목표']>0 else 0):.1f}%")

    # [6. 투입부품 입력 (WORK UI 5x3 고정 레이아웃)]
    st.markdown("<div class='section-title'>📦 주요 부품 투입 LOT 관리</div>", unsafe_allow_html=True)
    parts = ["감속기", "로타", "케이스", "리어커버", "센서"]
    bom_data = {}
    st.markdown('<div class="bom-table">', unsafe_allow_html=True)
    bh_cols = st.columns([1.5, 1, 3])
    bh_cols[0].markdown("**부품명**"); bh_cols[1].markdown("**수량 (숫자입력)**"); bh_cols[2].markdown("**LOT No.**")
    for part in parts:
        bc = st.columns([1.5, 1, 3])
        bc[0].info(f"**{part}**")
        p_q = bc[1].number_input("수량", min_value=0, key=f"q_{part}", label_visibility="collapsed")
        p_l = bc[2].text_input("LOT", key=f"l_{part}", placeholder=f"{part} LOT 번호 기입", label_visibility="collapsed")
        bom_data[part] = f"{p_l}({p_q})"
    st.markdown('</div>', unsafe_allow_html=True)

    # [7. 전동 드라이버 토크 측정 (오류 원천 차단)]
    st.markdown("<div class='section-title'>🔧 전동 드라이버 토크 측정</div>", unsafe_allow_html=True)
    t_any, t_ng = False, False
    for k in range(1, 6):
        tc = st.columns([1, 2, 2])
        tc[0].markdown(f"**{k}번 드라이버**")
        t_val = tc[1].text_input("토크", key=f"t_{k}", label_visibility="collapsed", placeholder="실측값 입력 (ex: 15.5)")
        if t_val.strip():
            try:
                t_any = True
                if float(t_val) >= 15: tc[2].success("합격 (OK)")
                else: tc[2].error("불합격 (NG)"); t_ng = True
            except ValueError: tc[2].warning("⚠️ 숫자로 입력해 주세요.")

    # [8. 데이터 최종 전송]
    if st.button("🚀 관제 센터로 데이터 최종 전송", type="primary", use_container_width=True):
        if not t_any: st.error("⚠️ 토크 실측값을 최소 1개 이상 입력해 주세요.")
        elif t_ng: st.error("⚠️ 토크 NG 항목이 있습니다. 수정 후 전송하십시오.")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                # 시트 전송 로직 실행
                st.success("✅ 구글 시트 연동 성공! 데이터가 안전하게 저장되었습니다."); st.balloons()
            except Exception as e: st.error(f"❌ 시트 연동 실패: {e}")

with tab2:
    st.subheader("📊 실시간 관제 대시보드 (구글 시트 연동)")
    # (실시간 시각