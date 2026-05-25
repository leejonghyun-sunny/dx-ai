# -*- coding: utf-8 -*-
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# 파이썬 엔진 가져오기
from extractor import extract_capa_master
from calculator import calculate_capa

c_file = "CAPA 분석-26년 5월_Rev00_260427.xls"

try:
    # 1. 엑셀 원본 데이터 직접 로드 (검증용)
    df_raw_excel = pd.read_excel(c_file, sheet_name="armature CAPA분석(09월)", header=None)
    
    # 2. 파이썬 마스터 데이터 로드 (수량 치환 없이 원본 그대로 사용)
    df_master, meta_info = extract_capa_master(c_file)
    
    # 파이썬 계산 실행 (근무조건은 마스터 데이터의 월근무일수 22.0일 기준으로 설정)
    # meta_info는 {'월근무일수': 22.0, '월근무시간': 225.5, '일근무시간': 10.25} 로 되어 있음
    # calculate_capa가 기본적으로 meta_info의 계획_근무일수를 쓰므로 강제로 마스터 값으로 지정
    meta_for_calc = {
        "계획_근무일수": meta_info["월근무일수"],
        "마스터_근무일수": meta_info["월근무일수"],
        "마스터_일근무시간": meta_info["일근무시간"],
    }
    
    df_calc, applied_meta = calculate_capa(df_master, meta_for_calc)
    
    print("=== 기종별 1:1 비교 대조 ===")
    
    # 5행부터 징검다리 홀수행에 있는 기종 정보 파싱
    for idx, row in df_calc.iterrows():
        excel_row_idx = 5 + idx * 2
        pm_name = row["품명"]
        
        # 엑셀 원본 셀 값 추출
        excel_qty = df_raw_excel.iloc[excel_row_idx, 3] # 판매계획
        excel_st = df_raw_excel.iloc[excel_row_idx, 6] # ST
        excel_eff = df_raw_excel.iloc[excel_row_idx, 7] # 효율(가동률)
        excel_sph = df_raw_excel.iloc[excel_row_idx, 8] # SPH
        excel_avail_mhr = df_raw_excel.iloc[excel_row_idx, 14] # 생산가능 공수(M.hr) M.hr
        excel_need_hours = df_raw_excel.iloc[excel_row_idx, 15] # 필요 공수(M.hr) 시간
        excel_need_mhr = df_raw_excel.iloc[excel_row_idx, 17] # 필요 공수(M.hr) M.hr
        excel_deficit_hours = df_raw_excel.iloc[excel_row_idx, 18] # 과부족 공수(M.hr) 시간
        
        # 파이썬 계산 결과
        py_qty = row["계획수량"]
        py_st = row["ST"]
        py_eff = row["가동률"]
        py_sph = row["SPH"]
        py_avail_mhr = row["가용시간(M.hr)"]
        py_need_hours = row["필요시간(M.hr)"]
        py_deficit_hours = row["과부족(시간)"]
        
        print(f"\n[기종: {pm_name}]")
        print(f"  - 계획수량 : 엑셀={excel_qty} | 파이썬={py_qty}")
        print(f"  - ST       : 엑셀={excel_st} | 파이썬={py_st}")
        print(f"  - 가동률   : 엑셀={excel_eff} | 파이썬={py_eff}")
        print(f"  - SPH      : 엑셀={excel_sph:.6f} | 파이썬={py_sph:.6f} | 차이={abs(excel_sph - py_sph):.6f}")
        print(f"  - 가용시간 : 엑셀={excel_avail_mhr:.6f} | 파이썬={py_avail_mhr:.6f} | 차이={abs(excel_avail_mhr - py_avail_mhr):.6f}")
        print(f"  - 필요공수 : 엑셀={excel_need_hours:.6f} | 파이썬={py_need_hours:.6f} | 차이={abs(excel_need_hours - py_need_hours):.6f}")
        print(f"  - 과부족공수: 엑셀={excel_deficit_hours:.6f} | 파이썬={py_deficit_hours:.6f} | 차이={abs(excel_deficit_hours - py_deficit_hours):.6f}")
        
except Exception as e:
    print(f"에러 발생: {e}")
