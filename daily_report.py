import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 UI 고정 (다크테마 & 화살표 제거 강력 CSS) ---
st.set_page_config(page_title="스마트작업일보 조립1라인 (v7.5.9)", layout="wide")

st.markdown("""
<style>
    /* 모든 숫자 입력칸의 +/- 화살표 및 증감 버튼 완전 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; margin: 0 !important; }
    input[type=number] { -moz-appearance: textfield !important; }
    
    .section-title { font-size: 18px; font-weight: bold; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; margin-top:20px; margin-bottom:15px; }
    .stButton>button { border-radius: 5px; font-weight: bold; width: 100%; height: 45px; }
    .check-item-box { background-color: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; text-align: center; color: #c9d1d9; }
</style>
""", unsafe_allow_html=True)

# --- 2. 표준 데이터베이스 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
SUPPORT_WORKERS = ["없음", "강유진", "유진화", "하순영", "강은미", "권갑순"]
FIXED_WORKER_NAME = "안희선, 강선혜"

# --- 3. 세션 초기화 ---
if 'rows' not in st.session_state:
    slots = [("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50), ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60), ("18:00", "19:00", 60), ("19:00", "20:00", 60)]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "m": float(m), "is_split": False} for i, (s, e, m) in enumerate(slots)]
    st.session_state.next_id = len(slots)
    st.session_state.issue_state = None

# [타이틀 고정]
st.title("스마트작업일보 조립1라인 (v7.5.9)")

# [1. 통합 작업표준 확인 (문구 수정 반영)]
st.markdown("<div class='section-title'>📋 작업 표준 및 품질 통합 확인</div>", unsafe_allow_html=True)
c_all = st.checkbox("✅ 작업표준및 작업지침 4대항목 확인 완료", key="confirm_v759")
ck_cols = st.columns(4)
items = ["작업표준서 확인", "Q-POINT/지침 확인", "지그청소 상태 확인", "작업 전 자주검사"]
for col, item in zip(ck_cols, items):
    status = "🟢 확인" if c_all else "⚪ 미확인"
    col.markdown(f"<div class='check-item-box'><b>{item}</b><br>{status}</div>", unsafe_allow_html=True)

# [2. 현장 비상 호출 (기존 로직 원복)]
st.markdown("<div class='section-title'>🚨 현장 비상 호출</div>", unsafe_allow_html=True)
ic = st.columns(5)
for i, label in enumerate(["자재결품", "품질문제", "장비문제", "기타사항", "상황종료"]):
    if ic[i].button(label, key=f"btn_{label}"):
        st.session_state.issue_state = label if label != "상황종료" else None

# [3. 생산 기록 본문]
st.markdown("<div class='section-title'>📊 생산 관리 기록</div>", unsafe_allow_html=True)
c_info = st.columns(2)
work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
c_info[1].info(f"👤 메인 작업자: **{FIXED_WORKER_NAME}**")

cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
h_names = ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원", "➕", "🗑️"]
for col, h in zip(cols, h_names): col.markdown(f"**{h}**")

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
    dr = c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    dm = c[8].number_input("비가", min_value=0, key=f"dm_{rid}", label_visibility="collapsed")
    c[9].selectbox("지원", SUPPORT_WORKERS, key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕", key=f"add_{rid}"):
        used_m = round((act_qty * (3600 / uph)) / 60, 1) if uph > 0 else 0
        rem_m = row['m'] - used_m - dm 
        if rem_m > 0:
            st.session_state.rows[idx]['m'] = used_m
            st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": rem_m, "is_split": True})
            st.session_state.next_id += 1; st.rerun()
    if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
        st.session_state.rows.pop(idx); st.rerun()

# [4. 종합 실적 집계란 (달성률/불량률 자동 계산)]
st.markdown("<div class='section-title'>📦 종합 실적 분석 및 자재 투입 관리</div>", unsafe_allow_html=True)
sc1, sc2 = st.columns([1.8, 1])
with sc1:
    st.write("**기종별 생산 지표 분석 (실시간 자동 계산)**")
    summary_list = []
    for r in st.session_state.rows:
        p = st.session_state.get(f"p_{r['id']}", "선택")
        if p != "선택":
            summary_list.append({
                "기종": p, "목표": st.session_state.get(f"target_{r['id']}", 0),
                "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)
            })
    if summary_list:
        df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
        # 경영 지표 수식 적용
        df_sum['달성률'] = df_sum.apply(lambda x: f"{round((x['실적']/x['목표']*100),1)}%" if x['목표'] > 0 else "0%", axis=1)
        df_sum['불량률'] = df_sum.apply(lambda x: f"{round((x['불량']/x['실적']*100),1)}%" if x['실적'] > 0 else "0%", axis=1)
        
        h_sum = st.columns([1.5, 0.6, 0.6, 0.6, 0.8, 0.8, 1.5])
        for col, h in zip(h_sum, ["기종명", "목표", "실적", "불량", "달성률", "불량률", "기종별 LOT"]): col.markdown(f"**{h}**")
        for i, sr in df_sum.iterrows():
            r_sum = st.columns([1.5, 0.6, 0.6, 0.6, 0.8, 0.8, 1.5])
            r_sum[0].write(sr['기종']); r_sum[1].write(sr['목표']); r_sum[2].write(sr['실적']); r_sum[3].write(sr['불량'])
            r_sum[4].write(f"**{sr['달성률']}**"); r_sum[5].write(sr['불량률'])
            st.session_state[f"model_lot_{sr['기종']}"] = r_sum[6].text_input("LOT", key=f"mlot_{i}", label_visibility="collapsed")

with sc2:
    st.write("**주요 부품 LOT (5x3 고정)**")
    bom_data = {}
    for pt in ["감속기", "로타", "케이스", "리어커버", "센서"]:
        bc = st.columns([1, 1, 2.5])
        bc[0].info(f"**{pt}**")
        p_q = bc[1].number_input("수량", min_value=0, key=f"q_{pt}", label_visibility="collapsed")
        p_l = bc[2].text_input("LOT", key=f"l_{pt}", label_visibility="collapsed", placeholder="로트번호")
        bom_data[pt] = f"{p_l}({p_q})"

# [5. 데이터 전송 및 구글 시트 연동]
st.markdown("<div class='section-title'>🔧 전동 드라이버 토크 측정 (kgf-cm)</div>", unsafe_allow_html=True)
t_list = []
for k in range(1, 6):
    tc = st.columns([1, 2, 2])
    tc[0].write(f"**{k}번**"); t_v = tc[1].text_input("값", key=f"t_{k}", label_visibility="collapsed")
    t_list.append(t_v)
    if t_v.strip():
        try:
            if float(t_v.replace(',', '.')) >= 15: tc[2].success("OK")
            else: tc[2].error("NG")
        except: pass

if st.button("🚀 데이터 최종 전송 (v7.5.9)", type="primary"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bom_str = " / ".join([f"{k}:{v}" for k, v in bom_data.items()])
        final_data = []
        for r in st.session_state.rows:
            p = st.session_state.get(f"p_{r['id']}", "선택")
            if p != "선택":
                final_data.append({
                    "Timestamp": ts, "Work_Date": work_date.strftime("%Y-%m-%d"), "Worker_Name": FIXED_WORKER_NAME,
                    "Time_Slot": r['time'], "Invested_Min": r['m'], "Item_Name": p,
                    "Target_UPH": st.session_state.get(f"target_{r['id']}", 0),
                    "Actual_Qty": st.session_state.get(f"a_{r['id']}", 0), "Defect_Type": st.session_state.get(f"dt_{r['id']}", "없음"),
                    "Defect_Qty": st.session_state.get(f"dq_{r['id']}", 0), "Reason": st.session_state.get(f"dr_{r['id']}", "없음"),
                    "Downtime_Min": st.session_state.get(f"dm_{r['id']}", 0), "Torque_Value": " / ".join(t_list),
                    "Material_Check": bom_str, 
                    "Issue_Status": "[CRITICAL]" if st.session_state.issue_state else "NORMAL", # 비상상황 연동
                    "Issue_Type": st.session_state.issue_state if st.session_state.issue_state else "None",
                    "Model_Lot": st.session_state.get(f"model_lot_{p}", "")
                })
        df = conn.read(worksheet="sheet1")
        conn.update(worksheet="sheet1", data=pd.concat([df, pd.DataFrame(final_data)], ignore_index=True))
        st.success("✅ [버전 7.5.9] 전송 및 연동 성공!"); st.balloons()
    except Exception as e:
        st.error(f"❌ 전송 오류: {e}")
