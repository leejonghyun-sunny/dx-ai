import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 시각적 스타일 ---
st.set_page_config(page_title="조립 1라인 통합 관제 v6.0", layout="wide")
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; margin-top: 20px; margin-bottom:15px; }
    .alarm-bar { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px; animation: blinker 1.5s linear infinite; margin-bottom: 20px; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .issue-card { background-color: #2d3748; padding: 15px; border-radius: 10px; border: 2px solid #e53e3e; margin-bottom: 20px; }
    .ok-label { background-color: #28a745; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
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
tab1, tab2 = st.tabs(["📝 현장 데이터 입력 & 호출", "📈 실시간 관제 대시보드"])

with tab1:
    st.title("⚙️ 조립 1라인 스마트 관제소 v6.0")
    
    # [1. 시각적 알람 기능]
    # 현재 시간대 입력 확인용 (간이 로직: 입력 버튼 미클릭 시 노출)
    st.markdown('<div class="alarm-bar">🚨 [경고] 현재 시간대 생산 데이터 미전송! 관리자 호출 대기 중</div>', unsafe_allow_html=True)

    # [2. 관리자 호출 및 이상 발생 섹션]
    st.markdown("<div class='section-title'>🚨 현장 이상 발생 - 관리자 호출</div>", unsafe_allow_html=True)
    if 'issue_state' not in st.session_state: st.session_state.issue_state = None
    
    with st.container():
        st.markdown('<div class="issue-card">', unsafe_allow_html=True)
        i_col1, i_col2, i_col3, i_col4, i_col5 = st.columns(5)
        if i_col1.button("📉 자재결품", use_container_width=True): st.session_state.issue_state = "자재결품"
        if i_col2.button("🚫 품질문제", use_container_width=True): st.session_state.issue_state = "품질문제"
        if i_col3.button("🔧 장비문제", use_container_width=True): st.session_state.issue_state = "장비문제"
        if i_col4.button("❓ 기타사항", use_container_width=True): st.session_state.issue_state = "기타사항"
        if i_col5.button("✅ 상황종료", use_container_width=True): st.session_state.issue_state = None
        
        if st.session_state.issue_state:
            st.error(f"📢 현재 상황: [{st.session_state.issue_state}] - 관리자 대시보드에 CRITICAL 기록 중")
        st.markdown('</div>', unsafe_allow_html=True)

    c_i1, c_i2 = st.columns(2)
    work_date = c_i1.date_input("🗓️ 작업일자", datetime.today())
    worker_name = c_i2.text_input("👤 작업자명", value="안희선")

    # [3. 실시간 생산 기록]
    st.markdown("<div class='section-title'>📊 1. 생산 실적 기록 (목표 고정 모드)</div>", unsafe_allow_html=True)
    if 'rows' not in st.session_state:
        slots = [("08:30", "09:30"), ("09:30", "10:30"), ("10:40", "11:40"), ("11:40", "12:30"), ("13:20", "14:30"), ("14:30", "15:30"), ("15:40", "16:30"), ("16:30", "17:30")]
        st.session_state.rows = [{"id": i, "display_time": f"{s}~{e}", "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"), "m": 60.0, "is_split": False, "fixed_target": 0} for i, (s, e) in enumerate(slots)]
        st.session_state.next_id = len(slots)

    cols_h = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.6, 0.6])
    h_labels = ["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "변경", "삭제"]
    for i, h in enumerate(h_labels): cols_h[i].markdown(f"**{h}**")

    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']; c = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.6, 0.6])
        p_sel = st.session_state.get(f"p_{rid}", "선택"); act_qty = st.session_state.get(f"a_{rid}", 0); uph = PRODUCT_DB.get(p_sel, 65)

        if row['is_split']:
            inv_m = c[1].number_input("분", value=float(row['m']), key=f"m_{rid}", disabled=True, label_visibility="collapsed")
            target = row['fixed_target']
        else:
            calc_m = round((act_qty * (3600 / uph)) / 60, 1) if p_sel != "선택" and act_qty > 0 else row['m']
            st.session_state[f"m_{rid}"] = float(calc_m)
            inv_m = c[1].number_input("분", key=f"m_{rid}", label_visibility="collapsed")
            target = round((uph / 60) * inv_m) if p_sel != "선택" else 0

        c[0].write(row['display_time'])
        c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
        c[3].write(f"**{target}**")
        c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
        c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
        c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed")
        c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
        dm = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed")
        c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
        if c[10].button("➕", key=f"add_{rid}"):
            new_s = row['start'] + timedelta(minutes=inv_m + dm)
            if new_s < row['end']:
                rem = round((row['end'] - new_s).total_seconds() / 60, 1)
                st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "display_time": f"{new_s.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}", "start": new_s, "end": row['end'], "m": rem, "is_split": True, "fixed_target": round((uph / 60) * rem, 1)})
                st.session_state.next_id += 1; st.rerun()
        if row['is_split'] and c[11].button("🗑️", key=f"del_{rid}"): st.session_state.rows.pop(idx); st.rerun()

    # [4. 주요 자재 투입 관리 (5x3 고정 테이블)]
    st.markdown("<div class='section-title'>📦 2. 주요 자재 투입 관리 (고정 BOM)</div>", unsafe_allow_html=True)
    parts = ["감속기", "로타", "케이스", "리어커버", "센서"]
    bom_data = {}
    b_h1, b_h2, b_h3 = st.columns([2, 1, 3])
    b_h1.markdown("**부품명**"); b_h2.markdown("**수량**"); b_h3.markdown("**LOT No.**")
    for part in parts:
        bc = st.columns([2, 1, 3])
        bc[0].info(f"**{part}**")
        p_q = bc[1].number_input(f"q_{part}", min_value=0, value=0, label_visibility="collapsed")
        p_l = bc[2].text_input(f"l_{part}", placeholder=f"{part} LOT 입력", label_visibility="collapsed")
        bom_data[part] = f"{p_l}({p_q})"

    # [5. 토크 기록]
    st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정</div>", unsafe_allow_html=True)
    v_any, ng_f = False, False
    t_list = []
    for k in range(1, 6):
        tr = st.columns([0.5, 1.5, 1.0])
        tr[0].write(f"**{k}번**")
        tv = tr[1].text_input(f"T{k}", key=f"torque_{k}", label_visibility="collapsed")
        t_list.append(tv)
        if tv:
            v_any = True
            if float(tv) >= 15: tr[2].markdown('<div class="ok-label">OK</div>', unsafe_allow_html=True)
            else: tr[2].markdown('<div class="ng-label">NG</div>', unsafe_allow_html=True); ng_f = True

    # [6. 데이터 통합 전송]
    if st.button("📊 오늘의 스마트 관제 데이터 최종 전송", type="primary"):
        if not v_any: st.error("⚠️ 토크 값을 입력하세요!")
        elif ng_f: st.error("⚠️ 토크 NG 항목이 있습니다!")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                bom_str = " / ".join([f"{k}:{v}" for k, v in bom_data.items()])
                final_data = []
                for r in st.session_state.rows:
                    rid_f = r['id']; p = st.session_state.get(f"p_{rid_f}", "선택")
                    if p != "선택":
                        final_data.append({
                            "Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": worker_name,
                            "Time_Slot": r['display_time'], "Invested_Min": st.session_state.get(f"m_{rid_f}", 0),
                            "Item_Name": p, "Target_UPH": round((PRODUCT_DB.get(p, 65) / 60) * st.session_state.get(f"m_{rid_f}", 0), 1),
                            "Actual_Qty": st.session_state.get(f"a_{rid_f}", 0), "Defect_Type": st.session_state.get(f"dt_{rid_f}", "없음"),
                            "Defect_Qty": st.session_state.get(f"dq_{rid_f}", 0), "Downtime_Reas": st.session_state.get(f"dr_{rid_f}", "없음"),
                            "Downtime_Min": st.session_state.get(f"dm_{rid_f}", 0), "Torque_Value": " / ".join(t_list),
                            "Material_Check": bom_str, 
                            "Issue_Status": "[CRITICAL]" if st.session_state.issue_state else "NORMAL",
                            "Issue_Type": st.session_state.issue_state if st.session_state.issue_state else "None"
                        })
                df = conn.read(worksheet="sheet1")
                conn.update(worksheet="sheet1", data=pd.concat([df, pd.DataFrame(final_data)], ignore_index=True))
                st.success("✅ 관제 센터로 데이터가 동기화되었습니다!"); st.balloons()
            except Exception as e: st.error(f"연동 실패: {e}")

