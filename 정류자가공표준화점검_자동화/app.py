import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import io
import socket
import qrcode
import subprocess
import threading
import time
import re
import random
from PIL import Image
from datetime import datetime

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

LOG_FILE = "inspection_logs.csv"
PORT = 8501
# Base Subdomain
APP_SUBDOMAIN_BASE = "dcv5-auditor" 

# ==========================================
# [함수 정의: 데이터 저장 및 로드, QR 생성]
# ==========================================
def calculate_control_limits(data, sigma=3):
    """Calculate Control Limits (UCL, LCL, Mean) for X-Chart"""
    if len(data) < 2: return None, None, None
    mean = data.mean()
    std = data.std()
    ucl = mean + (sigma * std)
    lcl = mean - (sigma * std)
    return ucl, lcl, mean

def save_log(data):
    """점검 결과를 CSV 파일에 저장"""
    df = pd.DataFrame([data])
    try:
        if not os.path.exists(LOG_FILE):
            df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
        else:
            existing_df = pd.read_csv(LOG_FILE)
            for col in existing_df.columns:
                if col not in df.columns:
                    df[col] = "" 
            df.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")
        return True, "저장 성공"
    except PermissionError:
        return False, "파일이 열려있습니다. 엑셀을 닫고 다시 시도해주세요."
    except Exception as e:
        return False, f"저장 중 오류 발생: {str(e)}"

def load_log():
    """CSV 파일에서 점검 이력 로드"""
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def to_excel(df):
    """데이터프레임을 엑셀 바이너리로 변환"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def analyze_trends(df):
    """데이터 추이 분석 (최근 5개 데이터 기준)"""
    alerts = []
    if len(df) < 3: return alerts

    recent = df.tail(5)
    
    if recent['Tension_Kg'].is_monotonic_increasing:
        alerts.append("⚠️ [경고] 텐션값이 지속적으로 상승하고 있습니다. (장력 조절 필요)")
    elif recent['Tension_Kg'].is_monotonic_decreasing:
        alerts.append("⚠️ [경고] 텐션값이 지속적으로 하락하고 있습니다. (벨트 마모 의심)")

    if recent['Roundness_um'].is_monotonic_increasing:
        alerts.append("⚠️ [주의] 진원도가 점차 나빠지고 있습니다. (바이트 마모 가능성)")

    return alerts

def get_all_ips():
    """사용 가능한 모든 IPv4 주소 반환"""
    ip_list = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ip_list.append(ip)
    except:
        pass
    
    if not ip_list:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            ip_list.append(ip)
        except:
            pass
            
    return ip_list if ip_list else ["127.0.0.1"]

def generate_qr(url):
    """URL에 대한 QR 코드 생성"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

