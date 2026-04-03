import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from streamlit_gsheets import GSheetsConnection

# ══════════════════════════════════════════════════════════════
# HSG 스마트작업일보 v8.1
# 기존 streamlit-gsheets 연동 방식 유지
#
# [Fix1] 구글 시트 전송 오류 3가지 원인 수정
#   - ttl=0 으로 캐시 무효화 (stale 데이터 방지)
#   - 빈 시트 안전 처리 (컬럼 불일치 오류 제거)
#   - 전송 실패 상세 오류 메시지 출력
#
# [Fix2] 데이터 휘발 방지
#   - 구글 시트 "임시저장" 시트를 자동저장소로 활용
#   - 세션 재시작 시 자동 복원
#
# [Fix3] 토크 기준 통일 → 15 kgf·cm 미만 NG
# [Fix4] ➕ 무한분할 방지
# [Fix5] 중복 전송 방지
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="HSG 스마트작업일보 v8.1",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .emergency-alarm {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #ff4b4b; color: white; padding: 14px;
        text-align: center; font-size: 20px; font-weight: 900;
        z-index: 9999; border-bottom: 3px solid #fff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        animation: blink 1.2s ease-in-out infinite;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.8} }

    .main .block-container { padding-top: 60px !important; }

    input[type=number]::-webkit-inner-spin-button,
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; }
    input[type=number] { -moz-appearance: textfield !important; }

    .section-title {
        font-size: 17px; font-weight: 700; color: #58a6ff;
        border-left: 5px solid #58a6ff; padding-left: 11px;
        margin: 22px 0 14px;
    }
    .total-stat-box {
        background-color: #0d1117; padding: 20px;
        border-radius: 10px; border: 2px solid #58a6ff;
        text-align: center; margin-bottom: 16px;
    }
    .check-item-box {
        background-color: #161b22; padding: 12px;
        border-radius: 6px; border: 1px solid #30363d;
        text-align: center; color: #c9d1d9;
    }
    .check-item-box.confirmed {
        background-color: #0d2136; border-color: #58a6ff; color: #58a6ff;
    }
    .save-badge-ok   { background:#0d2e12; color:#3fb950; padding:5px 12px; border-radius:4px; font-size:12px; display:inline-block; }
    .save-badge-fail { background:#2d1012; color:#f85149; padding:5px 12px; border-radius:4px; font-size:12px; display:inline-block; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 상수
# ══════════════════════════════════════════════════════════════
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
DEFECT_TYPES   = ["없음","이음","찍힘","파형","크랙","치수불량","기타"]
DEFECT_REASONS = ["없음","셋업","부품","품질","설비","작업자"]
SUPPORT_WORKERS= ["없음","강유진","유진화","하순영","강은미","권갑순"]
BOM_PARTS      = ["감속기","로타","케이스","리어커버","센서"]
TORQUE_LIMIT   = 15.0   # kgf·cm 미만 → NG (전체 통일 기준)
FIXED_WORKER   = "안희선, 강선혜"

SLOTS = [
    ("08:30","09:30",60), ("09:30","10:30",60),
    ("10:40","11:40",60), ("11:40","12:30",50),
    ("13:20","14:30",70), ("14:30","15:30",60),
    ("15:40","16:30",50), ("16:30","17:30",60),
    ("18:00","19:00",60), ("19:00","20:00",60),
]

MAIN_SHEET    = "sheet1"       # 최종 전송 시트 (기존 유지)
BOM_SHEET     = "sheet1_BOM"   # BOM/토크 전송 시트
AUTOSAVE_SHEET= "임시저장"      # 자동저장 전용 시트

# ══════════════════════════════════════════════════════════════
# [Fix1] 안전한 시트 읽기/쓰기 유틸 (streamlit-gsheets 방식 유지)
# ══════════════════════════════════════════════════════════════
def safe_read(conn, worksheet: str) -> pd.DataFrame:
    """
    핵심 수정:
    - ttl=0 → 캐시 없이 항상 최신 시트 데이터 읽기
    - 빈 시트 반환 시 빈 DataFrame 안전하게 처리
    """
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        # 전부 NaN인 컬럼 제거 (빈 시트 부산물)
        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
        return df
    except Exception as e:
        # 시트가 아예 없을 때도 빈 DataFrame 반환 (오류 전파 안 함)
        return pd.DataFrame()

def safe_update(conn, worksheet: str, new_rows: list[dict]) -> tuple[bool, str]:
    """
    핵심 수정:
    - 기존 데이터 읽기(ttl=0) → 새 행 concat → 전체 update
    - df_old가 비어있으면 new_rows만 사용 (컬럼 불일치 방지)
    - 상세 오류 메시지 반환
    """
    try:
        df_old = safe_read(conn, worksheet)
        df_new = pd.DataFrame(new_rows)

        if df_old.empty or len(df_old.columns) == 0:
            # 빈 시트: 새 데이터만 저장
            combined = df_new
        else:
            # 컬럼 정렬 후 concat (누락 컬럼은 NaN 대신 "" 처리)
            all_cols = list(dict.fromkeys(
                list(df_old.columns) + list(df_new.columns)
            ))
            df_old = df_old.reindex(columns=all_cols, fill_value="")
            df_new = df_new.reindex(columns=all_cols, fill_value="")
            combined = pd.concat([df_old, df_new], ignore_index=True)

        conn.update(worksheet=worksheet, data=combined)
        return True, "성공"

    except Exception as e:
        # 상세 오류 타입과 메시지 반환
        return False, f"{type(e).__name__}: {e}"


def autosave_state(conn) -> bool:
    """
    [Fix2] 현재 세션 상태를 구글 시트 '임시저장' 시트에 1행으로 저장
    비상호출, 행분할, 수동저장 버튼 클릭 시 호출
    """
    try:
        rows_snapshot = []
        for row in st.session_state.rows:
            rid = row['id']
            rows_snapshot.append({
                "id":         rid,
                "time":       row['time'],
                "m":          row['m'],
                "start_h":    row['start_h'],
                "is_split":   row['is_split'],
                "product":    st.session_state.get(f"p_{rid}",  "선택"),
                "actual":     st.session_state.get(f"a_{rid}",  0),
                "def_type":   st.session_state.get(f"dt_{rid}", "없음"),
                "def_qty":    st.session_state.get(f"dq_{rid}", 0),
                "def_reason": st.session_state.get(f"dr_{rid}", "없음"),
                "down_min":   st.session_state.get(f"dm_{rid}", 0),
                "support":    st.session_state.get(f"s_{rid}",  "없음"),
            })

        bom_snapshot = {
            pt: {"qty": st.session_state.get(f"q_{pt}", 0),
                 "lot": st.session_state.get(f"l_{pt}", "")}
            for pt in BOM_PARTS
        }
        torque_snapshot = {
            str(k): st.session_state.get(f"t_{k}", "")
            for k in range(1, 6)
        }

        snapshot = pd.DataFrame([{
            "saved_at":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "work_date":    str(st.session_state.get("work_date", date.today())),
            "issue_state":  str(st.session_state.get("issue_state", "")),
            "confirmed":    str(st.session_state.get("confirmed",   False)),
            "rows_json":    json.dumps(rows_snapshot,  ensure_ascii=False),
            "bom_json":     json.dumps(bom_snapshot,   ensure_ascii=False),
            "torques_json": json.dumps(torque_snapshot, ensure_ascii=False),
        }])

        # 임시저장 시트는 항상 1행 덮어쓰기 (누적 불필요)
        conn.update(worksheet=AUTOSAVE_SHEET, data=snapshot)
        return True
    except Exception as e:
        return False


def restore_from_autosave(conn) -> bool:
    """
    [Fix2] 세션 재시작 시 '임시저장' 시트에서 복원
    """
    try:
        df = safe_read(conn, AUTOSAVE_SHEET)
        if df.empty:
            return False

        row = df.iloc[-1]

        # 날짜 복원
        try:
            st.session_state["work_date"] = date.fromisoformat(str(row.get("work_date", "")))
        except Exception:
            pass

        # 비상 상태 복원
        issue = str(row.get("issue_state", ""))
        st.session_state.issue_state = issue if issue not in ("", "None") else None

        # 행 데이터 복원
        rows_json = row.get("rows_json", "")
        if rows_json:
            saved_rows = json.loads(rows_json)
            st.session_state.rows = [
                {k: v for k, v in r.items()
                 if k in ["id","time","m","start_h","is_split"]}
                for r in saved_rows
            ]
            st.session_state.next_id = max(r["id"] for r in saved_rows) + 1
            for r in saved_rows:
                rid = r["id"]
                st.session_state[f"p_{rid}"]  = r.get("product",    "선택")
                st.session_state[f"a_{rid}"]  = int(r.get("actual",  0))
                st.session_state[f"dt_{rid}"] = r.get("def_type",   "없음")
                st.session_state[f"dq_{rid}"] = int(r.get("def_qty", 0))
                st.session_state[f"dr_{rid}"] = r.get("def_reason", "없음")
                st.session_state[f"dm_{rid}"] = int(r.get("down_min",0))
                st.session_state[f"s_{rid}"]  = r.get("support",    "없음")

        # BOM 복원
        bom_json = row.get("bom_json", "")
        if bom_json:
            bom = json.loads(bom_json)
            for pt, v in bom.items():
                st.session_state[f"q_{pt}"] = int(v.get("qty", 0))
                st.session_state[f"l_{pt}"] = str(v.get("lot", ""))

        # 토크 복원
        torques_json = row.get("torques_json", "")
        if torques_json:
            torques = json.loads(torques_json)
            for k, v in torques.items():
                st.session_state[f"t_{k}"] = str(v)

        st.session_state.autosave_msg  = f"✓ 데이터 복원 완료 ({row.get('saved_at','')})"
        st.session_state.autosave_ok   = True
        return True

    except Exception as e:
        st.session_state.autosave_msg = f"⚠ 복원 실패: {e}"
        st.session_state.autosave_ok  = False
        return False

# ══════════════════════════════════════════════════════════════
# 구글 시트 연결 (기존 방식 유지)
# secrets.toml의 [connections.gsheets] 설정 그대로 사용
# ══════════════════════════════════════════════════════════════
conn = st.connection("gsheets", type=GSheetsConnection)

# ══════════════════════════════════════════════════════════════
# 세션 초기화
# ══════════════════════════════════════════════════════════════
if 'rows' not in st.session_state:
    st.session_state.rows = [
        {"id":i, "time":f"{s}-{e}", "m":float(m),
         "start_h":int(s.split(':')[0]), "is_split":False}
        for i,(s,e,m) in enumerate(SLOTS)
    ]
    st.session_state.next_id     = len(SLOTS)
    st.session_state.issue_state = None
    st.session_state.submitted   = False
    st.session_state.confirmed   = False
    st.session_state.autosave_msg= ""
    st.session_state.autosave_ok = True

# [Fix2] 앱 시작 시 1회만 복원 시도
if "restore_attempted" not in st.session_state:
    st.session_state.restore_attempted = True
    restore_from_autosave(conn)

# ══════════════════════════════════════════════════════════════
# UI 렌더링
# ══════════════════════════════════════════════════════════════

# 비상 알람 바
if st.session_state.issue_state:
    st.markdown(
        f"<div class='emergency-alarm'>"
        f"🚨 현재 상태: [{st.session_state.issue_state}] 보고 중 🚨"
        f"</div>",
        unsafe_allow_html=True
    )

st.title("스마트작업일보 조립1라인 (v8.1)")

# 자동저장 상태 배지
if st.session_state.autosave_msg:
    css = "save-badge-ok" if st.session_state.autosave_ok else "save-badge-fail"
    st.markdown(
        f"<span class='{css}'>{st.session_state.autosave_msg}</span>",
        unsafe_allow_html=True
    )

# ── ① 작업표준 확인 ──────────────────────────────────────────
st.markdown("<div class='section-title'>📋 작업 표준 및 품질 통합 확인</div>",
            unsafe_allow_html=True)

confirmed = st.checkbox(
    "✅ 작업표준 및 작업지침 4대항목 확인 완료",
    key="confirmed"
)
ck_cols = st.columns(4)
items = ["작업표준서 확인","Q-POINT/지침 확인","지그청소 상태 확인","작업 전 자주검사"]
for col, item in zip(ck_cols, items):
    css = "check-item-box confirmed" if confirmed else "check-item-box"
    col.markdown(
        f"<div class='{css}'><b>{item}</b><br>"
        f"{'🟢 확인' if confirmed else '⚪ 미확인'}</div>",
        unsafe_allow_html=True
    )

# ── ② 현장 비상 호출 ─────────────────────────────────────────
st.markdown("<div class='section-title'>🚨 현장 비상 호출</div>",
            unsafe_allow_html=True)

ic = st.columns(5)
for i, label in enumerate(["자재결품","품질문제","장비문제","기타사항","상황종료"]):
    if ic[i].button(label, key=f"btn_{label}", use_container_width=True):
        st.session_state.issue_state = None if label == "상황종료" else label
        st.session_state.submitted   = False
        ok = autosave_state(conn)
        st.session_state.autosave_msg = "✓ 비상 상태 저장 완료" if ok else "⚠ 저장 실패"
        st.session_state.autosave_ok  = ok
        st.rerun()

# ── ③ 생산 관리 기록 ─────────────────────────────────────────
st.markdown("<div class='section-title'>📊 생산 관리 기록</div>",
            unsafe_allow_html=True)

c_info = st.columns(2)
work_date = c_info[0].date_input("🗓️ 작업일자", key="work_date")
c_info[1].info(f"👤 메인 작업자: **{FIXED_WORKER}**")

# 테이블 헤더
hc = st.columns([1.3,0.5,1.8,0.55,0.55,1.0,0.5,0.8,0.55,1.0,0.45,0.45])
for col, h in zip(hc, ["시간대","분","기종","목표","실적","불량명","수량","사유","비가","지원","➕","🗑️"]):
    col.markdown(f"**{h}**")

for idx, row in enumerate(st.session_state.rows):
    rid = row['id']
    c = st.columns([1.3,0.5,1.8,0.55,0.55,1.0,0.5,0.8,0.55,1.0,0.45,0.45])

    p_sel   = c[2].selectbox("기종", ["선택"]+list(PRODUCT_DB.keys()),
                              key=f"p_{rid}", label_visibility="collapsed")
    act_qty = c[4].number_input("실적", min_value=0,
                                key=f"a_{rid}", label_visibility="collapsed")

    uph    = PRODUCT_DB.get(p_sel, 0)
    target = round((uph / 60) * row['m']) if p_sel != "선택" else 0
    st.session_state[f"target_{rid}"] = target

    c[0].write(row['time'])
    c[1].write(f"{row['m']:.0f}")
    c[3].write(f"**{target}**")

    c[5].selectbox("불량명", DEFECT_TYPES,    key=f"dt_{rid}", label_visibility="collapsed")
    c[6].number_input("수량", min_value=0,    key=f"dq_{rid}", label_visibility="collapsed")
    c[7].selectbox("사유",   DEFECT_REASONS,  key=f"dr_{rid}", label_visibility="collapsed")
    c[8].number_input("비가", min_value=0,    key=f"dm_{rid}", label_visibility="collapsed")
    c[9].selectbox("지원",   SUPPORT_WORKERS, key=f"s_{rid}",  label_visibility="collapsed")

    # [Fix4] ➕ 무한분할 방지
    if c[10].button("➕", key=f"add_{rid}"):
        if p_sel == "선택" or act_qty <= 0 or uph <= 0:
            st.warning(f"⚠ [{row['time']}] 기종 선택 및 실적 입력 후 분할하세요")
        else:
            used_m = round((act_qty * (3600 / uph)) / 60, 1)
            down_m = st.session_state.get(f"dm_{rid}", 0)
            rem_m  = row['m'] - used_m - down_m
            if 0 < rem_m < row['m']:
                st.session_state.rows.insert(idx + 1, {
                    "id":       st.session_state.next_id,
                    "time":     row['time'],
                    "m":        rem_m,
                    "start_h":  row['start_h'],
                    "is_split": True
                })
                st.session_state.next_id += 1
                autosave_state(conn)
                st.rerun()
            else:
                st.warning("⚠ 남은 시간이 없거나 분할 불가합니다")

    if row.get('is_split'):
        if c[11].button("🗑️", key=f"del_{rid}"):
            st.session_state.rows.pop(idx)
            autosave_state(conn)
            st.rerun()

# ── ④ 종합 실적 분석 ─────────────────────────────────────────
st.markdown("<div class='section-title'>📈 종합 실적 분석 및 자재 투입 관리</div>",
            unsafe_allow_html=True)

summary_list = []
for r in st.session_state.rows:
    p = st.session_state.get(f"p_{r['id']}", "선택")
    if p != "선택":
        summary_list.append({
            "기종": p,
            "목표": st.session_state.get(f"target_{r['id']}", 0),
            "실적": st.session_state.get(f"a_{r['id']}", 0),
            "불량": st.session_state.get(f"dq_{r['id']}", 0),
        })

if summary_list:
    df_sum = pd.DataFrame(summary_list).groupby("기종").sum().reset_index()
    t_sum  = df_sum['목표'].sum()
    a_sum  = df_sum['실적'].sum()
    d_sum  = df_sum['불량'].sum()
    achieve = round(a_sum / t_sum * 100, 1) if t_sum > 0 else 0
    defect  = round(d_sum / a_sum * 100, 1) if a_sum > 0 else 0

    st.markdown(
        f"""<div class="total-stat-box">
        <span style="font-size:22px;color:#58a6ff;"><b>라인 전체 달성률: {achieve}%</b></span>
        <span style="font-size:22px;margin-left:40px;color:#ff7b72;"><b>라인 전체 불량률: {defect}%</b></span>
        <span style="font-size:16px;margin-left:40px;color:#8b949e;">목표 {t_sum} / 실적 {a_sum}</span>
        </div>""",
        unsafe_allow_html=True
    )

    lot_h = st.columns([1.5,0.6,0.6,0.6,1.5])
    for col, h in zip(lot_h, ["기종명","목표","실적","불량","기종별 LOT"]):
        col.markdown(f"**{h}**")
    for i, sr in df_sum.iterrows():
        rc = st.columns([1.5,0.6,0.6,0.6,1.5])
        rc[0].write(sr['기종'])
        rc[1].write(sr['목표'])
        rc[2].write(sr['실적'])
        rc[3].write(sr['불량'])
        st.session_state[f"model_lot_{sr['기종']}"] = rc[4].text_input(
            "LOT", key=f"mlot_{i}", label_visibility="collapsed"
        )

st.divider()

# ── ⑤ 주요 부품 LOT + 토크 측정 ────────────────────────────
sc1, sc2 = st.columns(2)

with sc1:
    st.write("**주요 부품 LOT (숫자패드)**")
    for pt in BOM_PARTS:
        bc = st.columns([1, 1, 2.5])
        bc[0].info(f"**{pt}**")
        bc[1].number_input("EA",  min_value=0, key=f"q_{pt}", label_visibility="collapsed")
        bc[2].text_input("LOT번호", key=f"l_{pt}", label_visibility="collapsed")

with sc2:
    # [Fix3] 토크 기준 통일: 15 kgf·cm 미만 NG
    st.write(f"**토크 측정 ({int(TORQUE_LIMIT)} kgf·cm 미만 NG)**")
    for k in range(1, 6):
        tc = st.columns([0.8, 2, 1.8])
        tc[0].write(f"**{k}번**")
        t_v = tc[1].text_input(
            "값", key=f"t_{k}",
            placeholder="kgf·cm 입력",
            label_visibility="collapsed"
        )
        if t_v.strip():
            try:
                val = float(t_v.replace(',', '.'))
                if val >= TORQUE_LIMIT:
                    tc[2].success(f"✅ OK ({val})")
                else:
                    tc[2].error(f"🚨 NG ({val} < {int(TORQUE_LIMIT)})")
            except ValueError:
                tc[2].warning("⚠ 숫자 입력 필요")

st.divider()

# ── ⑥ 수동 자동저장 버튼 ────────────────────────────────────
col_sv, _ = st.columns([1, 3])
if col_sv.button("💾 현재 상태 저장", use_container_width=True):
    ok = autosave_state(conn)
    st.session_state.autosave_msg = (
        f"✓ 수동저장 완료: {datetime.now().strftime('%H:%M:%S')}" if ok
        else "⚠ 저장 실패 — 네트워크 확인"
    )
    st.session_state.autosave_ok = ok
    st.rerun()

# ── ⑦ 최종 전송 ──────────────────────────────────────────────
# [Fix5] 중복 전송 방지
if st.session_state.submitted:
    st.success("✅ 이미 전송 완료된 작업일보입니다.")
    if st.button("🔄 새 작업 시작 (초기화)", type="secondary", use_container_width=True):
        keys_to_del = [k for k in st.session_state.keys()]
        for k in keys_to_del:
            del st.session_state[k]
        st.rerun()
else:
    if st.button("🚀 v8.1 최종 데이터 전송", type="primary", use_container_width=True):

        ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        curr_h = datetime.now().hour

        # ── 생산 데이터 수집 ──
        final_data = []
        for r in st.session_state.rows:
            p = st.session_state.get(f"p_{r['id']}", "선택")
            if p == "선택":
                continue

            uph     = PRODUCT_DB.get(p, 0)
            target  = round((uph / 60) * r['m']) if uph > 0 else 0
            actual  = st.session_state.get(f"a_{r['id']}", 0)
            def_qty = st.session_state.get(f"dq_{r['id']}", 0)

            issue_val = "NORMAL"
            if st.session_state.issue_state and curr_h == r['start_h']:
                issue_val = f"[CRITICAL] {st.session_state.issue_state}"

            final_data.append({
                "Timestamp":     ts,
                "Work_Date":     work_date.strftime("%Y-%m-%d"),
                "Worker_Name":   FIXED_WORKER,
                "Time_Slot":     r['time'],
                "Invested_Min":  r['m'],
                "Item_Name":     p,
                "Target_Qty":    target,
                "Actual_Qty":    actual,
                "Defect_Type":   st.session_state.get(f"dt_{r['id']}", "없음"),
                "Defect_Qty":    def_qty,
                "Defect_Reason": st.session_state.get(f"dr_{r['id']}", "없음"),
                "Downtime_Min":  st.session_state.get(f"dm_{r['id']}", 0),
                "Support_Worker":st.session_state.get(f"s_{r['id']}",  "없음"),
                "Model_LOT":     st.session_state.get(f"model_lot_{p}",""),
                "Issue_Status":  issue_val,
                "Attainment_Pct":round(actual / target * 100, 1) if target > 0 else 0,
                "Defect_Pct":    round(def_qty / actual * 100, 1) if actual > 0 else 0,
            })

        if not final_data:
            st.warning("⚠ 기종이 선택된 행이 없습니다. 최소 1개 이상 기종을 선택하세요.")
            st.stop()

        # ── BOM + 토크 데이터 수집 ──
        bom_row = {
            "Timestamp":   ts,
            "Work_Date":   work_date.strftime("%Y-%m-%d"),
            "Worker_Name": FIXED_WORKER,
        }
        for pt in BOM_PARTS:
            bom_row[f"BOM_{pt}_qty"] = st.session_state.get(f"q_{pt}", 0)
            bom_row[f"BOM_{pt}_lot"] = st.session_state.get(f"l_{pt}", "")
        for k in range(1, 6):
            tv = st.session_state.get(f"t_{k}", "")
            bom_row[f"Torque_{k}"] = tv
            try:
                v = float(str(tv).replace(',', '.'))
                bom_row[f"Torque_{k}_판정"] = "OK" if v >= TORQUE_LIMIT else "NG"
            except Exception:
                bom_row[f"Torque_{k}_판정"] = "미입력"

        # ── [Fix1] 안전한 전송 ──
        with st.spinner("구글 시트에 전송 중..."):
            ok1, err1 = safe_update(conn, MAIN_SHEET, final_data)
            ok2, err2 = safe_update(conn, BOM_SHEET,  [bom_row])

        if ok1 and ok2:
            st.session_state.submitted   = True
            st.session_state.issue_state = None
            # 임시저장 시트 비우기
            try:
                conn.update(worksheet=AUTOSAVE_SHEET, data=pd.DataFrame())
            except Exception:
                pass
            st.success(f"✅ v8.1 전송 완료! 생산 {len(final_data)}행 저장됨")
            st.balloons()
            st.rerun()

        elif ok1 and not ok2:
            # 생산 데이터는 성공, BOM만 실패 → 재시도 안내
            st.warning(
                f"⚠ 생산 데이터 저장 성공, BOM/토크 저장 실패\n"
                f"오류: {err2}\n"
                f"'현재 상태 저장' 후 BOM 탭만 재전송하세요."
            )
        else:
            # 생산 데이터 전송 실패 → 상세 오류 표시
            st.error(
                f"❌ 전송 실패\n"
                f"생산 데이터: {err1}\n"
                f"BOM 데이터: {err2}"
            )
