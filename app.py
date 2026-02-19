import streamlit as st
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ==========================================
# [표준 데이터 베이스: 타협 불가 기준값 (Range)]
# 출처: DC V5 정류자 가공 공정 표준 지침서 (2026.02.19 개정)
# ==========================================
MIN_FREQ, MAX_FREQ = 28.0, 32.0          # Hz
MIN_RPM, MAX_RPM = 1750, 1900            # RPM
MIN_CUT_SEC, MAX_CUT_SEC = 15.0, 17.0    # Sec
MIN_DEPTH_2ND, MAX_DEPTH_2ND = 0.02, 0.04 # mm
MIN_TENSION, MAX_TENSION = 2.5, 2.8      # Kg
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
# [사이드바: 사용자 정보 및 일일 점검표]
# ==========================================
with st.sidebar:
    st.header("👤 점검자 정보")
    input_user = st.text_input("점검자 성명", placeholder="이름을 입력하세요")
    input_date = st.date_input("점검 일자", datetime.date.today())
    
    st.markdown("---")
    st.header("📋 일일 점검 체크리스트")
    st.markdown("매일 아침 작업 전 확인")
    
    st.checkbox(f"주파수: {MIN_FREQ}~{MAX_FREQ} Hz")
    st.checkbox(f"RPM: {MIN_RPM}~{MAX_RPM} RPM")
    st.checkbox(f"절삭 속도: {MIN_CUT_SEC}~{MAX_CUT_SEC} Sec")
    st.checkbox(f"가공 깊이: {MIN_DEPTH_2ND}~{MAX_DEPTH_2ND} mm")
    st.checkbox(f"밸트 텐션: {MIN_TENSION}~{MAX_TENSION} Kg")
    st.checkbox("바이트 위치: 중하 (Middle-Lower)")
    
    st.markdown("---")
    st.caption("Based on Hyoseong Geared Motor Standards")
# ==========================================
# [관리자 모드 (Admin Mode 로그인)]
# ==========================================
with st.sidebar:
    st.markdown("---")
    with st.expander("🔒 관리자 모드 (Admin)"):
        admin_password = st.text_input("비밀번호", type="password")
        if admin_password == "1234":
            st.session_state['is_admin'] = True
            st.success("관리자 인증 성공")
        else:
            st.session_state['is_admin'] = False

# 관리자 권한 상태 변수 설정 (Global Scope)
is_admin = st.session_state.get('is_admin', False)

# ==========================================
# [탭 구성: 점검 수행 vs 이력 조회]
# ==========================================
if is_admin:
    tab1, tab2, tab3 = st.tabs(["🛡️ 설정값 점검 (Audit)", "📊 점검 이력 조회 (User)", "📈 관리자 대시보드 (Manager)"])
else:
    tab1, tab2 = st.tabs(["🛡️ 설정값 점검 (Audit)", "📊 점검 이력 조회 (History)"])

