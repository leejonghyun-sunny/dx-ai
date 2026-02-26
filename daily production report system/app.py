
import streamlit as st
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd
# --- 1. 페이지 설정 (태블릿 가로화면 최적화) ---
st.set_page_config(page_title="조립 1라인 실시간 작업일보 (시범운영)", layout="wide", page_icon="📝")

# --- CSS 주입 (number_input의 +/- 화살표 버튼 숨기기) ---
st.markdown("""
<style>
    /* Chrome, Safari, Edge, Opera 작동 */
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    /* Firefox 작동 */
    input[type=number] {
        -moz-appearance: textfield;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 내부 데이터 하드코딩 ---
# 1) 기종별 UPH 매핑 (50분, 60분, 70분)
PRODUCT_DB = {
    "VE, 100바, 6*14, 방화": {50: 54, 60: 65, 70: 76},
    "황동": {50: 34, 60: 40, 70: 46},
    "80각": {50: 35, 60: 42, 70: 49},
    "MC, 90W(태성)": {50: 36, 60: 45, 70: 54},
    "60W B/K, 90W B/K": {50: 25, 60: 30, 70: 35},
    "태광": {50: 47, 60: 55, 70: 62},
    "펜타포스(단독)": {50: 65, 60: 80, 70: 92},
    "코르텍, 펜타포스(중문), 윈스터": {50: 46, 60: 54, 70: 62},
    "60W(동명)": {50: 45, 60: 53, 70: 62},
    "90W(동명)": {50: 33, 60: 40, 70: 47},
    "씨넷": {50: 80, 60: 88, 70: 95},
    "현대": {50: 50, 60: 58, 70: 65},
    "H&T": {50: 54, 60: 60, 70: 66},
    "60W(신일)": {50: 38, 60: 44, 70: 50},
    "90W(신일)": {50: 26, 60: 32, 70: 37}
}

PRODUCT_LIST = ["[기종 선택]"] + list(PRODUCT_DB.keys())

# 2) 불량명 및 비가동사유 드롭다운 리스트
DEFECT_OUT_LIST = ["[없음]", "이음", "감소음", "찍힘", "파형"]
DOWNTIME_OUT_LIST = ["[없음]", "셋업", "부품", "품질", "기타"]

# 3) 시간대 설정 (총 10개 행, 엄수)
TIME_SLOTS = [
    {"time": "08:30~09:30", "duration": 60},
    {"time": "09:30~10:30", "duration": 60},
    {"time": "10:40~11:40", "duration": 60},
    {"time": "11:40~12:30", "duration": 50},
    {"time": "13:20~14:30", "duration": 70}, # 70분 추가
    {"time": "14:30~15:30", "duration": 60},
    {"time": "15:40~16:30", "duration": 50},
    {"time": "16:30~17:30", "duration": 60},
    {"time": "18:00~19:00", "duration": 60},
    {"time": "19:00~20:00", "duration": 60},
]

# --- 3. 타이틀 영역 ---
st.title("조립 1라인 실시간 작업일보 (시범운영)")

# --- 4. 기본 정보 및 레이아웃 (최상단) ---
col1, col2 = st.columns(2)
with col1:
    work_date = st.date_input("🗓️ 작업일자", datetime.today())
with col2:
    worker_name = st.text_input("👤 메인 작업자명", placeholder="메인 작업자 이름을 입력하세요")

st.divider()

# --- Session State 초기화 (동적 행 추가용) ---
if 'row_data' not in st.session_state:
    st.session_state.row_data = []
    for i, slot in enumerate(TIME_SLOTS):
        st.session_state.row_data.append({
            "id": i,
            "time": slot["time"],
            "default_duration": slot["duration"],
            "is_added": False
        })
    st.session_state.next_id = len(TIME_SLOTS)

def cb_add_row(idx, time_str, default_dur):
    st.session_state.row_data.insert(idx + 1, {
        "id": st.session_state.next_id,
        "time": time_str,
        "default_duration": default_dur,
        "is_added": True
    })
    st.session_state.next_id += 1

def cb_delete_row(idx):
    st.session_state.row_data.pop(idx)

# --- 5. 작업 실적 입력 그리드 (Table 레이아웃) 헤더 ---
cols_ratio = [1.3, 0.7, 1.8, 0.8, 0.8, 1.0, 0.8, 1.0, 0.8, 1.0, 0.8]
h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11 = st.columns(cols_ratio)
h1.markdown("**시간대**")
h2.markdown("**투입분**")
h3.markdown("**기종명**")
h4.markdown("<div style='text-align:center;'>**목표**</div>", unsafe_allow_html=True)
h5.markdown("**실적**")
h6.markdown("**불량명**")
h7.markdown("**불량**")
h8.markdown("**비가동사유**")
h9.markdown("**비가동분**")
h10.markdown("**지원자**")
h11.markdown("**관리**")

st.markdown("<hr style='margin: 0px; padding: 0px;'/>", unsafe_allow_html=True)

# 실시간 합계 계산용 변수 초기화
total_target = 0
total_actual = 0
total_defect = 0
total_downtime_min = 0

defect_breakdown = {}
downtime_breakdown = {}
model_stats = {}

st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)

# --- 6. 시간대별 데이터 행 생성 ---
for idx, slot in enumerate(st.session_state.row_data):
    row_id = slot['id']
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = st.columns(cols_ratio)
    
    # 1. 시간대 표시 (Read-only)
    if not slot['is_added']:
        c1.markdown(f"<div style='margin-top:8px; font-size:14px;'>{slot['time']}<br/><span style='font-size:0.85em; color:gray;'>({slot['default_duration']}분)</span></div>", unsafe_allow_html=True)
    else:
        c1.markdown(f"<div style='margin-top:8px; font-size:13px; color:#1f77b4;'>↳ (추가 기종)</div>", unsafe_allow_html=True)
        
    # 2. 작업시간(분) 입력
    invested_time = c2.number_input("투입분", min_value=0, value=slot['default_duration'] if not slot['is_added'] else 0, key=f"inv_time_{row_id}", label_visibility="collapsed")
    
    # 3. 기종명 선택 (Select)
    row_product = c3.selectbox("기종선택", options=PRODUCT_LIST, key=f"prod_{row_id}", label_visibility="collapsed")

    # 4. 목표수량 자동 비례 할당
    target_qty = 0
    if row_product != "[기종 선택]":
        if invested_time in [50, 60, 70]:
            target_qty = PRODUCT_DB[row_product].get(invested_time, 0)
        else:
            base_60 = PRODUCT_DB[row_product].get(60, 0)
            target_qty = round((base_60 / 60.0) * invested_time)
            
    c4.markdown(f"<div style='margin-top:8px; font-weight:bold; color:#1f77b4; font-size:16px; text-align:center;'>{target_qty}</div>", unsafe_allow_html=True)
    total_target += target_qty
    
    # 5. 실적수량 (Number)
    actual = c5.number_input("실적", min_value=0, value=0, key=f"actual_{row_id}", label_visibility="collapsed")
    total_actual += actual
    
    # 6. 불량명 (Select)
    defect_name = c6.selectbox("불량명", options=DEFECT_OUT_LIST, key=f"defect_name_{row_id}", label_visibility="collapsed")
    
    # 7. 불량수량 (Number)
    defect_qty = c7.number_input("불량수량", min_value=0, value=0, key=f"defect_qty_{row_id}", label_visibility="collapsed")
    total_defect += defect_qty
    
    if defect_name != "[없음]" and defect_qty > 0:
        defect_breakdown[defect_name] = defect_breakdown.get(defect_name, 0) + defect_qty
    
    # 8. 비가동사유 (Select)
    downtime_reason = c8.selectbox("비가동사유", options=DOWNTIME_OUT_LIST, key=f"down_name_{row_id}", label_visibility="collapsed")
    
    # 9. 비가동 시간 (Number)
    downtime_qty = c9.number_input("비가동시간", min_value=0, value=0, key=f"down_qty_{row_id}", label_visibility="collapsed")
    total_downtime_min += downtime_qty
    
    if downtime_reason != "[없음]" and downtime_qty > 0:
        downtime_breakdown[downtime_reason] = downtime_breakdown.get(downtime_reason, 0) + downtime_qty

    # 10. 지원자 이름 (Text)
    supporter_name = c10.text_input("지원자", placeholder="홍길동", key=f"supporter_{row_id}", label_visibility="collapsed")

    # [WORK UI 2] 기종별 실적 집계용 딕셔너리 연산
    if row_product != "[기종 선택]":
        if row_product not in model_stats:
            model_stats[row_product] = {"target": 0, "actual": 0, "defect": 0}
        model_stats[row_product]["target"] += target_qty
        model_stats[row_product]["actual"] += actual
        model_stats[row_product]["defect"] += defect_qty

    # 11. 관리 버튼 (+ / X)
    if not slot['is_added']:
        c11.button("➕", key=f"add_{row_id}", on_click=cb_add_row, args=(idx, slot['time'], slot['default_duration']))
    else:
        c11.button("❌", key=f"del_{row_id}", on_click=cb_delete_row, args=(idx,))

st.markdown("<hr style='margin: 10px 0px; padding: 0px;'/>", unsafe_allow_html=True)

# --- 7. 하단 집계 영역 (총합계 및 분석 지표) ---
total_time = sum([slot['duration'] for slot in TIME_SLOTS])

# 분모가 0이 되는 에러 극복 (실적=0 이고 불량만 났을 경우 불량률 100% 산출)
total_produced = float(total_actual) + float(total_defect)

achievement_rate = (float(total_actual) / float(total_target) * 100) if float(total_target) > 0 else 0.0
defect_rate = (float(total_defect) / total_produced * 100) if total_produced > 0 else 0.0
downtime_rate = (float(total_downtime_min) / float(total_time) * 100) if float(total_time) > 0 else 0.0

defect_details_str = "<br>".join([f"- {k}: {v}개" for k, v in defect_breakdown.items()]) if defect_breakdown else ""
downtime_details_str = "<br>".join([f"- {k}: {v}분" for k, v in downtime_breakdown.items()]) if downtime_breakdown else ""

s1, s2, s3, s4, s5, s6, s7, s8, s9 = st.columns([1.5, 2.0, 1.0, 1.0, 1.2, 1.0, 1.2, 1.0, 1.5])
s1.markdown("<h3 style='margin-bottom:0px;'>합계(Sum)</h3>", unsafe_allow_html=True)
s2.markdown("")
s3.markdown(f"<h3 style='color:#1f77b4; text-align:center; margin-bottom:0px;'>{total_target}</h3>", unsafe_allow_html=True)
s4.markdown(f"<h3 style='color:#2ca02c; margin-bottom:0px;'>{total_actual}</h3><div style='color:#2ca02c; font-weight:bold; font-size:15px;'>달성율: {achievement_rate:.1f}%</div>", unsafe_allow_html=True)
s5.markdown("")
s6.markdown(f"<h3 style='color:#d62728; margin-bottom:0px;'>{total_defect}</h3><div style='color:#d62728; font-weight:bold; font-size:15px;'>불량율: {defect_rate:.1f}%</div><div style='color:gray; font-size:13px; margin-top:5px; line-height:1.3;'>{defect_details_str}</div>", unsafe_allow_html=True)
s7.markdown("")
s8.markdown(f"<h3 style='color:#ff7f0e; margin-bottom:0px;'>{total_downtime_min}</h3><div style='color:#ff7f0e; font-weight:bold; font-size:15px;'>비가동율: {downtime_rate:.1f}%</div><div style='color:gray; font-size:13px; margin-top:5px; line-height:1.3;'>{downtime_details_str}</div>", unsafe_allow_html=True)
s9.markdown("")

# --- 8. 부가 정보 (WORK UI 2) ---
st.markdown("<br/>", unsafe_allow_html=True)
st.markdown("### 📋 실적 분석 및 부가 정보")
st.markdown("<hr style='margin: 5px 0px;'/>", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([4.0, 3.5, 2.5])

# --- 왼쪽: 실적 분석 ---
with col_left:
    st.markdown("**기종별 실적 분석**")
    l1, l2, l3, l4, l5, l6 = st.columns([2.5, 1.0, 1.0, 1.0, 1.0, 1.5])
    l1.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>기종</b></div>", unsafe_allow_html=True)
    l2.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>목표</b></div>", unsafe_allow_html=True)
    l3.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>양품</b></div>", unsafe_allow_html=True)
    l4.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>불량</b></div>", unsafe_allow_html=True)
    l5.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>불량율</b></div>", unsafe_allow_html=True)
    l6.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>Lot No</b></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 5px 0px;'/>", unsafe_allow_html=True)
    
    if not model_stats:
        st.markdown("<div style='text-align:center; padding:10px; color:gray;'>조회된 기종 실적이 없습니다.</div>", unsafe_allow_html=True)
    else:
        for m_idx, (m_name, m_data) in enumerate(model_stats.items()):
            m_target = m_data["target"]
            m_actual = m_data["actual"]
            m_defect = m_data["defect"]
            m_total = float(m_actual) + float(m_defect)
            m_defect_rate = (float(m_defect) / m_total * 100) if m_total > 0 else 0.0
            
            r1, r2, r3, r4, r5, r6 = st.columns([2.5, 1.0, 1.0, 1.0, 1.0, 1.5])
            r1.markdown(f"<div style='font-size:13px; margin-top:8px;'>{m_name}</div>", unsafe_allow_html=True)
            r2.markdown(f"<div style='margin-top:8px; text-align:center;'>{m_target}</div>", unsafe_allow_html=True)
            r3.markdown(f"<div style='margin-top:8px; text-align:center; color:#2ca02c;'>{m_actual}</div>", unsafe_allow_html=True)
            r4.markdown(f"<div style='margin-top:8px; text-align:center; color:#d62728;'>{m_defect}</div>", unsafe_allow_html=True)
            r5.markdown(f"<div style='margin-top:8px; text-align:center; color:#d62728;'>{m_defect_rate:.1f}%</div>", unsafe_allow_html=True)
            r6.text_input("Lot No", key=f"model_lot_{m_idx}", label_visibility="collapsed")
            st.markdown("<hr style='margin: 5px 0px; border-top: 1px dashed #eee;'/>", unsafe_allow_html=True)

# --- 중간: 투입 부품 ---
with col_mid:
    st.markdown("**투입 부품 (부품별 LOT 및 수량)**")
    m1, m2, m3 = st.columns([1.5, 1.5, 1.0])
    m1.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>부품명</b></div>", unsafe_allow_html=True)
    m2.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>Lot No</b></div>", unsafe_allow_html=True)
    m3.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>수량</b></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 5px 0px;'/>", unsafe_allow_html=True)
    
    for i in range(5):
        mr1, mr2, mr3 = st.columns([1.5, 1.5, 1.0])
        mr1.text_input("부품명", key=f"part_name_{i}", label_visibility="collapsed")
        mr2.text_input("Lot No", key=f"part_lot_{i}", label_visibility="collapsed")
        mr3.number_input("수량", min_value=0, value=0, key=f"part_qty_{i}", label_visibility="collapsed")
        st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)

# --- 오른쪽: 전동 드라이버 ---
with col_right:
    st.markdown("**전동 드라이버 점검**")
    d1, d2 = st.columns([0.8, 2.2])
    d1.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>No</b></div>", unsafe_allow_html=True)
    d2.markdown("<div style='text-align:center; font-size:14px; color:gray;'><b>토크 측정값(kgf·m)</b></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 5px 0px;'/>", unsafe_allow_html=True)
    
    circle_nums = ["①", "②", "③", "④", "⑤"]
    for i in range(1, 6):
        dr1, dr2 = st.columns([0.8, 2.2])
        dr1.markdown(f"<div style='text-align:center; margin-top:8px;'><b>{circle_nums[i-1]}</b></div>", unsafe_allow_html=True)
        dr2.text_input("토크", key=f"torque_val_{i}", label_visibility="collapsed", placeholder="측정값 입력")
        st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
# --- [추가 코드] 9. 구글 시트 통합 전송 로직 ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 화면 하단 중앙에 커다란 전송 버튼 생성
if st.button("🚀 오늘의 작업일보 구글 시트로 최종 전송하기", use_container_width=True):
    data_to_send = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = work_date.strftime("%Y-%m-%d")

    # 세션 스테이트(session_state)에 저장된 각 행의 입력값을 싹쓸이 수집
    for slot in st.session_state.row_data:
        row_id = slot['id']
        time_slot = slot['time']

        # 해당 행의 '기종명' 가져오기
        prod = st.session_state.get(f"prod_{row_id}", "[기종 선택]")

        # 기종이 선택된(작업이 진행된) 행만 데이터로 수집
        if prod != "[기종 선택]":
            inv_time = st.session_state.get(f"inv_time_{row_id}", 0)
            actual = st.session_state.get(f"actual_{row_id}", 0)
            def_name = st.session_state.get(f"defect_name_{row_id}", "[없음]")
            def_qty = st.session_state.get(f"defect_qty_{row_id}", 0)
            down_name = st.session_state.get(f"down_name_{row_id}", "[없음]")
            down_qty = st.session_state.get(f"down_qty_{row_id}", 0)
            supporter = st.session_state.get(f"supporter_{row_id}", "")

            # 목표 UPH 재계산 (UI 표시용과 동일 로직)
            target_qty = 0
            if inv_time in [50, 60, 70]:
                target_qty = PRODUCT_DB[prod].get(inv_time, 0)
            else:
                base_60 = PRODUCT_DB[prod].get(60, 0)
                target_qty = round((base_60 / 60.0) * inv_time)

            # 한 줄(Row)의 데이터를 딕셔너리로 묶기
            data_to_send.append({
                "Timestamp": current_time,
                "Work_Date": date_str,
                "Worker_Name": worker_name,
                "Time_Slot": time_slot,
                "Invested_Min": inv_time,
                "Item_Name": prod,
                "Target_UPH": target_qty,
                "Actual_Qty": actual,
                "Defect_Type": def_name if def_name != "[없음]" else "",
                "Defect_Qty": def_qty,
                "Downtime_Reason": down_name if down_name != "[없음]" else "",
                "Downtime_Min": down_qty,
                "Supporter": supporter
            })

    # 전송할 데이터가 1건이라도 있다면 구글 시트로 발사!
    if len(data_to_send) > 0:
        new_df = pd.DataFrame(data_to_send)
        try:
            existing_df = conn.read(worksheet="Sheet1")
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            st.success(f"🎉 성공! 총 {len(data_to_send)}건의 시간대별 실적이 구글 시트에 기록되었습니다!")
            st.balloons() # 성공 축하 애니메이션
        except Exception as e:
            st.error(f"❌ 전송 오류가 발생했습니다. (Secrets 설정이나 시트 권한을 확인하세요): {e}")
    else:
        st.warning("⚠️ 전송할 데이터가 없습니다. (최소 1개 이상의 기종을 선택해 주세요.)")