# --- SSH Tunnel Automation (Multi-Provider) ---
def kill_ssh():
    """기존 SSH 프로세스 종료"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ssh.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def start_tunnel_provider():
    """SSH 터널 시작 (Serveo -> Localhost.run 순차 시도)"""
    kill_ssh() # Clean up previous sessions
    
    providers = []
    
    # 1. Serveo (Custom)
    providers.append({
        "name": "Serveo (Custom)",
        "cmd": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"{APP_SUBDOMAIN_BASE}:80:localhost:{PORT}", "serveo.net"],
        "regex": r"https://[a-zA-Z0-9-]+\.serveo\.net"
    })
    
    # 2. Serveo (Random)
    providers.append({
        "name": "Serveo (Random)",
        "cmd": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"80:localhost:{PORT}", "serveo.net"],
        "regex": r"https://[a-zA-Z0-9-]+\.serveo\.net"
    })
    
    # 3. Localhost.run (Fallback)
    providers.append({
        "name": "Localhost.run",
        "cmd": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60", "-R", f"80:localhost:{PORT}", "nokey@localhost.run"],
        "regex": r"https://[a-zA-Z0-9-]+\.lhr\.life"
    })

    final_url = None
    final_process = None

    for p in providers:
        print(f"Trying provider: {p['name']}")
        
        process = subprocess.Popen(
            p['cmd'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8'
        )
        
        start_time = time.time()
        found = False
        
        # Give each provider 8 seconds to respond
        while time.time() - start_time < 8:
            line = process.stdout.readline()
            if not line: break
            
            # Check for success URL
            match = re.search(p['regex'], line)
            if match:
                final_url = match.group(0)
                final_process = process
                found = True
                break
            
            # Fail fast if possible
            if "Forwarding failed" in line or "already taken" in line:
                break 
        
        if found:
            break
        else:
            process.kill() # Kill failed process before trying next
            
    return final_url, final_process

# ==========================================
# [UI 및 스타일 설정]
# ==========================================
st.set_page_config(page_title="가공표준화점검 (HSG)", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# Inject PWA Meta Tags & Open Graph Tags for Social Sharing
st.markdown(f"""
    <link rel="manifest" href="manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    
    <!-- Open Graph Tags for KakaoTalk/SMS Previews -->
    <meta property="og:title" content="🛡️ 가공표준화점검 (HSG)">
    <meta property="og:description" content="Click to install the Quality Inspection App.">
    <meta property="og:image" content="https://cdn-icons-png.flaticon.com/512/2910/2910795.png">
    <meta property="og:type" content="website">
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Global Settings */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
    }

    /* Background: Darker Sky Blue */
    .stApp { 
        background-color: #B3D9FF; 
    }
    
    /* Title/Headers: Malgun Gothic Bold 26px */
    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Malgun Gothic', sans-serif !important;
        font-weight: bold !important;
        font-size: 26px !important;
        color: #000000 !important;
    }
    
    /* Input Labels (Treating as titles/headers for inputs) */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stRadio label {
        font-family: 'Malgun Gothic', sans-serif !important;
        font-weight: bold !important;
        font-size: 20px !important;
        color: #000000 !important;
    }

    /* Body Text: Malgun Gothic Bold 18px */
    .stMarkdown p, .stMarkdown div, .stMarkdown span, div[data-testid="stMarkdownContainer"] p {
        font-family: 'Malgun Gothic', sans-serif !important;
        font-weight: bold !important;
        font-size: 18px !important;
        color: #333333 !important;
    }
    
    /* HSG Logo Fixed Top Right */
    .hsg-logo {
        position: fixed;
        top: 2.5rem;
        right: 1.5rem;
        z-index: 99999;
        font-family: 'Arial Black', sans-serif;
        font-size: 24px;
        font-weight: 900;
        color: #0052cc;
        background-color: rgba(255, 255, 255, 0.9);
        padding: 5px 15px;
        border-radius: 8px;
        border: 2px solid #0052cc;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .big-font { font-size:20px !important; font-weight: bold; }
    .success { color: green; font-weight: bold; }
    .fail { color: red; font-weight: bold; }
    
    /* Sidebar Styling */
    div[data-testid="stSidebar"] { background-color: #f0f8ff; border-right: 1px solid #dae1e7; }
    
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #333; }
    div[data-testid="stExpander"] { border: 1px solid #b0c4de; border-radius: 10px; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    <div class="hsg-logo">HSG</div>
    """, unsafe_allow_html=True)

# Initialize Session State
if 'public_url' not in st.session_state:
    st.session_state.public_url = None
if 'tunnel_process' not in st.session_state:
    st.session_state.tunnel_process = None

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910795.png", width=100)
    st.title("DC V5\nAuditor App")
    st.caption("v2.6 (Multi-Network)")
    st.markdown("---")
    
    conn_mode = st.radio("📡 모드 선택 (Select Mode)", 
                         ["🔥 모바일 핫스팟 (Private Net)", "📱 어플 다운로드 (Public Net)", "🔒 관리자/PC 모드 (Local)"])
    
    if conn_mode == "🔥 모바일 핫스팟 (Private Net)":
        st.markdown("### 🔥 Mobile Hotspot Connection")
        st.info("**가장 빠르고 안정한 연결 방식입니다.**")
        
        st.markdown("""
        **[연결 순서]**
        1. **휴대폰**의 '모바일 핫스팟'을 켭니다.
        2. **PC** 와이파이를 휴대폰 핫스팟에 연결합니다.
        3. 아래 QR코드를 휴대폰 카메라로 스캔하세요.
        """)
        
        # Get active local IP (prefer 192.x or 172.x which are common for hotspots)
        all_ips = get_all_ips()
        # Filter for likely hotspot IPs if possible, else take the first non-localhost
        target_ip = all_ips[0]
        for ip in all_ips:
            if ip.startswith("192.168") or ip.startswith("172."):
                target_ip = ip
                break
                
        hotspot_url = f"http://{target_ip}:{PORT}"
        
        # QR Code Generation
        qr_img = generate_qr(hotspot_url)
        img_byte_arr = io.BytesIO()
        qr_img.save(img_byte_arr, format='PNG')
        st.image(img_byte_arr, caption=f"Scan to Connect: {hotspot_url}", width=200)
        
        st.success(f"🔗 접속 주소: {hotspot_url}")
        st.warning("주의: PC와 휴대폰이 같은 와이파이(핫스팟)에 있어야 합니다.")

    elif conn_mode == "🔒 관리자/PC 모드 (Local)":
        st.markdown("### 💻 Local Dashboard")
        available_ips = get_all_ips()
        selected_ip = st.selectbox("IP Address", available_ips)
        st.code(f"http://{selected_ip}:{PORT}")
        st.caption("PC나 사내망에서 접속할 때 사용하세요.")
        
    else:
        st.markdown("### 📥 Mobile App Install")
        st.info("한 번만 설치하면 언제든 접속 가능!")
        
        if st.session_state.public_url:
            # Display as "App Store" style
            st.success("✅ 다운로드 링크 생성 완료!")
            qr_img = generate_qr(st.session_state.public_url)
            img_byte_arr = io.BytesIO()
            qr_img.save(img_byte_arr, format='PNG')
            
            col_qr, col_desc = st.columns([1, 1.5])
            with col_qr:
                 st.image(img_byte_arr, width=110)
            with col_desc:
                 st.markdown(f"**[설치하기]({st.session_state.public_url})**")
                 st.caption(f"Server: {st.session_state.public_url.split('/')[2]}")

            st.markdown("---")
            st.markdown("#### 📤 공유하기 (Share Link)")
            
            # Native Share Button (Web Share API)
            components.html(f"""
                <style>
                .share-btn {{
                    background: linear-gradient(135deg, #FEE500 0%, #F5C900 100%);
                    color: #3C1E1E;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    width: 100%;
                    cursor: pointer;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: 'Apple SD Gothic Neo', sans-serif;
                }}
                .share-btn:active {{ transform: scale(0.98); }}
                </style>
                <button class="share-btn" onclick="share()">
                    💬 카카오톡/문자로 공유하기
                </button>
                <script>
                async function share() {{
                    const shareData = {{
                        title: '가공표준화점검 (HSG)',
                        text: 'HSG 정류자 가공 표준화 점검 어플 설치 링크입니다.\\n(클릭하여 설치)',
                        url: '{st.session_state.public_url}'
                    }};
                    
                    if (navigator.share) {{
                        try {{
                            await navigator.share(shareData);
                        }} catch (err) {{
                            console.log('Share failed:', err);
                        }}
                    }} else {{
                        // Fallback: Copy to clipboard
                        const el = document.createElement('textarea');
                        el.value = shareData.url;
                        document.body.appendChild(el);
                        el.select();
                        document.execCommand('copy');
                        document.body.removeChild(el);
                        alert('🔗 링크가 복사되었습니다!');
                    }}
                }}
                </script>
                """, height=70)
            
            st.caption(f"Server: {st.session_state.public_url}")
            
            st.markdown("---")
            st.markdown("#### ⚡ 설치 방법 (Install Guide)")
            st.info("""
            **1. 링크 접속** (카톡/문자/QR)
            **2. '홈 화면에 추가'** 누르기
               - 삼성 인터넷: `≡` → `현재 페이지 추가` → `홈 화면`
               - 크롬: `⋮` → `홈 화면에 추가`
            **3. 완료!** 이제 바탕화면 아이콘으로 접속하세요.
            """)
                
            if st.button("🔄 링크 재생성 (Server Restart)"):
                kill_ssh()
                st.session_state.public_url = None
                st.rerun()
        else:
            st.markdown("전세계 어디서든 접속 가능한 **영구 앱 링크**를 생성합니다.")
            if st.button("🚀 어플 다운로드 링크 생성", type="primary"):
                with st.spinner("최적의 통신 서버를 찾는 중... (최대 20초)"):
                    url, proc = start_tunnel_provider()
                    if url:
                        st.session_state.public_url = url
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("⚠️ 모든 서버 연결 실패. 잠시 후 다시 시도해주세요.")
                        kill_ssh()
    
    st.markdown("---")
    st.caption("System Online 🟢")

tab1, tab2 = st.tabs(["🛡️ 공정 점검 (Audit)", "📊 이력 관리 & 분석 (Analytics)"])

# ==========================================
# [탭 1: 공정 점검]
# ==========================================
with tab1:
    st.markdown("### 1. 정보입력")
    
    with st.form("setting_check_form", clear_on_submit=False):
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            worker_name = st.text_input("점검자 성명 (Inspector)", placeholder="홍길동")
        with c_w2:
            shift = st.selectbox("근무조 (Shift)", ["주간 (Day)", "야간 (Night)"])

        st.markdown("---")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            input_freq = st.number_input("인버터 주파수 (Hz)", value=0.0, step=0.1, format="%.1f")
            input_rpm = st.number_input("실측 RPM", value=0, step=10)
        with c2:
            input_tension = st.number_input("밸트 입력값 (Kg)", value=0.00, step=0.01, format="%.2f")
            input_cut_sec = st.number_input("절삭 속도 (Sec)", value=0.0, step=0.5)
        with c3:
             input_depth = st.number_input("2차 가공 깊이 (mm)", value=0.00, step=0.01, format="%.2f")
             bite_check = st.selectbox("바이트 위치 확인", ["상 (Upper)", "중 (Middle)", "중하 (Middle-Lower)", "하 (Lower)"], index=2)
        
        st.markdown("---")
        st.markdown("### 2. 진원도 측정")
        
        c4, c5 = st.columns(2)
        with c4:
             meas_roundness = st.number_input("측정 진원도 (µm)", value=0.0, step=0.1)
        with c5:
             meas_step = st.number_input("측정 단차 (µm)", value=0.0, step=0.1)

        submitted = st.form_submit_button("🛡️ 입력값 감사 및 저장 (SAVE)", type="primary")

    if submitted:
        if not worker_name:
            st.error("⚠️ 점검자 성명을 입력해주세요!")
        else:
            errors = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Validations
            if input_freq != STD_FREQ: errors.append(f"❌ [주파수] 표준: {STD_FREQ}Hz / 현재: {input_freq}Hz")
            if input_rpm != STD_RPM: errors.append(f"❌ [RPM] 표준: {STD_RPM}RPM / 현재: {input_rpm}RPM")
            if input_depth != STD_DEPTH_2ND: errors.append(f"❌ [가공깊이] 표준: {STD_DEPTH_2ND}mm / 현재: {input_depth}mm")
            if input_tension != STD_TENSION: errors.append(f"❌ [텐션] 표준: {STD_TENSION}Kg / 현재: {input_tension}Kg")
            if input_cut_sec != STD_CUT_SEC: errors.append(f"❌ [절삭속도] 표준: {STD_CUT_SEC}s / 현재: {input_cut_sec}s")
            if bite_check != "중하 (Middle-Lower)": errors.append(f"⚠️ [바이트위치] 권장: 중하 / 현재: {bite_check}")

            is_roundness_fail = meas_roundness > LIMIT_ROUNDNESS
            is_step_fail = meas_step > LIMIT_STEP

            status = "FAIL" if errors or is_roundness_fail or is_step_fail else "PASS"
            
            log_data = {
                "Timestamp": timestamp,
                "Worker": worker_name,
                "Shift": shift,
                "Result": status,
                "Freq_Hz": input_freq,
                "RPM": input_rpm,
                "Tension_Kg": input_tension,
                "Cut_Sec": input_cut_sec,
                "Depth_mm": input_depth,
                "Bite_Pos": bite_check,
                "Roundness_um": meas_roundness,
                "Step_um": meas_step
            }
            
            is_saved, msg = save_log(log_data)
            if is_saved:
                st.toast("데이터가 안전하게 저장되었습니다.", icon="💾")
            else:
                st.error(f"🚨 저장 실패: {msg}")

            if status == "PASS":
                st.balloons()
                st.markdown("### ✅ AUDITED & CERTIFIED")
                st.success(f"[{timestamp}] 검사 완료 - 품질 기준 만족 (Approved)")
                
                with st.container():
                    st.info(f"""
                    **DIGITAL CERTIFICATE**
                    - **Inspector**: {worker_name} ({shift})
                    - **Result**: PASS
                    - **Key Metrics**: Tension {input_tension}kg, Roundness {meas_roundness}µm
                    
                    *Quality is not negotiable.*
                    """)
            else:
                st.error("🚨 품질 기준 위반 (FAIL) - 즉시 조치하십시오.")
                for err in errors:
                    st.write(err)
                
                if is_roundness_fail or is_step_fail:
                     st.error(f"🚨 품질 불량: 진원도({meas_roundness}µm) / 단차({meas_step}µm)")
                     with st.expander("🛠️ 긴급 조치 가이드", expanded=True):
                        st.warning("1. 바이트 마모 점검 / 2. 텐션 2.72kg 재설정 / 3. 속도 2.5단 확인")

# ==========================================
# [탭 2: 이력 관리 & 분석]
# ==========================================
with tab2:
    col_h1, col_h2, col_h3 = st.columns([6, 2, 2])
    with col_h1:
        st.markdown("### 📊 점검 이력 및 추이 분석")
    with col_h2:
        if st.button("🗑️ 이력 초기화", type="secondary"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
    with col_h3:
         df = load_log()
         if not df.empty:
            excel_data = to_excel(df)
            st.download_button(
                label="📥 엑셀 다운로드",
                data=excel_data,
                file_name=f"audit_log_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    
    if not df.empty:
        if 'Worker' not in df.columns:
            st.warning("⚠️ 이전 버전의 로그 파일이 감지되었습니다. 일부 데이터(점검자 등)가 없을 수 있습니다.")
        
        # --- Trend Analysis ---
        st.markdown("### 📊 이력확인 및 추이분석")
        alerts = analyze_trends(df)
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("✅ 최근 데이터 추이가 안정적입니다.", icon="👍")
        
        st.markdown("---")
        
        # --- Statistics ---
        st.markdown("#### 📈 Summary Statistics (최근 20건)")
        recent_stats = df.tail(20)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("평균 텐션", f"{recent_stats['Tension_Kg'].mean():.2f} Kg")
        s2.metric("평균 진원도", f"{recent_stats['Roundness_um'].mean():.1f} µm")
        s3.metric("최악 진원도", f"{recent_stats['Roundness_um'].max():.1f} µm")
        s4.metric("PASS 비율", f"{(len(recent_stats[recent_stats['Result']=='PASS'])/len(recent_stats))*100:.0f}%")
        
        st.markdown("---")

        def highlight_status(val):
            color = 'red' if val == 'FAIL' else 'green'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df.sort_values(by="Timestamp", ascending=False).style.map(highlight_status, subset=['Result']),
            use_container_width=True
        )
        
        chart_tab1, chart_tab2 = st.tabs(["주요 인자 (Key Factors)", "품질 결과 (Quality Output)"])
        
        with chart_tab1:
            c1, c2 = st.columns(2)
            with c1: st.line_chart(df, x="Timestamp", y="Tension_Kg", color="#FF5733")
            with c2: st.line_chart(df, x="Timestamp", y="RPM", color="#33FF57")
            
        with chart_tab2:
            c3, c4 = st.columns(2)
            with c3: st.line_chart(df, x="Timestamp", y="Roundness_um", color="#3357FF")
            with c4: st.line_chart(df, x="Timestamp", y="Step_um", color="#FF33FF")
            
    else:
        st.info("데이터가 없습니다.")

    # --- X-R Control Charts Section ---
    if not df.empty and len(df) > 1:
        st.markdown("---")
        st.markdown("### 📉 X-R Control Charts (공정 관리도)")
        
        # Chart Helper
        def draw_control_chart(df, target_col, std_val, limit_val=None, title=""):
            st.markdown(f"#### {title}")
            
            chart_data = df[['Timestamp', target_col]].copy()
            chart_data['Timestamp'] = pd.to_datetime(chart_data['Timestamp'])  # Ensure timestamp format
            
            # Calculate Statistics
            ucl, lcl, mean = calculate_control_limits(chart_data[target_col])
            
            # Create a combined chart dataframe
            chart_data['Mean'] = mean
            chart_data['UCL'] = ucl
            chart_data['LCL'] = lcl
            if limit_val:
                chart_data['SPEC_LIMIT'] = limit_val
            
            # Display Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Mean (X̄)", f"{mean:.2f}")
            m2.metric("UCL (+3σ)", f"{ucl:.2f}")
            if limit_val:
                m3.metric("Spec Limit", f"{limit_val:.2f}")
            else:
                m3.metric("LCL (-3σ)", f"{lcl:.2f}")

            # Plot using Streamlit Line Chart (Simple version)
            # For better control charts, Altair is preferred but keeping it simple as per current stack
            st.line_chart(chart_data.set_index('Timestamp')[[target_col, 'Mean', 'UCL', 'LCL'] + (['SPEC_LIMIT'] if limit_val else [])])

        # 1. Tension Chart
        draw_control_chart(df, 'Tension_Kg', STD_TENSION, title="① Tension (텐션) 관리도")
        
        # 2. Roundness Chart (Spec Limit exists)
        draw_control_chart(df, 'Roundness_um', 0, limit_val=LIMIT_ROUNDNESS, title="② Roundness (진원도) 관리도")
        
        # 3. Step Chart (Spec Limit exists)
        draw_control_chart(df, 'Step_um', 0, limit_val=LIMIT_STEP, title="③ Step (단차) 관리도")

