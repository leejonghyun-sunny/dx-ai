import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 시각적 스타일 ---
st.set_page_config(page_title="조립 1라인 통합 관제 시스템", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 15px; border: 2px solid red; font-size: 18px; }
    .ok-label { background-color: #28a745; color: #004085; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; border: 1px solid white; }
    .stButton>button { width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 및 시간 설정 ---
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

# --- 탭 구성 (입력과 분석의 분리) ---
tab1, tab2 = st.tabs(["📝 현장 데이터 입력 (Ver 4.5+)", "📈 실시간 보는 관리 (Dashboard)"])

# --- Tab 1: 데이터 입력 레이어 ---
with tab1:
    st.title("⚙️ 조립 1라인 스마트 작업일보")
    c_i1, c_i2 = st.columns(2)
    with c_i1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
    with c_i2: worker_name = st.text_input("👤 작업자명", value="안희선")

    if 'rows' not in st.session_state:
        st.session_state.rows = []
        for i, (s, e) in enumerate(TIME_SLOTS_BASE):
            st.session_state.rows.append({"id": i, "display_time": f"{s}~{e}", "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"), "m": 60.0 if i not in [3, 6] else 50.0, "is_split": False, "fixed_target": 0})
        st.session_state.next_id = len(TIME_SLOTS_BASE)

    st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)
    cols_h = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.9])
    for i, h in enumerate(["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "변경"]): cols_h[i].markdown(f"**{h}**")

    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']; c = st.columns([1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.9])
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
        c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
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

    st.markdown("<div class='section-title'>🔧 2. 전동 드라이버 토크 (1개 이상 필수)</div>", unsafe_allow_html=True)
    t_vals = [st.session_state.get(f"torque_{k}", "") for k in range(1, 6)]
    v_any, ng_f = False, False
    tc = st.columns(5)
    for k in range(1, 6):
        tv = tc[k-1].text_input(f"{k}번 (Kgf/cm)", key=f"torque_{k}")
        if tv:
            try:
                v_any = True
                if float(tv) < 15: ng_f = True; st.warning(f"{k}번 NG")
            except: ng_f = True

    if st.button("📊 오늘의 실적 데이터 최종 전송", type="primary"):
        if not v_any: st.error("⚠️ 토크 값을 입력하세요!")
        elif ng_f: st.error("⚠️ 토크 NG가 있습니다!")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_data = []
                for r in st.session_state.rows:
                    rid = r['id']; p = st.session_state.get(f"p_{rid}", "선택")
                    if p != "선택":
                        final_data.append({"Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": worker_name, "Time_Slot": r['display_time'], "Invested_Min": st.session_state.get(f"m_{rid}", 0), "Item_Name": p, "Target_UPH": round((PRODUCT_DB.get(p, 65) / 60) * st.session_state.get(f"m_{rid}", 0), 1), "Actual_Qty": st.session_state.get(f"a_{rid}", 0), "Defect_Type": st.session_state.get(f"dt_{rid}", "없음"), "Defect_Qty": st.session_state.get(f"dq_{rid}", 0), "Downtime_Reas": st.session_state.get(f"dr_{rid}", "없음"), "Downtime_Min": st.session_state.get(f"dm_{rid}", 0), "Torque_Value": " / ".join(t_vals), "Material_Check": ""})
                df = conn.read(worksheet="sheet1")
                conn.update(worksheet="sheet1", data=pd.concat([df, pd.DataFrame(final_data)], ignore_index=True))
                st.success("✅ 전송 완료!"); st.balloons()
            except Exception as e: st.error(f"전송 실패: {e}")

# --- Tab 2: 실시간 관제 레이어 (보는 관리) ---
with tab2:
    st.subheader("📊 조립 1라인 실시간 생산 관제")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_all = conn.read(worksheet="sheet1")
        if not df_all.empty:
            df_t = df_all[df_all['Work_Date'] == datetime.today().strftime("%Y-%m-%d")]
            if not df_t.empty:
                m1, m2, m3 = st.columns(3)
                tar, act = df_t['Target_UPH'].sum(), df_t['Actual_Qty'].sum()
                m1.metric("오늘의 목표", f"{tar:.0f} EA")
                m2.metric("현재 실적", f"{act} EA", f"{act-tar:.0f}")
                m3.metric("달성률", f"{(act/tar*100):.1f}%" if tar>0 else "0%")
                
                c1, c2 = st.columns(2)
                fig1 = px.line(df_t, x='Time_Slot', y=['Target_UPH', 'Actual_Qty'], title="시간대별 목표 vs 실적 추이", markers=True)
                c1.plotly_chart(fig1, use_container_width=True)
                fig2 = px.bar(df_t.groupby('Item_Name')['Actual_Qty'].sum().reset_index(), x='Item_Name', y='Actual_Qty', title="기종별 누적 생산량", color='Item_Name')
                c2.plotly_chart(fig2, use_container_width=True)
            else: st.info("오늘 입력된 데이터가 없습니다.")
    except: st.warning("데이터를 불러오는 중입니다...")