# --- Tab 2: 실시간 관제 대시보드 ---
with tab2:
    st.subheader("📊 조립 1라인 실시간 생산 관제 센터")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_all = conn.read(worksheet="sheet1")
        if not df_all.empty:
            df_t = df_all[df_all['Work_Date'] == datetime.today().strftime("%Y-%m-%d")]
            if not df_t.empty:
                m1, m2, m3 = st.columns(3)
                tar, act = df_t['Target_UPH'].sum(), df_t['Actual_Qty'].sum()
                m1.metric("누적 목표", f"{tar:.0f} EA")
                m2.metric("누적 실적", f"{act} EA", f"{act-tar:.0f}")
                m3.metric("달성률", f"{(act/tar*100):.1f}%" if tar>0 else "0%")
                
                c1, c2 = st.columns(2)
                fig1 = px.line(df_t, x='Time_Slot', y=['Target_UPH', 'Actual_Qty'], title="시간대별 목표/실적 추이", markers=True)
                c1.plotly_chart(fig1, use_container_width=True)
                
                # 이상 상황 발생 이력 표시
                st.markdown("<div class='section-title'>🚨 오늘 발생한 현장 이상 이력</div>", unsafe_allow_html=True)
                df_critical = df_t[df_t['Issue_Status'] == "[CRITICAL]"][['Timestamp', 'Issue_Type', 'Worker_Name', 'Time_Slot']]
                if not df_critical.empty: st.table(df_critical)
                else: st.info("현재까지 발생한 이상 상황이 없습니다.")
    except: st.warning("데이터 로딩 중...")