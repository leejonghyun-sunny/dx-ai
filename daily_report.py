import streamlit as st
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. 페이지 설정 및 시각적 스타일 (이사님 지침 반영) ---
st.set_page_config(page_title="조립 1라인 스마트 작업일보", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-title { font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #58a6ff; border-left: 5px solid #58a6ff; padding-left: 10px; }
    .highlight-box { background-color: yellow; color: red; padding: 12px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 15px; border: 2px solid red; font-size: 18px; }
    .ok-label { background-color: #28a745; color: #004085; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; }
    .ng-label { background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; border: 1px solid white; }
    .stButton>button { width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터베이스 설정 (기종별 고유 UPH) ---
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

# --- 3. 기본 정보 입력 ---
st.title("⚙️ 조립 1라인 스마트 작업일보 (버전 4.4)")
c_info1, c_info2 = st.columns(2)
with c_info1: work_date = st.date_input("🗓️ 작업일자", datetime.today())
with c_info2: worker_name = st.text_input("👤 메인 작업자명", value="안희선")

# --- 4. 1. 실시간 생산 기록 (이사님 CT 수식 및 Target Lock 적용) ---
st.markdown("<div class='section-title'>📊 1. 실시간 생산 기록</div>", unsafe_allow_html=True)

if 'rows' not in st.session_state:
    st.session_state.rows = []
    for i, (s, e) in enumerate(TIME_SLOTS_BASE):
        st.session_state.rows.append({
            "id": i, "display_time": f"{s}~{e}",
            "start": datetime.strptime(s, "%H:%M"), "end": datetime.strptime(e, "%H:%M"),
            "m": 60.0 if i not in [3, 6] else 50.0,
            "is_split": False, "fixed_target": 0
        })
    st.session_state.next_id = len(TIME_SLOTS_BASE)

cols_h = [1.3, 0.7, 1.8, 0.7, 0.7, 1.0, 0.6, 1.0, 0.7, 0.8, 0.9]
h_cols = st.columns(cols_h)
for i, h in enumerate(["시간대", "생산분", "기종명", "목표", "실적", "불량명", "불량", "사유", "비가", "지원", "기종변경"]):
    h_cols[i].markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns(cols_h)
    c[0].write(row['display_time'])
    
    p_sel = st.session_state.get(f"p_{rid}", "선택")
    act_val = st.session_state.get(f"a_{rid}", 0)
    uph_base = PRODUCT_DB.get(p_sel, 65)

    # [핵심 로직: CT 기반 생산분 및 목표 고정]
    if row['is_split']:
        # 기종변경 슬롯: 분(m)과 목표를 실적 입력에 상관없이 고정 (Lock)
        inv_m = c[1].number_input("분", value=float(row['m']), key=f"m_{rid}", disabled=True, label_visibility="collapsed")
        target = row['fixed_target']
    else:
        # 일반 슬롯: 이사님 8단계 수식 적용 (실적 입력 시 생산분 자동 계산)
        if p_sel != "선택" and act_val > 0:
            calc_m = round((act_val * (3600 / uph_base)) / 60, 1)
            st.session_state[f"m_{rid}"] = float(calc_m)
        elif f"m_{rid}" not in st.session_state:
            st.session_state[f"m_{rid}"] = float(row['m'])
        
        inv_m = c[1].number_input("분", key=f"m_{rid}", label_visibility="collapsed")
        target = round((uph_base / 60) * inv_m) if p_sel != "선택" else 0

    c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
    c[3].write(f"**{target}**") 

    c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
    c[5].selectbox("불량명", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("EA", key=f"dq_{rid}", label_visibility="collapsed", min_value=0)
    c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
    down_m = c[8].number_input("비가", key=f"dm_{rid}", label_visibility="collapsed", min_value=0)
    c[9].text_input("지원", key=f"s_{rid}", label_visibility="collapsed")
    
    if c[10].button("➕", key=f"add_{rid}"):
        total_used = inv_m + down_m
        new_start_dt = row['start'] + timedelta(minutes=total_used)
        if new_start_dt < row['end']:
            rem_m = round((row['end'] - new_start_dt).total_seconds() / 60, 1)
            st.session_state.rows.insert(idx + 1, {
                "id": st.session_state.next_id,
                "display_time": f"{new_start_dt.strftime('%H:%M')}~{row['end'].strftime('%H:%M')}",
                "start": new_start_dt, "end": row['end'], 
                "m": rem_m, "is_split": True, 
                "fixed_target": round((uph_base / 60) * rem_m, 1) 
            })
            st.session_state.next_id += 1
            st.rerun()

# --- 5. 2. 실적 분석 및 품질 추적 (종합 실적 집계) ---
st.markdown("<div class='section-title'>📋 2. 실적 분석 및 품질 추적 (기종별 통합 관리)</div>", unsafe_allow_html=True)
summary_data = []
first_appearance = {}
for idx, r in enumerate(st.session_state.rows):
    rid = r['id']
    p_name = st.session_state.get(f"p_{rid}", "선택")
    if p_name != "선택":
        summary_data.append({"p_name": p_name, "actual": st.session_state.get(f"a_{rid}", 0), "defect": st.session_state.get(f"dq_{rid}", 0)})
        if p_name not in first_appearance: first_appearance[p_name] = idx

if summary_data:
    df_sum = pd.DataFrame(summary_data).groupby("p_name").agg({'actual': 'sum', 'defect': 'sum'}).reset_index()
    df_sum['f_idx'] = df_sum['p_name'].map(first_appearance)
    df_sum = df_sum.sort_values(by='f_idx').reset_index(drop=True)
    ah_cols = st.columns([1.5, 1, 1, 1, 2.5])
    for i, h in enumerate(["기종명(합계)", "양품수량", "불량수량", "불량율(%)", "LOT 넘버 입력"]): ah_cols[i].markdown(f"**{h}**")
    for idx, row in df_sum.iterrows():
        ac = st.columns([1.5, 1, 1, 1, 2.5])
        good = row['actual'] - row['defect']
        rate = (row['defect'] / row['actual'] * 100) if row['actual'] > 0 else 0
        ac[0].write(f"**{row['p_name']}**")
        ac[1].write(f"{good} EA"); ac[2].write(f"{row['defect']} EA"); ac[3].write(f"{rate:.1f}%")
        st.session_state[f"lot_total_{row['p_name']}"] = ac[4].text_input(f"LOT ({row['p_name']})", key=f"lot_sum_{idx}", label_visibility="collapsed", placeholder="LOT 입력")

# --- 6. 3. 전동 드라이버 토크 측정 기록 (스마트 알람) ---
st.markdown("<div class='section-title'>🔧 3. 전동 드라이버 토크 측정 기록</div>", unsafe_allow_html=True)
torque_list = [st.session_state.get(f"torque_{k}", "").strip() for k in range(1, 6)]
if all(v == "" for v in torque_list):
    st.markdown('<div class="highlight-box">전동드라이버 토크 측정 하세요</div>', unsafe_allow_html=True)

t_c1, t_c2 = st.columns([1.5, 2.5])
with t_c1:
    valid_torque = True
    for k in range(1, 6):
        tr = st.columns([0.4, 1.6, 1.0])
        tr[0].markdown(f"<div style='padding-top:10px;'>{k}번</div>", unsafe_allow_html=True)
        t_val = tr[1].text_input(f"T_{k}", key=f"torque_{k}", label_visibility="collapsed", placeholder="Kgf/cm")
        if t_val:
            try:
                val = float(t_val)
                if val >= 15: tr[2].markdown('<div class="ok-label">OK</div>', unsafe_allow_html=True)
                else: 
                    tr[2].markdown('<div class="ng-label">NG</div>', unsafe_allow_html=True)
                    st.error(f"{k}번 토크 불량!"); valid_torque = False
            except: valid_torque = False
        else: valid_torque = False
with t_c2:
    st.markdown('<div class="highlight-box"> 전동 드라이버 토크 실측값을 전동드라이버 번호대로 반드시 입력 하세요 !</div>', unsafe_allow_html=True)

# --- 7. 데이터 최종 전송 (구글 시트 칼럼 매핑 최적화) ---
if st.button("📊 오늘의 실적 데이터 최종 전송 및 저장", type="primary", use_container_width=True):
    if all(torque_list) and valid_torque:
        conn = st.connection("gsheets", type=GSheetsConnection)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_data = []
        for r in st.session_state.rows:
            rid = r['id']; p = st.session_state.get(f"p_{rid}", "선택")
            if p != "선택":
                # [이사님 구글 시트 칼럼명에 정확히 매칭]
                final_data.append({
                    "Timestamp": ts,
                    "Work_Date": work_date.strftime("%Y-%m-%d"),
                    "Worker_Name": worker_name,
                    "Time_Slot": r['display_time'],
                    "Invested_Min": st.session_state.get(f"m_{rid}", 0), # 생산분
                    "Item_Name": p,
                    "Target_UPH": round((PRODUCT_DB.get(p, 0) / 60) * st.session_state.get(f"m_{rid}", 0), 1), # 목표
                    "Actual_Qty": st.session_state.get(f"a_{rid}", 0), # 실적
                    "Defect_Type": st.session_state.get(f"dt_{rid}", "없음"), # 불량명
                    "Defect_Qty": st.session_state.get(f"dq_{rid}", 0), # 불량수
                    "Downtime_Reas": st.session_state.get(f"dr_{rid}", "없음"), # 비가동사유
                    "Downtime_Min": st.session_state.get(f"dm_{rid}", 0), # 비가동분
                    "Torque_Value": " / ".join(torque_list),
                    "Material_Check": st.session_state.get(f"lot_total_{p}", "") # LOT
                })
        if final_data:
            # 시트 이름 'sheet1' (소문자) 및 ID 확인 완료
            df = conn.read(worksheet="sheet1")
            updated = pd.concat([df, pd.DataFrame(final_data)], ignore_index=True)
            conn.update(worksheet="sheet1", data=updated)
            st.success("✅ 전송 완료!"); st.balloons()
