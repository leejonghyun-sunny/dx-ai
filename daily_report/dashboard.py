import streamlit as st
import pandas as pd
import json
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================================
# HSG 스마트 작업일보 실시간 현황판 (Dashboard)
# 10초 주기 자동 폴링(Polling) 방식 적용
# ==========================================================

st.set_page_config(
    page_title="HSG 실시간 생산 현황판",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 고급스러운 대시보드 UI를 위한 CSS (글래스모피즘, 네온 효과, 다크 테마)
st.markdown("""
<style>
    /* 메인 배경 및 폰트 설정 */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #e2e8f0;
        font-family: 'Inter', 'Noto Sans KR', sans-serif;
    }
    
    /* 화면 꽉 차게 패딩 조절 */
    .main .block-container { padding: 2rem 3rem !important; }
    
    /* 제목 스타일 */
    .dash-title {
        font-size: 2.5rem;
        font-weight: 900;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
    }
    
    /* 글래스모피즘 카드 스타일 */
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-bottom: 1.5rem;
        transition: transform 0.3s ease;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(56, 189, 248, 0.4);
        box-shadow: 0 12px 40px 0 rgba(56, 189, 248, 0.2);
    }
    
    /* KPI 수치 강조 스타일 */
    .kpi-value { font-size: 3rem; font-weight: 800; margin: 0; line-height: 1.2; }
    .kpi-label { font-size: 1.1rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;}
    
    /* 색상 유틸리티 */
    .text-blue { color: #38bdf8; }
    .text-green { color: #34d399; }
    .text-red { color: #f87171; }
    .text-yellow { color: #fbbf24; }
    
    /* 비상 알람 애니메이션 */
    .emergency-banner {
        background: linear-gradient(90deg, #991b1b 0%, #dc2626 50%, #991b1b 100%);
        color: white;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 2rem;
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.8);
        animation: pulse-red 1.5s infinite;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 20px rgba(220, 38, 38, 0.5); }
        50% { box-shadow: 0 0 40px rgba(220, 38, 38, 0.9); }
        100% { box-shadow: 0 0 20px rgba(220, 38, 38, 0.5); }
    }
    
    /* 최종 업데이트 시간 */
    .update-time { text-align: right; color: #64748b; font-size: 0.9rem; margin-top: -1rem; margin-bottom: 2rem;}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 상수 (app.py와 동일하게 유지)
# ==========================================================
PRODUCT_DB = {
    "VE (태양)":65, "100바 (태양)":65, "6*14 (태양)":65,
    "황동 (태양)":40, "80각 (태양)":42, "방화 (태양)":65,
    "MC (태성)":45, "90W (태성)":45,
    "60W B/K (태성)":30, "90W B/K (태성)":30,
    "60W (동명)":53, "90W (동명)":40,
    "60W (신일)":44, "90W (신일)":32,
    "윈스터 (중문)":54, "펜타포스 (중문)":54, "코르텍 (중문)":54,
    "태광":55, "펜타포스(단독)":80, "씨넷":88, "현대":58, "H&T":60
}

AUTOSAVE_SHEET = "임시저장"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1wQQiJ2j2Bl7tOkdt9-_IKXsNDtdvUqlXqtgcrWWj6Rs/edit?usp=sharing"

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_latest_data():
    """임시저장 시트에서 최신 1행 데이터를 가져옵니다."""
    try:
        # ttl=0 으로 항상 최신 데이터를 폴링합니다.
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=AUTOSAVE_SHEET, ttl=0)
        if df.empty:
            return None
        return df.iloc[-1].to_dict()
    except Exception as e:
        return {"error": str(e)}

# ==========================================================
# @st.fragment: 페이지 전체 새로고침 없이 이 함수 부분만 지정된 주기(10초)로 실행됩니다.
# (Streamlit 최신 기능으로 부드러운 실시간 대시보드 구현에 핵심적인 역할)
# ==========================================================
@st.fragment(run_every="10s")
def render_dashboard():
    data = get_latest_data()
    
    if not data:
        st.warning("데이터가 없습니다. app.py에서 데이터를 한 번 이상 임시저장해 주세요.")
        return
        
    if "error" in data:
        st.error(f"구글 시트 데이터를 불러오는 중 오류 발생: {data['error']}")
        return

    # 업데이트 시간 표시
    saved_at = data.get("saved_at", "알 수 없음")
    st.markdown(f"<div class='update-time'>🕒 마지막 동기화: {saved_at} (10초 주기 자동 갱신)</div>", unsafe_allow_html=True)
    
    # 비상 알람 렌더링
    issue_state = str(data.get("issue_state", ""))
    if issue_state and issue_state.lower() not in ("none", "nan", ""):
        st.markdown(
            f"<div class='emergency-banner'>🚨 현장 긴급 호출 발생: [{issue_state}] 🚨</div>", 
            unsafe_allow_html=True
        )

    # 데이터 파싱 및 통계 계산
    rows_json_str = str(data.get("rows_json", "[]"))
    rows = []
    if rows_json_str and rows_json_str.lower() != "nan":
        try:
            rows = json.loads(rows_json_str)
        except json.JSONDecodeError:
            pass

    total_target = 0
    total_actual = 0
    total_defect = 0
    model_stats = {}

    for r in rows:
        p = r.get("product", "선택")
        if p == "선택":
            continue
            
        m = float(r.get("m", 0))
        uph = PRODUCT_DB.get(p, 0)
        target = round((uph / 60) * m) if uph > 0 else 0
        actual = int(r.get("actual", 0))
        defect = int(r.get("def_qty", 0))
        
        total_target += target
        total_actual += actual
        total_defect += defect
        
        if p not in model_stats:
            model_stats[p] = {"target": 0, "actual": 0, "defect": 0}
        model_stats[p]["target"] += target
        model_stats[p]["actual"] += actual
        model_stats[p]["defect"] += defect

    # 달성률 및 불량률 계산
    achieve_rate = round((total_actual / total_target * 100), 1) if total_target > 0 else 0
    defect_rate = round((total_defect / total_actual * 100), 1) if total_actual > 0 else 0

    # ==========================================================
    # 메인 KPI 섹션
    # ==========================================================
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">목표 수량</div>
            <div class="kpi-value text-blue">{total_target:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">생산 실적</div>
            <div class="kpi-value text-green">{total_actual:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        # 달성률 색상 로직 (90% 이상 녹색, 70% 이상 노란색, 미만 빨간색)
        achieve_color = "text-green" if achieve_rate >= 90 else ("text-yellow" if achieve_rate >= 70 else "text-red")
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">종합 달성률</div>
            <div class="kpi-value {achieve_color}">{achieve_rate}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c4:
        # 불량률 색상 로직 (3% 이상 빨간색)
        defect_color = "text-red" if defect_rate >= 3 else "text-green"
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">종합 불량률</div>
            <div class="kpi-value {defect_color}">{defect_rate}%</div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================================
    # 상세 현황 테이블 및 차트 섹션
    # ==========================================================
    st.markdown("<h3 style='margin-top: 1rem; margin-bottom: 1rem;'>📊 기종별 생산 현황</h3>", unsafe_allow_html=True)
    
    if model_stats:
        # 표 형식으로 정리
        df_stats = pd.DataFrame.from_dict(model_stats, orient='index').reset_index()
        df_stats.columns = ["기종", "목표", "실적", "불량"]
        df_stats["달성률(%)"] = (df_stats["실적"] / df_stats["목표"] * 100).fillna(0).round(1)
        df_stats["불량률(%)"] = (df_stats["불량"] / df_stats["실적"] * 100).fillna(0).round(1)
        
        # 글래스모피즘 카드 안에 표 삽입
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.dataframe(
            df_stats.style.background_gradient(cmap="Blues", subset=["실적"])
                          .background_gradient(cmap="Reds", subset=["불량"])
                          .format({"달성률(%)": "{:.1f}%", "불량률(%)": "{:.1f}%"}),
            use_container_width=True,
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("현재 작업 중인 기종 데이터가 없습니다.")

# 타이틀 렌더링
st.markdown("<div class='dash-title'>⚡ 스마트 조립1라인 실시간 현황판</div>", unsafe_allow_html=True)

# 프래그먼트 호출 (자동 갱신 루프 시작)
render_dashboard()
