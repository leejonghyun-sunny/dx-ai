import pandas as pd
import os
import datetime

# ... (기존 상수 정의 유지) ...

# ==========================================
# [데이터 저장 함수]
# ==========================================
LOG_FILE = "inspection_logs.csv"

def save_log(date, user, freq, rpm, tension, cut_sec, depth, bite, result):
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Date", "User", "Freq", "RPM", "Tension", "Cut_Sec", "Depth", "Bite", "Result", "Timestamp"])
        df.to_csv(LOG_FILE, index=False)
    
    new_data = pd.DataFrame({
        "Date": [date],
        "User": [user],
        "Freq": [freq],
        "RPM": [rpm],
        "Tension": [tension],
        "Cut_Sec": [cut_sec],
        "Depth": [depth],
        "Bite": [bite],
        "Result": [result],
        "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    })
    new_data.to_csv(LOG_FILE, mode='a', header=False, index=False)

# ... (UI 설정 및 스타일 유지) ...

# ==========================================
# [사이드바: 사용자 정보 및 일일 점검표]
# ==========================================
with st.sidebar:
    st.header("👤 점검자 정보")
    input_user = st.text_input("점검자 성명", placeholder="이름을 입력하세요")
    input_date = st.date_input("점검 일자", datetime.date.today())
    
    st.markdown("---")
    st.header("📋 일일 점검 체크리스트")
    st.markdown("매일 아침 작업 전 확인")
    
    st.checkbox("벨트 속도: 1860 RPM (30Hz)")
    st.checkbox("절삭 속도: 16 Sec (2.5단)")
    st.checkbox("가공 깊이: 0.03 mm (2차)")
    st.checkbox("밸트 텐션: 2.72 Kg")
    st.checkbox("바이트 위치: 중하 (Middle-Lower)")
    
    st.markdown("---")
    st.caption("Based on Hyoseong Geared Motor Standards")

# ==========================================
# [탭 구성: 점검 수행 vs 이력 조회]
# ==========================================
tab1, tab2 = st.tabs(["🛡️ 설정값 점검 (Audit)", "📊 점검 이력 조회 (History)"])

with tab1:
    # ==========================================
    # [섹션 1: 가공 조건 세팅 점검]
    # ==========================================
    st.header("1. 설비 세팅값 검증 (Strict Monitoring)")
    st.info(f"💡 {input_date.strftime('%Y-%m-%d')} / 점검자: {input_user if input_user else '미지정'}")

    # ... (기존 입력 폼 유지) ...
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
        if not input_user:
            st.warning("⚠️ 사이드바에서 '점검자 성명'을 먼저 입력해주세요.")
        else:
            errors = []
            
            # ... (기존 점검 로직 유지) ...
            
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

            # 결과 출력 및 저장
            if not errors:
                st.balloons()
                st.success(f"✅ 완벽합니다! ({input_user}님 확인됨)")
                save_log(input_date, input_user, input_freq, input_rpm, input_tension, input_cut_sec, input_depth, bite_check, "PASS")
            else:
                st.error("🚨 품질은 타협 대상이 아닙니다. 다음 항목을 즉시 수정하십시오!")
                for err in errors:
                    st.write(err)
                save_log(input_date, input_user, input_freq, input_rpm, input_tension, input_cut_sec, input_depth, bite_check, "FAIL")

    st.markdown("---")

    # ==========================================
    # [섹션 2: 트러블 슈팅 (품질 이상 대응)]
    # ==========================================
    # ... (기존 트러블슈팅 로직 유지) ...
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

with tab2:
    st.header("📊 점검 이력 조회 (History)")
    
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        
        # 날짜 필터링
        search_date = st.date_input("조회할 날짜 선택", datetime.date.today(), key="history_date")
        filtered_df = df[df['Date'] == str(search_date)]
        
        if not filtered_df.empty:
            st.success(f"{search_date} 기록: 총 {len(filtered_df)}건 발견")
            st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False))
            
            # 통계 표시
            pass_count = len(filtered_df[filtered_df['Result'] == 'PASS'])
            fail_count = len(filtered_df[filtered_df['Result'] == 'FAIL'])
            st.metric("합격률 (Pass Rate)", f"{pass_count}/{len(filtered_df)} ({pass_count/len(filtered_df)*100:.1f}%)")
        else:
            st.info(f"{search_date}에 대한 점검 기록이 없습니다.")
    else:
        st.warning("아직 저장된 점검 이력이 없습니다.")
