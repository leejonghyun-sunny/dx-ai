# -*- coding: utf-8 -*-
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

file_path = "CAPA 분석-26년 5월_Rev00_260427.xls"
sheet_name = "armature CAPA분석(09월)"

try:
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    print(f"=== {sheet_name} 전체 크기: {df_raw.shape} ===")
    
    # 0행부터 30행까지, 0열부터 25열까지 상세 출력
    for r in range(min(50, len(df_raw))):
        row_vals = []
        for c in range(df_raw.shape[1]):
            val = df_raw.iloc[r, c]
            row_vals.append(f"{c}:{val}")
        print(f"Row {r:02d}: " + " | ".join(row_vals[:20])) # 20열까지만 출력
except Exception as e:
    print(f"에러 발생: {e}")