# ... (Tab 1: 설정값 점검 - 기존 코드와 동일) ...
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
        
        # 바이트 위치 확인 (체크박스 & 가이드 그림)
        st.markdown("**바이트 위치 확인**")
        
        # 가이드 그림 생성을 위한 함수
        def draw_byte_guide():
            fig, ax = plt.subplots(figsize=(4, 3))
            
            # 1. 바이트 (Byte) - 검은색 형상 (좌측)
            # (x, y, width, height)
            byte_rect = patches.Rectangle((0.1, 0.2), 0.4, 0.6, color='#333333', label='Byte')
            ax.add_patch(byte_rect)
            
            # 2. 정류자 (Commutator) - 회색 곡면 (우측)
            # 바이트와 접촉하는 부분 표현
            comm_arc = patches.Arc((0.8, 0.5), 0.6, 1.0, theta1=90, theta2=270, color='#95a5a6', linewidth=3)
            ax.add_patch(comm_arc)
            # 채워진 느낌을 위해 Polygon 사용 가능하지만 Arc로 단순화
            
            # 3. 위치 표시 (상/중/하) - 바이트 우측면 기준
            # Byte Right Edge X = 0.5
            # Top Y = 0.8 / Bottom Y = 0.2
            # Height = 0.6
            
            # 화살표 및 텍스트 스타일
            arrow_props = dict(facecolor='red', edgecolor='red', arrowstyle='->', linewidth=1.5)
            text_offset_x = 0.55
            
            # 상 (Upper) - Y=0.75 (상단 부근)
            ax.annotate('상 (Upper)', xy=(0.5, 0.75), xytext=(0.65, 0.75), arrowprops=arrow_props, fontsize=8, va='center')
            
            # 중 (Middle) - Y=0.5 (중앙)
            ax.annotate('중 (Middle)', xy=(0.5, 0.5), xytext=(0.65, 0.5), arrowprops=arrow_props, fontsize=8, va='center')
            
            # 하 (Lower) - Y=0.25 (하단 부근)
            ax.annotate('하 (Lower)', xy=(0.5, 0.25), xytext=(0.65, 0.25), arrowprops=arrow_props, fontsize=8, va='center')
            
            # 4. 타겟 포인트 (중하) - 파란색 점 + 강조
            # 중(0.5)과 하(0.25) 사이 -> 약 0.375
            target_y = 0.375
            
            # 파란 점 (Blue Dot)
            target_dot = patches.Circle((0.5, target_y), 0.03, color='blue', zorder=10)
            ax.add_patch(target_dot)
            
            # 타겟 라벨
            ax.annotate('권장 (Target)', xy=(0.5, target_y), xytext=(0.15, target_y), 
                        arrowprops=dict(facecolor='blue', edgecolor='blue', arrowstyle='->'),
                        fontsize=9, fontweight='bold', color='blue', ha='center', va='center')

            # 5. 시각적 조정
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off') # 축 숨기기
            ax.set_title("가공 바이트 위치 표준", fontsize=10)
            
            return fig

        col_bite_input, col_bite_img = st.columns([1.5, 1])
        
        with col_bite_input:
            bite_check = st.radio("현재 바이트 사용 구간은?", ["상 (Upper)", "중 (Middle)", "중하 (Middle-Lower)", "하 (Lower)"], index=1)
            st.caption("※ 우측 그림의 '파란색 점(중하)' 위치를 준수하세요.")
            
        with col_bite_img:
            st.pyplot(draw_byte_guide(), use_container_width=True)        
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
            
            # 1. 주파수 점검
            if not (MIN_FREQ <= input_freq <= MAX_FREQ):
                errors.append(f"❌ [주파수 이탈] 기준: {MIN_FREQ}~{MAX_FREQ}Hz / 현재: {input_freq}Hz")
            
            # 2. RPM 점검
            if not (MIN_RPM <= input_rpm <= MAX_RPM):
                errors.append(f"❌ [RPM 이탈] 기준: {MIN_RPM}~{MAX_RPM}RPM / 현재: {input_rpm}RPM")
                
            # 3. 2차 가공 깊이 점검
            if not (MIN_DEPTH_2ND <= input_depth <= MAX_DEPTH_2ND):
                errors.append(f"❌ [가공 깊이 이탈] 기준: {MIN_DEPTH_2ND}~{MAX_DEPTH_2ND}mm / 현재: {input_depth}mm")
                
            # 4. 텐션 점검
            if not (MIN_TENSION <= input_tension <= MAX_TENSION):
                errors.append(f"❌ [텐션 이탈] 기준: {MIN_TENSION}~{MAX_TENSION}Kg / 현재: {input_tension}Kg")

            # 5. 절삭 속도 점검
            if not (MIN_CUT_SEC <= input_cut_sec <= MAX_CUT_SEC):
                errors.append(f"❌ [절삭 속도 이탈] 기준: {MIN_CUT_SEC}~{MAX_CUT_SEC}초 / 현재: {input_cut_sec}초")

            # 6. 바이트 위치 점검
            if bite_check != "중하 (Middle-Lower)":
                errors.append(f"⚠️ [바이트 위치 경고] 권장: 중하(Middle-Lower) / 현재: {bite_check}")

            # 품질 데이터 판정
            q_result = "PASS"
            if meas_roundness > LIMIT_ROUNDNESS or meas_step > LIMIT_STEP:
                q_result = "FAIL (Quality)"
                errors.append(f"❌ [품질 불량] 진원도/단차 기준 초과")
            elif errors: # If there are setting errors but no quality errors
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
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
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

# ==========================================
# [관리자 전용 대시보드 (Tab 3)]
# ==========================================
if is_admin:
    # tab3 변수가 정의되어 있어야 함 (위에서 정의됨)
    with tab3:
        st.header("📈 관리자 대시보드 (Manager Dashboard)")
        st.info("관리자 전용: 품질 KPI 및 트렌드 분석 모니터링")
        
        if os.path.exists(LOG_FILE):
            df_admin = pd.read_csv(LOG_FILE)
            if not df_admin.empty:
                # ------------------------------------------
                # 1. KPI 지표 (Metrics)
                # ------------------------------------------
                st.subheader("1. 핵심 성과 지표 (KPI Monitor)")
                
                total_cnt = len(df_admin)
                pass_df = df_admin[df_admin['Result'] == 'PASS']
                pass_cnt = len(pass_df)
                fail_cnt = total_cnt - pass_cnt
                
                # 합격률 계산
                pass_rate = (pass_cnt / total_cnt) * 100 if total_cnt > 0 else 0
                
                # KPI 카드 배치
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("총 점검 수 (Total)", f"{total_cnt} 건")
                kpi2.metric("합격 수 (PASS)", f"{pass_cnt} 건", delta=f"{pass_rate:.1f}%")
                kpi3.metric("불량 수 (FAIL)", f"{fail_cnt} 건", delta_color="inverse")
                
                st.markdown("---")
                
                # ------------------------------------------
                # 2. 품질 데이터 트렌드 (Line Chart)
                # ------------------------------------------
                st.subheader("2. 품질 데이터 트렌드 (Quality Trends)")
                
                # Timestamp를 datetime으로 변환
                df_admin['Timestamp'] = pd.to_datetime(df_admin['Timestamp'])
                
                # 필요한 컬럼만 추출하여 인덱스 설정
                df_trend = df_admin[['Timestamp', 'Roundness', 'Step']].copy()
                df_trend.set_index('Timestamp', inplace=True)
                
                # 차트 그리기
                st.caption("🟦 진원도(Roundness) & 🟧 단차(Step) 변화 추이")
                st.line_chart(df_trend)
                
                # ------------------------------------------
                # 3. 상세 로그 (관리자용 - 전체 데이터)
                # ------------------------------------------
                st.markdown("---")
                st.subheader("3. 전체 상세 로그 (Full Log)")
                st.dataframe(df_admin.sort_values(by="Timestamp", ascending=False), use_container_width=True)
            else:
                st.warning("데이터가 아직 없습니다.")
        else:
            st.warning("로그 파일이 없습니다. 점검을 먼저 수행해주세요.")
