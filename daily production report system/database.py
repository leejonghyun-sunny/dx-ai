import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_NAME = "production_data.db"

def get_db_connection():
    """데이터베이스 연결을 반환합니다."""
    # DB 파일 경로 설정 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, DB_NAME)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 결과를 딕셔너리처럼 접근할 수 있게 해줍니다.
    return conn

def init_db():
    """초기 테이블을 생성합니다."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. 기종 및 UPH 정보 마스터 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS Product_Master (
            product_code TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            target_uph INTEGER NOT NULL
        )
    ''')
    
    # 기본 기종 데이터 입력 (데이터가 없을 때만)
    c.execute("SELECT COUNT(*) FROM Product_Master")
    if c.fetchone()[0] == 0:
        default_products = [
            ("DC-50", "DC 자동문(50분)", 50),
            ("DC-60", "DC 자동문(60분)", 60),
            ("DC-70", "DC 자동문(70분)", 70)
        ]
        c.executemany("INSERT INTO Product_Master VALUES (?, ?, ?)", default_products)
    
    # 2. 일일 생산 실적 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS Production_Record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,     -- 작업일 (예: 2026-02-23)
            line_name TEXT NOT NULL,     -- 라인명
            worker_name TEXT NOT NULL,   -- 작업자
            product_code TEXT NOT NULL,  -- 기종 코드
            time_slot TEXT NOT NULL,     -- 시간대 (예: 08:00~09:00)
            target_qty INTEGER NOT NULL, -- 목표수량(UPH)
            actual_qty INTEGER DEFAULT 0,-- 생산수량
            defect_qty INTEGER DEFAULT 0,-- 불량수량
            remarks TEXT,                -- 특이사항/점검내용
            UNIQUE(work_date, line_name, time_slot) -- 동일 날짜, 라인, 시간대에 중복 행 방지
        )
    ''')
    
    conn.commit()
    conn.close()

def get_product_list():
    """마스터 테이블에서 기종 정보를 딕셔너리 형태로 불러옵니다."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM Product_Master")
    rows = c.fetchall()
    conn.close()
    
    product_dict = {}
    for row in rows:
        product_dict[row['product_code']] = {
            "name": row['product_name'],
            "uph": row['target_uph']
        }
    return product_dict

def create_hourly_slots(work_date, line_name, product_code, worker_name, target_uph):
    """
    선택된 기종과 작업 정보를 바탕으로 08:00부터 17:00까지 시간대별 빈 슬롯을 자동 생성합니다.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # 생성할 시간대 리스트 (08시부터 17시까지 1시간 간격)
    time_slots = [f"{str(i).zfill(2)}:00~{str(i+1).zfill(2)}:00" for i in range(8, 17)]
    # 점심시간 12:00~13:00은 생산 제외 또는 특수 슬롯으로 처리할 수 있으나, 일단 모두 생성
    
    success_count = 0
    for slot in time_slots:
        try:
            c.execute('''
                INSERT INTO Production_Record 
                (work_date, line_name, worker_name, product_code, time_slot, target_qty, actual_qty, defect_qty)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            ''', (work_date, line_name, worker_name, product_code, slot, target_uph))
            success_count += 1
        except sqlite3.IntegrityError:
            # UNIQUE 제약조건 때문에 이미 해당 슬롯이 존재하면 무시 (중복 생성 방지)
            pass
            
    conn.commit()
    conn.close()
    return success_count

def get_daily_records(work_date, line_name):
    """특정 날짜, 라인의 생산 실적을 Pandas DataFrame으로 불러옵니다. 대시보드 출력용"""
    conn = get_db_connection()
    query = '''
        SELECT 
            time_slot AS "시간대",
            product_code AS "기종코드",
            worker_name AS "작업자",
            target_qty AS "목표수량",
            actual_qty AS "생산수량",
            defect_qty AS "불량수량",
            remarks AS "비고/특이사항"
        FROM Production_Record
        WHERE work_date = ? AND line_name = ?
        ORDER BY time_slot
    '''
    df = pd.read_sql_query(query, conn, params=(work_date, line_name))
    conn.close()
    return df

# 모듈이 직접 실행될 때 (테스트용)
if __name__ == "__main__":
    init_db()
    print("DB 초기화 완료 및 Product_Master 데이터 확인 세팅됨")
