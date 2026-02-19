import streamlit as st

# ==========================================
# [표준 데이터 베이스: 타협 불가 기준값]
# 출처: DC V5 정류자 가공 공정 표준 지침서
# ==========================================
STD_FREQ = 30.0          # Hz
STD_RPM = 1860           # RPM
STD_CUT_SEC = 16.0       # Sec
STD_CUT_DIAL = 2.5       # Dial Step
STD_DEPTH_2ND = 0.03     # mm
STD_TENSION = 2.72       # Kg (Ø41.5 기준)
LIMIT_ROUNDNESS = 3.0    # µm (진원도 한계)
LIMIT_STEP = 2.0         # µm (단차 한계)

# ==========================================
# [UI 및 스타일 설정]
# ==========================================
st.set_page_config(page_title="DC V5 AI 감사관", page_icon="🛡️", layout="centered")

st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .success { color: green; font-weight: bold; }
    .fail { color: red; font-weight: bold; }
    
    /* [User Request] 숫자 입력창의 +/- 버튼 숨기기 (직관적 숫자패드 사용 유도) */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }
    
    /* 웹킷 브라우저 기본 스핀 버튼 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ DC V5 공정 AI 감사관")
st.caption("안티그래비티 생산 현장 지원 시스템")
st.markdown("---")

# ==========================================
# [섹션 1: 가공 조건 세팅 점검]
# ==========================================
st.header("1. 설비 세팅값 검증 (Strict Monitoring)")
st.info("💡 작업 시작 전, 현재 기계의 세팅값을 입력하세요.")

with st.form("setting_check_form"):
    col1, col2 = st.columns(2)
    with col1:
        input_freq = st.number_input("인버터 주파수 (Hz)", value=0.0, step=0.1, format="%.1f")
        input_rpm = st.number_input("실측 RPM", value=0, step=10)
        input_tension = st.number_input("밸트 텐션 (Kg)", value=0.00, step=0.01, format="%.2f")
    with col2:
        input_cut_sec = st.number_input("절삭 속도 (Sec)", value=0.0, step=0.5)
        input_depth = st.number_input("2차 가공 깊이 (mm)", value=0.00, step=0.01, format="%.2f")
    
    # 바이트 위치 확인 (체크박스)
    st.markdown("**바이트 위치 확인**")
    bite_check = st.radio("현재 바이트 사용 구간은?", ["상 (Upper)", "중 (Middle)", "중하 (Middle-Lower)", "하 (Lower)"], index=1)
    
    submitted = st.form_submit_button("🛡️ 설정값 감사 실행")

if submitted:
    errors = []
    
    # 1. 주파수 점검
    if input_freq != STD_FREQ:
        errors.append(f"❌ [주파수 불량] 표준: {STD_FREQ}Hz / 현재: {input_freq}Hz (편차: {input_freq - STD_FREQ:.1f})")
    
    # 2. RPM 점검
    if input_rpm != STD_RPM:
        errors.append(f"❌ [RPM 불량] 표준: {STD_RPM}RPM / 현재: {input_rpm}RPM")
        
    # 3. 2차 가공 깊이 점검
    if input_depth != STD_DEPTH_2ND:
        errors.append(f"❌ [가공 깊이 위반] 표준: {STD_DEPTH_2ND}mm / 현재: {input_depth}mm (정밀도 요망)")
        
    # 4. 텐션 점검
    if input_tension != STD_TENSION:
        errors.append(f"❌ [텐션 부적합] 표준: {STD_TENSION}Kg / 현재: {input_tension}Kg (Ø41.5 기준 필수)")

    # 5. 절삭 속도 점검
    if input_cut_sec != STD_CUT_SEC:
        errors.append(f"❌ [절삭 속도 불량] 표준: {STD_CUT_SEC}초(2.5단) / 현재: {input_cut_sec}초")

    # 6. 바이트 위치 점검
    if bite_check != "중하 (Middle-Lower)":
        errors.append(f"⚠️ [바이트 위치 경고] 권장: 중하(Middle-Lower) / 현재: {bite_check}")

    # 결과 출력
    if not errors:
        st.balloons()
        st.success("✅ 완벽합니다! 모든 설정값이 표준과 일치합니다. 작업을 시작하십시오.")
    else:
        st.error("🚨 품질은 타협 대상이 아닙니다. 다음 항목을 즉시 수정하십시오!")
        for err in errors:
            st.write(err)

st.markdown("---")

# ==========================================
# [섹션 2: 트러블 슈팅 (품질 이상 대응)]
# ==========================================
st.header("2. 품질 측정 및 트러블슈팅")
st.warning("⚠️ 진원도나 단차 이상 발생 시 입력하십시오.")

col3, col4 = st.columns(2)
with col3:
    meas_roundness = st.number_input("측정 진원도 (µm)", value=0.0, step=0.1)
with col4:
    meas_step = st.number_input("측정 단차 (µm)", value=0.0, step=0.1)

if meas_roundness > 0 or meas_step > 0:
    # 기준치 초과 여부 확인
    is_roundness_fail = meas_roundness > LIMIT_ROUNDNESS
    is_step_fail = meas_step > LIMIT_STEP
    
    if is_roundness_fail or is_step_fail:
        st.error(f"🚨 비상: 품질 기준 초과 발생! (진원도 한계: {LIMIT_ROUNDNESS}µm, 단차 한계: {LIMIT_STEP}µm)")
        
        with st.expander("🛠️ 긴급 조치 가이드 (클릭하여 확인)", expanded=True):
            st.markdown("""
            **분석된 표준화 솔루션에 따라 다음 순서대로 조치하십시오:**
            
            1. **바이트 마모 및 위치 점검**
               - 현재 바이트가 **'중하 (Middle-Lower)'** 구간에 닿아 있는지 눈으로 확인하십시오.
               - 상단이나 중앙 사용 시 진원도 불량의 주원인이 됩니다.
            
            2. **밸트 텐션 재설정**
               - 텐션계로 측정 시 정확히 **2.72 Kg**이 나오는지 확인하십시오.
               - 기존 2.0 Kg, 2.5 Kg 세팅은 최적 조건이 아닙니다.
               
            3. **절삭 속도 다이얼 확인**
               - 속도 다이얼이 정확히 **2.5 단계 (16초)**에 위치해 있는지 확인하십시오.
            """)
    else:
        st.success("✅ 측정값이 정상 범위 내에 있습니다.")

# ==========================================
# [사이드바: 일일 점검표]
# ==========================================
with st.sidebar:
    st.header("📋 일일 점검 체크리스트")
    st.markdown("매일 아침 작업 전 확인")
    
    st.checkbox("벨트 속도: 1860 RPM (30Hz)")
    st.checkbox("절삭 속도: 16 Sec (2.5단)")
    st.checkbox("가공 깊이: 0.03 mm (2차)")
    st.checkbox("밸트 텐션: 2.72 Kg")
    st.checkbox("바이트 위치: 중하 (Middle-Lower)")
    
    st.markdown("---")
    st.caption("Based on Hyoseong Geared Motor Standards")
