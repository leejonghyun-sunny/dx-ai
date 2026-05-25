import pandas as pd
import sys

file_path = "capa_분석-09월_200828-R.XLS"

try:
    print(f"[{file_path}] 파일 분석 중...\n")
    
    # 엑셀 파일 로드 (모든 시트)
    xl = pd.ExcelFile(file_path)
    print(f"시트 목록: {xl.sheet_names}\n")
    
    for sheet in xl.sheet_names:
        print(f"=== 시트: {sheet} ===")
        df = pd.read_excel(file_path, sheet_name=sheet, nrows=5)
        print("컬럼 목록:")
        print(df.columns.tolist())
        print("상위 5개 데이터 미리보기:")
        print(df.head())
        print("-" * 50)
        
except Exception as e:
    print(f"에러 발생: {e}")
