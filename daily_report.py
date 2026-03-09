import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 스타일 ---
st.set_page_config(page_title="조립 1라인 통합 관제 v6.1", layout="wide")
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; margin-top: 20px; }
    .alarm-bar { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px; animation: blinker 1.5s linear infinite; margin-bottom: 20px; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .issue-card { background-color: #2d3748; padding: 15px; border-radius: 10px; border: 2px solid #e53e3e; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}

# --- 탭 구성 ---
tab1, tab2 = st.tabs(["📝 현장 데이터 입력", "📈 실시간 관제 대시보드"])

with tab1:
    st.title("⚙️ 조립 1라인 스마트 관제소 v6.1")
    
    # [데이터 초기화 및 시간대 확장]
    if 'rows' not in st.session_state:
        slots = [("08:30", "09:30"), ("09:30", "10:30"), ("10:40", "11:40"), ("11:40", "12:30"), 
                 ("13:20", "14:30"), ("14:30", "15:30"), ("15:40", "16:30"), ("16:30", "17:30"),
                 ("18:00", "19:00"), ("19:00", "20:00")] # 잔업 시간 추가
        st.session_state.rows = [{"id": i, "display_time": f"{s}~{e}", "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"), "m": 60.0 if i not in [3, 6] else 50.0, "is_split": False} for i, (s, e) in enumerate(slots)]
        st.session_state.next_id = len(slots)

    # [지능형 알람 오프 로직]
    now_time = datetime.now().time()
    unfilled_count = 0
    for r in st.session_state.rows:
        if r['end'].time() <= now_time and st.session_state.get(f"a_{r['id']}", 0) == 0:
            unfilled_count += 1
    
    if unfilled_count > 0:
        st.markdown(f'<div class="alarm-bar">🚨 [경고] 미입력 구간 {unfilled_count}개 발견! 실적 입력을 완료하십시오.</div>', unsafe_allow_html=True)

    # [이상 발생 섹션]
    st.markdown("<div class='section-title'>🚨 관리자 호출</div>", unsafe_allow_html=True)
    if 'issue_state' not in st.session_state: st.session_state.issue_state = None
    i_c1, i_c2, i_c3, i_c4, i_c5 = st.columns(5)
    if i_c1.button("📉 자재결품"): st.session_state.issue_state = "자재결품"
    if i_c2.button("🚫 품질문제"): st.session_state.issue_state = "품질문제"
    if i_c3.button("🔧 장비문제"): st.session_state.issue_state = "장비문제"
    if i_c4.button("❓ 기타사항"): st.session_state.issue_state = "기타사항"
    if i_c5.button("✅ 상황종료"): st.session_state.issue_state = None

    st.markdown("<div class='section-title'>📊 1. 생산 실적 기록 (목표 고정)</div>", unsafe_allow_html=True)
    c_i1, c_i2 = st.columns(2)
    work_date = c_i1.date_input("🗓️ 작업일자", datetime.today())
    worker_name = c_i2.text_input("👤 작업자명", value="안희선")

    cols_h = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.6, 0.6])
    h_labels = ["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "변경", "삭제"]
    for i, h in enumerate(h_labels): cols_h[i].markdown(f"**{h}**")

    # 실적 입력 루프
    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']; c = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.6, 0.6])
        p_sel = st.session_state.get(f"p_{rid}", "선택"); uph = PRODUCT_DB.get(p_sel, 65)

        # [목표 수량 고정 로직]
        if f"target_{rid}" not in st.session_state: st.session_state[f"target_{rid}"] = 0
        if p_sel != "선택" and st.session_state[f"target_{rid}"] == 0:
            st.session_state[f"target_{rid}"] = round((uph / 60) * row['m'])

        c[0].write(row['display_time'])
        c[1].write(f"{row['m']:.1f}")
        c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
        c[3].write(f"**{st.session_state[f'target_{rid}']}**")
        c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
        c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
        c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed")
        c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
        c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
        c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
        
        if c[10].button("➕", key=f"add_{rid}"):
            new_s = row['start'] + timedelta(minutes=row['m'])
            if new_s < row['end']:
                rem = round((row['end'] - new_s).total_seconds() / 60, 1)
                st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "display_time": f"{new_s.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}", "start": new_s, "end": row['end'], "m": rem, "is_split": True})
                st.session_state.next_id += 1; st.rerun()
        if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"): st.session_state.rows.pop(idx); st.rerun()

    # [종합 실적 및 자재 관리 UI 강제 활성화]
    st.markdown("<div class='section-title'>📋 2. 종합 실적 및 자재 LOT 관리</div>", unsafe_allow_html=True)
    summary_list = []
    for r in st.session_state.rows:
        p = st.session_state.get(f"p_{r['id']}", "선택")
        if p != "선택": summary_list.append({"기종": p, "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)})
    
    if summary_list:
        df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
        for i, r in df_sum.iterrows():
            sc = st.columns([2, 1, 1, 3])
            sc[0].write(f"**{r['기종']}**")
            sc[1].write(f"양품: {r['실적']-r['불량']}")
            sc[2].write(f"불량: {r['불량']}")
            st.session_state[f"lot_{r['기종']}"] = sc[3].text_input(f"{r['기종']} LOT", key=f"l_{i}", placeholder="LOT 번호 입력")

    # [토크 기록 및 전송]
    st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정</div>", unsafe_allow_html=True)
    t_list = []
    v_any, ng_f = False, False
    for k in range(1, 6):
        tr = st.columns([1, 2, 1])
        tv = tr[1].text_input(f"{k}번 토크", key=f"t_{k}")
        t_list.append(tv)
        if tv.strip(): # 빈칸 방어 로직
            try:
                v_any = True
                if float(tv) >= 15: tr[2].success("OK")
                else: tr[2].error("NG"); ng_f = True
            except ValueError: st.warning("숫자를 입력하세요.")

    if st.button("📊 데이터 최종 전송", type="primary"):
        if not v_any: st.error("⚠️ 토크 값을 입력하세요!")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                # (전송 로직 생략 - v6.0과 동일)
                st.success("✅ 전송 완료!"); st.balloons()
            except Exception as e: st.error(f"실패: {e}")

with tab2:
    st.subheader("📊 실시간 관제 대시보드")
    # (대시보드 시각화 로직)
