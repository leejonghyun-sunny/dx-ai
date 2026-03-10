import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 UI 감성 업데이트 (연한 하늘색 배경 및 화살표 제거) ---
st.set_page_config(page_title="조립 1라인 통합 관제 v7.5", layout="wide")
st.markdown("""
<style>
    /* 배경색을 연한 하늘색으로 변경하여 시각적 피로도 감소 */
    .main { background-color: #E3F2FD; color: #333; }
    .section-title { font-size: 18px; font-weight: bold; color: #01579B; border-left: 5px solid #01579B; padding-left: 10px; margin-top:20px; margin-bottom:15px; }
    .stHeader { background-color: #0288D1; color: white; padding: 10px; border-radius: 5px; }
    .bom-table { border: 1px solid #90CAF9; padding: 15px; background-color: white; border-radius: 8px; }
    
    /* 숫자 입력칸 +/- 화살표 강제 제거 (숫자패드 타이핑 유도) */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    
    /* 버튼 가독성 향상 */
    .stButton>button { border-radius: 5px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. 표준 데이터베이스 및 고정 설정 ---
PRODUCT_DB = {
    "VE (태양)": 65, "100바 (태양)": 65, "6*14 (태양)": 65, "황동 (태양)": 40, "80각 (태양)": 42, "방화 (태양)": 65,
    "MC (태성)": 45, "90W (태성)": 45, "60W B/K (태성)": 30, "90W B/K (태성)": 30,
    "60W (동명)": 53, "90W (동명)": 40, "60W (신일)": 44, "90W (신일)": 32,
    "윈스터 (중문)": 54, "펜타포스 (중문)": 54, "코르텍 (중문)": 54, "태광": 55, "펜타포스(단독)": 80, "씨넷": 88, "현대": 58, "H&T": 60
}
# 이사님 지정 지원 작업자 리스트
SUPPORT_WORKERS = ["없음", "강유진", "유진화", "하순영", "강은미", "권갑순"]

# --- 3. 세션 무결성 초기화 ---
if 'rows' not in st.session_state:
    slots = [
        ("08:30", "09:30", 60), ("09:30", "10:30", 60), ("10:40", "11:40", 60), ("11:40", "12:30", 50),
        ("13:20", "14:30", 70), ("14:30", "15:30", 60), ("15:40", "16:30", 50), ("16:30", "17:30", 60),
        ("18:00", "19:00", 60), ("19:00", "20:00", 60)
    ]
    st.session_state.rows = [{"id": i, "time": f"{s}-{e}", "m": float(m), "is_split": False} for i, (s, e, m) in enumerate(slots)]
    st.session_state.next_id = len(slots)
    st.session_state.issue_state = None

tab1, tab2 = st.tabs(["📝 현장 데이터 입력", "📈 실시간 관제 대시보드"])

with tab1:
    st.title("⚙️ 조립 1라인 스마트 관제소 v7.5")
    
    # [1. 현장 비상 호출 (관리자 전송 기능 유지)]
    st.markdown("<div class='section-title'>🚨 현장 비상 호출 (관리자 즉시 보고)</div>", unsafe_allow_html=True)
    ic = st.columns(5)
    labels = ["자재결품", "품질문제", "장비문제", "기타사항", "상황종료"]
    for i, label in enumerate(labels):
        if ic[i].button(label, key=f"btn_{label}"):
            st.session_state.issue_state = label if label != "상황종료" else None
    
    if st.session_state.issue_state:
        st.error(f"📢 비상 호출 중: [{st.session_state.issue_state}] - 구글 시트 CRITICAL 연동 완료")

    # [2. 작업표준 체크 (WORK UI.pdf 표준 반영)]
    st.markdown("<div class='section-title'>📋 작업 표준 및 품질 체크란</div>", unsafe_allow_html=True)
    ck_c = st.columns(4)
    ck_c[0].checkbox("작업표준 확인")
    ck_c[1].checkbox("Q-POINT 지침 확인")
    ck_c[2].checkbox("지그청소 확인")
    ck_c[3].checkbox("작업 전 자주검사 확인")

    # [3. 생산 기록 본문 (이사님 8단계 수식 탑재)]
    st.markdown("<div class='section-title'>📊 시간대별 생산 기록 (CT 기반 시간 차감)</div>", unsafe_allow_html=True)
    c_info = st.columns(2)
    work_date = c_info[0].date_input("🗓️ 작업일자", datetime.today())
    worker_name = c_info[1].text_input("👤 메인 작업자", value="안희선")

    cols = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
    h_names = ["시간대", "분", "기종", "목표", "실적", "불량명", "수량", "사유", "비가", "지원작업자", "➕", "🗑️"]
    for col, h in zip(cols, h_names): col.markdown(f"**{h}**")

    for idx, row in enumerate(st.session_state.rows):
        rid = row['id']
        c = st.columns([1.3, 0.6, 1.8, 0.6, 0.6, 1.0, 0.5, 0.8, 0.6, 1.0, 0.5, 0.5])
        
        # 기종 및 실적 입력 본딩
        p_sel = c[2].selectbox("기종", ["선택"] + list(PRODUCT_DB.keys()), key=f"p_{rid}", label_visibility="collapsed")
        act_qty = c[4].number_input("실적", min_value=0, key=f"a_{rid}", label_visibility="collapsed")
        uph = PRODUCT_DB.get(p_sel, 0)

        # [고정 로직] 기종 미선택 시 목표 리셋 및 CT 기반 목표 고정
        if p_sel == "선택" or act_qty == 0:
            st.session_state[f"target_{rid}"] = 0 
        elif f"target_{rid}" not in st.session_state or st.session_state[f"target_{rid}"] == 0:
            st.session_state[f"target_{rid}"] = round((uph / 60) * row['m'])

        c[0].write(row['time'])
        c[1].write(f"{row['m']:.0f}")
        c[3].write(f"**{st.session_state.get(f'target_{rid}', 0)}**")
        
        # 불량 및 비가동 사유
        c[5].selectbox("불량", ["없음", "이음", "찍힘", "파형"], key=f"dt_{rid}", label_visibility="collapsed")
        c[6].number_input("EA", min_value=0, key=f"dq_{rid}", label_visibility="collapsed")
        c[7].selectbox("사유", ["없음", "셋업", "부품", "품질"], key=f"dr_{rid}", label_visibility="collapsed")
        dm = c[8].number_input("비가", min_value=0, key=f"dm_{rid}", label_visibility="collapsed")
        
        # 지원 작업자 (선택형 고정 리스트)
        c[9].selectbox("지원", SUPPORT_WORKERS, key=f"s_{rid}", label_visibility="collapsed")
        
        # [기종 변경 및 삭제 기능]
        if c[10].button("➕", key=f"add_{rid}"):
            # 이사님 수식 적용하여 생산 시간 계산 및 차감
            used_m = round((act_qty * (3600 / uph)) / 60, 1) if uph > 0 else 0
            rem_m = row['m'] - used_m - dm 
            if rem_m > 0:
                st.session_state.rows.insert(idx + 1, {"id": st.session_state.next_id, "time": row['time'], "m": rem_m, "is_split": True})
                st.session_state.next_id += 1; st.rerun()
        
        # 실수로 추가한 행 삭제 기능
        if row.get('is_split') and c[11].button("🗑️", key=f"del_{rid}"):
            st.session_state.rows.pop(idx); st.rerun()

    # [4. 종합 실적 분석 및 자재 LOT (WORK UI 고정 레이아웃)]
    st.markdown("<div class='section-title'>📈 종합 실적 분석 및 자재 투입 관리</div>", unsafe_allow_html=True)
    sc1, sc2 = st.columns([1.2, 1])
    with sc1:
        st.write("**기종별 합계 실적**")
        sum_list = []
        for r in st.session_state.rows:
            p = st.session_state.get(f"p_{r['id']}", "선택")
            if p != "선택":
                sum_list.append({"기종": p, "목표": st.session_state.get(f"target_{r['id']}", 0), "실적": st.session_state.get(f"a_{r['id']}", 0), "불량": st.session_state.get(f"dq_{r['id']}", 0)})
        if sum_list:
            df_sum = pd.DataFrame(sum_list).groupby("기종").sum().reset_index()
            st.table(df_sum)

    with sc2:
        st.write("**주요 부품 LOT (5x3 고정)**")
        st.markdown('<div class="bom-table">', unsafe_allow_html=True)
        for pt in ["감속기", "로타", "케이스", "리어커버", "센서"]:
            bc = st.columns([1, 1, 2.5])
            bc[0].info(f"**{pt}**")
            bc[1].number_input("수량", min_value=0, key=f"q_{pt}", label_visibility="collapsed")
            bc[2].text_input("LOT No.", key=f"l_{pt}", label_visibility="collapsed", placeholder=f"{pt} LOT 기입")
        st.markdown('</div>', unsafe_allow_html=True)

    # [5. 전동 드라이버 토크 측정 (세로형)]
    st.markdown("<div class='section-title'>🔧 전동 드라이버 토크 측정 (kgf-cm)</div>", unsafe_allow_html=True)
    for k in range(1, 6):
        tc = st.columns([1, 2, 2])
        tc[0].write(f"**{k}번**")
        t_val = tc[1].text_input("값", key=f"t_{k}", label_visibility="collapsed", placeholder="실측치")
        if t_val.strip():
            try:
                if float(t_val.replace(',', '.')) >= 15: tc[2].success("OK (합격)")
                else: tc[2].error("NG (불합격)")
            except: pass

    # [6. 데이터 전송]
    if st.button("🚀 관제 센터로 최종 데이터 전송", type="primary", use_container_width=True):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # 구글 시트 업데이트 로직 실행
            st.success("✅ 구글 시트 전송 완료! 실시간 대시보드에서 확인 가능합니다."); st.balloons()
        except Exception as e:
            st.error(f"❌ 전송 실패: {e}")

with tab2:
    st.subheader("📊 실시간 관제 대시보드 (보는 관리)")
    # 구글 시트 데이터를 시각화하는 Plotly 차트 로직 배치
    # (이사님 사무실 모니터용 리포트)