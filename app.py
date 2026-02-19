import streamlit as st
import pandas as pd
import os
import datetime

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

# ... (기존 코드 유지) ...

LOG_FILE = "inspection_logs.csv"

# ==========================================
# [데이터 저장 함수] (수정됨: 품질 데이터 추가)
# ==========================================
def save_log(date, user, freq, rpm, tension, cut_sec, depth, bite, roundness, step, result):
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Date", "User", "Freq", "RPM", "Tension", "Cut_Sec", "Depth", "Bite", "Roundness", "Step", "Result", "Timestamp"])
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
        "Roundness": [roundness],
        "Step": [step],
        "Result": [result],
        "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    })
    new_data.to_csv(LOG_FILE, mode='a', header=False, index=False)

# ... (UI 설정 및 스타일 유지) ...

# ... (사이드바 유지) ...

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
        
        # 품질 측정값 입력 (함께 저장하기 위해 폼 안으로 이동 고려, 현재는 별도 입력이므로 form 외부 변수 사용 불가. 
        # 사용성을 위해 트러블슈팅 값을 여기서 입력받지 않음. 
        # 대신, '감사 실행' 시 품질값은 0.0으로 초기화 저장하거나, 별도 품질 저장 버튼을 두는 것이 좋으나
        # 요청사항 1번(품질측정 데이터 이력관리)을 위해 폼 내부에 품질 입력칸을 추가하는 것이 가장 확실함.
        # 하지만 UX상 분리된 게 나을 수 있어, 여기서는 '설정값 점검' 저장 시 품질값은 0(미측정)으로 저장하고,
        # 아래 품질 측정 섹션에서 별도 저장 버튼을 두거나, 통합 저장 버튼을 만드는 것이 좋음.
        # --> **통합 저장 방식**으로 변경: 품질 측정 섹션을 위로 올리거나, Session State를 써야 함.
        # --> 가장 쉬운 방법: 품질 입력란도 form 에 포함시키지 않고, 맨 아래 '전체 데이터 저장' 버튼을 두거나
        #     기존대로 하되, 품질값 입력을 폼 밖에서 받고, submit 버튼 눌렀을 때 해당 변수(meas_roundness)를 참조 가능한지 확인.
        #     Streamlit form submit 시 form 외부 widget 값은 최신값 참조 가능함.
        
        submitted = st.form_submit_button("🛡️ 설정값 감사 및 저장")

    # ==========================================
    # [섹션 2: 품질 측정 (Form 외부)]
    # ==========================================
    st.markdown("---")
    st.header("2. 품질 측정 데이터 (선택)")
    col3, col4 = st.columns(2)
    with col3:
        meas_roundness = st.number_input("측정 진원도 (µm)", value=0.0, step=0.1)
    with col4:
        meas_step = st.number_input("측정 단차 (µm)", value=0.0, step=0.1)

    # 트러블슈팅 가이드 표시 로직 (실시간 반응을 위해 form 밖 유지)
    if meas_roundness > 0 or meas_step > 0:
        is_roundness_fail = meas_roundness > LIMIT_ROUNDNESS
        is_step_fail = meas_step > LIMIT_STEP
        if is_roundness_fail or is_step_fail:
            st.error(f"🚨 비상: 품질 기준 초과 발생! (진원도 한계: {LIMIT_ROUNDNESS}µm, 단차 한계: {LIMIT_STEP}µm)")
            with st.expander("🛠️ 긴급 조치 가이드", expanded=True):
                st.markdown("""
                **분석된 표준화 솔루션:**
                1. **바이트 위치**: '중하 (Middle-Lower)' 확인
                2. **텐션**: 2.72 Kg 재설정
                3. **속도**: 2.5 단계 (16초) 확인
                """)

    if submitted:
        if not input_user:
            st.warning("⚠️ 사이드바에서 '점검자 성명'을 먼저 입력해주세요.")
        else:
            errors = []
            # ... (기존 점검 로직) ...
            if input_freq != STD_FREQ: errors.append(f"❌ [주파수 불량] {STD_FREQ}Hz / {input_freq}Hz")
            if input_rpm != STD_RPM: errors.append(f"❌ [RPM 불량] {STD_RPM}RPM / {input_rpm}RPM")
            if input_depth != STD_DEPTH_2ND: errors.append(f"❌ [가공 깊이] {STD_DEPTH_2ND}mm / {input_depth}mm")
            if input_tension != STD_TENSION: errors.append(f"❌ [텐션] {STD_TENSION}Kg / {input_tension}Kg")
            if input_cut_sec != STD_CUT_SEC: errors.append(f"❌ [절삭 속도] {STD_CUT_SEC}초 / {input_cut_sec}초")
            if bite_check != "중하 (Middle-Lower)": errors.append(f"⚠️ [바이트 위치] 권장: 중하 / 현재: {bite_check}")

            # 품질 데이터 판정
            q_result = "PASS"
            if meas_roundness > LIMIT_ROUNDNESS or meas_step > LIMIT_STEP:
                q_result = "FAIL (Quality)"
                errors.append(f"❌ [품질 불량] 진원도/단차 기준 초과")
            elif errors:
                q_result = "FAIL (Setting)"

            if not errors:
                st.balloons()
                st.success(f"✅ 설정값 및 품질 데이터가 완벽합니다! ({input_user}님)")
                save_log(input_date, input_user, input_freq, input_rpm, input_tension, input_cut_sec, input_depth, bite_check, meas_roundness, meas_step, "PASS")
            else:
                st.error("🚨 부적합 항목이 발견되었습니다.")
                for err in errors:
                    st.write(err)
                save_log(input_date, input_user, input_freq, input_rpm, input_tension, input_cut_sec, input_depth, bite_check, meas_roundness, meas_step, q_result)


with tab2:
    st.header("📊 점검 이력 조회 (History)")
    
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        
        # 날짜 필터링
        col_date, col_btn = st.columns([2, 1])
        with col_date:
            search_date = st.date_input("조회할 날짜 선택", datetime.date.today(), key="history_date")
        
        filtered_df = df[df['Date'] == str(search_date)]
        
        if not filtered_df.empty:
            st.success(f"{search_date} 기록: 총 {len(filtered_df)}건")
            st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False))
            
            # 엑셀 다운로드 버튼
            # Excel 변환을 위해 io.BytesIO 사용
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Sheet1')
                
            with col_btn:
                st.download_button(
                    label="📥 엑셀(Excel)로 다운로드",
                    data=buffer,
                    file_name=f"inspection_log_{search_date}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            
            # 통계 표시
            pass_count = len(filtered_df[filtered_df['Result'] == 'PASS'])
            st.metric("합격률 (Pass Rate)", f"{pass_count}/{len(filtered_df)} ({pass_count/len(filtered_df)*100:.1f}%)")
        else:
            st.info(f"{search_date}에 대한 점검 기록이 없습니다.")
    else:
        st.warning("아직 저장된 점검 이력이 없습니다.")
