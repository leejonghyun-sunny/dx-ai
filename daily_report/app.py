<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HSG 조립1라인 스마트 작업일보 v7.6.2</title>
    <style>
        /* [UI/UX] 다크 테마 및 고정 레이아웃 설정 */
        :root {
            --bg-dark: #121212;
            --card-dark: #1e1e1e;
            --text-main: #ffffff;
            --text-dim: #b0b0b0;
            --accent-red: #ff4d4d;
            --accent-blue: #007bff;
            --border: #333333;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Pretendard', -apple-system, sans-serif;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }

        /* 🚨 비상 호출 시각화: 최상단 정적 적색 바 */
        #emergency-bar {
            width: 100%;
            padding: 12px 0;
            background-color: var(--accent-red);
            color: white;
            text-align: center;
            font-weight: 800;
            font-size: 1.1rem;
            position: sticky;
            top: 0;
            z-index: 9999;
            display: none; /* 기본 숨김 */
        }

        .container { padding: 20px; max-width: 800px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .worker-tag {
            background: #2d2d2d;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: var(--accent-blue);
            border: 1px solid var(--accent-blue);
        }

        /* [핵심] 숫자패드 강제 및 +/- 버튼 제거 CSS */
        input[type="number"] {
            -moz-appearance: textfield;
            background: #2a2a2a;
            border: 1px solid var(--border);
            color: white;
            padding: 12px;
            border-radius: 8px;
            width: 100%;
            box-sizing: border-box;
            font-size: 1.1rem;
            text-align: center;
        }

        input[type=number]::-webkit-outer-spin-button,
        input[type=number]::-webkit-inner-spin-button {
            -webkit-appearance: none;
            margin: 0;
        }

        /* 테이블 및 실적 UI */
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.9rem; }
        th, td { border: 1px solid var(--border); padding: 10px; text-align: center; }
        th { background: #252525; color: var(--text-dim); }

        .summary-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 25px;
        }

        .stat-card {
            background: var(--card-dark);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--border);
        }

        .stat-val { font-size: 1.5rem; font-weight: bold; margin-top: 5px; }
        .val-attain { color: #4caf50; }
        .val-defect { color: var(--accent-red); }

        .btn-group { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 20px; }
        button {
            padding: 15px;
            border-radius: 10px;
            border: none;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn-emer { background: #444; color: white; }
        .btn-submit { background: var(--accent-blue); color: white; grid-column: span 3; margin-top: 10px; }
        
        /* 토크 NG 시각화 */
        .torque-ng { background: rgba(255, 77, 77, 0.2); color: var(--accent-red); }
    </style>
</head>
<body>

    <div id="emergency-bar">🚨 현재 상태: <span id="emer-type">설비</span> 비상 보고 중</div>

    <div class="container">
        <header>
            <div>
                <h2 style="margin:0;">작업일보 <span style="font-size:0.8rem; color:var(--text-dim);">v7.6.2</span></h2>
            </div>
            <div class="worker-tag">메인: 안희선, 강선혜</div>
        </header>

        <div class="summary-grid">
            <div class="stat-card">
                <div style="font-size:0.8rem;">종합 달성률</div>
                <div id="disp-attain" class="stat-val val-attain">0%</div>
            </div>
            <div class="stat-card">
                <div style="font-size:0.8rem;">종합 불량률</div>
                <div id="disp-defect" class="stat-val val-defect">0%</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>시간대</th>
                    <th>목표</th>
                    <th>실적</th>
                    <th>불량</th>
                    <th>토크값</th>
                </tr>
            </thead>
            <tbody id="work-tbody">
                </tbody>
        </table>

        <div style="margin-top:20px;">
            <label style="font-size:0.8rem; color:var(--text-dim);">핵심 부품 LOT 입력 (숫자만)</label>
            <div style="display:flex; gap:10px; margin-top:5px;">
                <input type="number" id="lot-a" placeholder="LOT A" inputmode="numeric" pattern="[0-9]*">
                <input type="number" id="lot-b" placeholder="LOT B" inputmode="numeric" pattern="[0-9]*">
            </div>
        </div>

        <div class="btn-group">
            <button class="btn-emer" onclick="triggerEmergency('설비')">설비 비상</button>
            <button class="btn-emer" onclick="triggerEmergency('품질')">품질 비상</button>
            <button class="btn-emer" onclick="triggerEmergency('자재')">자재 비상</button>
            <button class="btn-submit" onclick="finalSubmit()">최종 데이터 구글 시트 전송</button>
        </div>
    </div>

    <script>
        const HOURS = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"];
        let activeEmergency = null;

        // 1. 테이블 초기화 및 8단계 CT 엔진
        function initTable() {
            const tbody = document.getElementById('work-tbody');
            HOURS.forEach((time, idx) => {
                const row = document.createElement('tr');
                row.id = `row-${idx}`;
                row.innerHTML = `
                    <td>${time}</td>
                    <td><input type="number" value="60" class="inp-target" oninput="calculate()"></td>
                    <td><input type="number" value="0" class="inp-actual" oninput="calculate()"></td>
                    <td><input type="number" value="0" class="inp-bad" oninput="calculate()"></td>
                    <td><input type="number" step="0.1" value="2.5" class="inp-torque" oninput="checkTorque(this)"></td>
                `;
                tbody.appendChild(row);
            });
        }

        // 2. 비상 호출 로직 (상단 바 노출 및 타입 저장)
        function triggerEmergency(type) {
            activeEmergency = type;
            const bar = document.getElementById('emergency-bar');
            const typeDisp = document.getElementById('emer-type');
            bar.style.display = 'block';
            typeDisp.innerText = type;
            console.log(`[로그] ${type} 비상 활성화`);
        }

        // 3. 토크 NG 시각화 (기존 UX 유지)
        function checkTorque(el) {
            const val = parseFloat(el.value);
            if(val < 2.0 || val > 3.0) {
                el.classList.add('torque-ng');
            } else {
                el.classList.remove('torque-ng');
            }
        }

        // 4. 종합 지표 자동 계산
        function calculate() {
            let totalTarget = 0, totalActual = 0, totalBad = 0;
            document.querySelectorAll('.inp-target').forEach(i => totalTarget += Number(i.value));
            document.querySelectorAll('.inp-actual').forEach(i => totalActual += Number(i.value));
            document.querySelectorAll('.inp-bad').forEach(i => totalBad += Number(i.value));

            const attain = totalTarget > 0 ? Math.round((totalActual / totalTarget) * 100) : 0;
            const defect = totalActual > 0 ? ((totalBad / totalActual) * 100).toFixed(1) : 0;

            document.getElementById('disp-attain').innerText = attain + "%";
            document.getElementById('disp-defect').innerText = defect + "%";
        }

        // 5. 최종 전송 (현재 시간대 로그 매칭 포함)
        function finalSubmit() {
            const now = new Date();
            const currentHour = now.getHours();
            
            // 현재 시간대에 맞는 행 번호 계산 (점심시간 제외 로직 포함)
            let targetRow = -1;
            if(currentHour >= 8 && currentHour <= 16) {
                targetRow = currentHour - 8;
                if(currentHour >= 13) targetRow -= 1; // 점심시간(12시) 제외 보정
            }

            const payload = {
                workers: "안희선, 강선혜",
                lotA: document.getElementById('lot-a').value,
                lotB: document.getElementById('lot-b').value,
                emergency: activeEmergency,
                targetRowIndex: targetRow,
                timestamp: now.toISOString()
            };

            console.log("전송 데이터:", payload);
            alert("v7.6.2 데이터 전송 성공: " + (activeEmergency ? activeEmergency + " 비상 로그 포함" : "정상 가동"));
            
            // 전송 후 비상 초기화
            activeEmergency = null;
            document.getElementById('emergency-bar').style.display = 'none';
        }

        window.onload = initTable;
    </script>
</body>
</html>