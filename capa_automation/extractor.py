# -*- coding: utf-8 -*-
"""
CAPA 분석 자동화 시스템 - 데이터 추출 및 정제 모듈 (Data Tier)
작성자: 데이터 아키텍트 (DataArchitect)
최초 작성일: 2026-05-25
설명: 최신 5월 CAPA 분석 엑셀 및 5월 생산계획서의 권선 라인(armature) 데이터를 정밀 파싱하고,
      수집 예외를 사전에 차단하는 Data Guard Harness 안전망이 결합된 최고 품질의 정제 엔진입니다.
"""

import os
import re
import sys
import logging
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import messagebox

# 디버깅을 위한 로깅 설정 (프로젝트 지침서 6.2 반영)
logging.basicConfig(
    filename="capa_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

def show_popup_alert(title: str, message: str):
    """
    수집 오류 또는 비정상적인 데이터 유입 시 사용자에게 GUI 경보 팝업을 발생시킵니다.
    비-GUI 환경을 대비하여 예외 처리가 가미되어 있습니다.
    """
    logging.warning(f"[경보 팝업 발생] {title}: {message}")
    try:
        root = tk.Tk()
        root.withdraw()  # 메인 Tk 윈도우 숨기기
        root.attributes("-topmost", True)  # 팝업창을 항상 맨 위에 노출
        messagebox.showerror(title, message)
        root.destroy()
    except Exception as e:
        # GUI를 지원하지 않는 터미널 환경 대비
        print(f"\n!!! [하네스 경보] {title} - {message} (팝업 호출 오류: {e}) !!!\n")


def data_guard_harness(df_raw: pd.DataFrame) -> bool:
    """
    [Data Guard Harness - 수집 보호망]
    원시 엑셀 로드 직후 데이터 아키텍처의 구조적 무결성과 밸류 경계값을 정밀 검증합니다.
    규격 불일치 혹은 유효 범위를 벗어날 시 에러를 유발하고 팝업 경보를 띄웁니다.
    """
    logging.info("[하네스 시스템] 권선 라인 원시 데이터 검증 가동 시작.")

    # 1. 헤더 위치 무결성 검증 (Header Integrity Check)
    try:
        # 3행(인덱스 3)의 컬럼 레이아웃 위치 검사
        st_header = df_raw.iloc[3, 6]
        eff_header = df_raw.iloc[3, 7]
        
        if st_header != 'ST':
            raise AssertionError(f"6번 열 헤더 불일치 (기대값: 'ST', 실제값: '{st_header}')")
        if eff_header not in ['효율', '가동률']:
            raise AssertionError(f"7번 열 헤더 불일치 (기대값: '효율' 또는 '가동률', 실제값: '{eff_header}')")
            
        logging.info("[하네스 시스템] 1단계: 헤더 위치 무결성 검증 통과.")
    except AssertionError as e:
        error_msg = f"엑셀 레이아웃 규격 불일치: {e}"
        show_popup_alert("하네스 경보 - Header", error_msg)
        raise ValueError(f"[하네스 경보 - Header] {error_msg}")

    # 2. 데이터 값 범위 검증 (Value Boundary Check)
    # 5행부터 시작하여 징검다리 홀수행 데이터 검증
    for idx in range(5, len(df_raw), 2):
        if idx >= len(df_raw):
            break
        row = df_raw.iloc[idx]
        
        pm_name = row[0]
        # 징검다리 공백 행 또는 합계 행 등 유효하지 않은 기종은 건너뜀
        if pd.isna(pm_name) or '합' in str(pm_name) and '계' in str(pm_name):
            continue
            
        pm_name = str(pm_name).strip()
        st_val = row[6]
        efficiency_val = row[7]
        
        # ST(표준 공수시간) 유효성 검사
        if pd.notna(st_val):
            try:
                st_float = float(st_val)
                if st_float <= 0:
                    error_msg = f"[{pm_name}] 기종의 ST 값이 0 이하입니다: {st_val}"
                    show_popup_alert("하네스 경보 - Value", error_msg)
                    raise ValueError(f"[하네스 경보 - Value] {error_msg}")
            except ValueError as ve:
                if "하네스 경보" in str(ve):
                    raise ve
                # 숫자가 아닌 문자열 유입 시 예외 처리
                error_msg = f"[{pm_name}] 기종의 ST 수치 변환 불가: {st_val}"
                show_popup_alert("하네스 경보 - Value", error_msg)
                raise ValueError(f"[하네스 경보 - Value] {error_msg}")
                
        # 가동률(효율) 유효성 검사 (0초과, 1.0이하 범위)
        if pd.notna(efficiency_val):
            try:
                eff_float = float(efficiency_val)
                if not (0.0 < eff_float <= 1.0):
                    error_msg = f"[{pm_name}] 기종의 가동률이 허용 범위를 초과했습니다 (값: {efficiency_val})"
                    show_popup_alert("하네스 경보 - Value", error_msg)
                    raise ValueError(f"[하네스 경보 - Value] {error_msg}")
            except ValueError as ve:
                if "하네스 경보" in str(ve):
                    raise ve
                error_msg = f"[{pm_name}] 기종의 가동률 수치 변환 불가: {efficiency_val}"
                show_popup_alert("하네스 경보 - Value", error_msg)
                raise ValueError(f"[하네스 경보 - Value] {error_msg}")

    logging.info("[하네스 시스템] 2단계: 데이터 범위 무결성 검증 통과.")
    print("[하네스 시스템] 권선 라인 원시 데이터 검증 통과 - 무결성 입증 완료.")
    return True


def extract_capa_master(file_path: str, sheet_name: str = "armature CAPA분석(09월)") -> tuple:
    """
    [마스터 데이터 추출 엔진]
    최신 CAPA 분석 파일의 대상 시트로부터 기종별 ST, 가동률, 정원 등의 정보를 정제하고,
    시트 내에 고정 상주하는 메타데이터(근무일수, 근무시간 등)를 딕셔너리로 추출합니다.
    """
    logging.info(f"CAPA 마스터 로드 시작: 파일={file_path}, 시트={sheet_name}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CAPA 파일이 존재하지 않습니다: {file_path}")
        
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    
    # Data Guard Harness 가동
    data_guard_harness(df_raw)
    
    # 0~2행 21~22열의 메타데이터(근무 기준정보) 파싱
    meta_info = {}
    try:
        meta_info['월근무일수'] = float(df_raw.iloc[0, 22])
        meta_info['월근무시간'] = float(df_raw.iloc[1, 22])
        meta_info['일근무시간'] = float(df_raw.iloc[2, 22])
        logging.info(f"메타데이터 파싱 성공: {meta_info}")
    except Exception as e:
        logging.warning(f"메타데이터 파싱 실패 (기본값 설정): {e}")
        meta_info = {'월근무일수': 22.0, '월근무시간': 225.5, '일근무시간': 10.25}

    # 기종별 유효 데이터 파싱 (5행부터 징검다리 홀수행만 정밀 추출)
    rows = []
    for idx in range(5, len(df_raw), 2):
        if idx >= len(df_raw):
            break
        row = df_raw.iloc[idx]
        
        pm_name = row[0]
        if pd.isna(pm_name):
            continue
            
        pm_name_str = str(pm_name).strip()
        # 합계 행 스킵
        if '합' in pm_name_str and '계' in pm_name_str:
            continue
            
        sales_plan = row[3]
        st = row[6]
        eff = row[7]
        operators = row[13]
        available_mhr = row[14]
        
        # 데이터 안전 변환 및 정밀성 보존 (결측치는 0.0 처리)
        sales_plan_clean = float(sales_plan) if pd.notna(sales_plan) else 0.0
        st_clean = float(st) if pd.notna(st) else 0.0
        eff_clean = float(eff) if pd.notna(eff) else 0.0
        operators_clean = float(operators) if pd.notna(operators) else 0.0
        available_mhr_clean = float(available_mhr) if pd.notna(available_mhr) else 0.0
        
        rows.append({
            "품명": pm_name_str,
            "계획수량": sales_plan_clean,
            "ST": st_clean,
            "가동률": eff_clean,
            "정원": operators_clean,
            "가용시간(M.hr)": available_mhr_clean
        })
        
    df_master = pd.DataFrame(rows)
    logging.info(f"CAPA 마스터 추출 완료. 총 {len(df_master)}개 품목 로드됨.")
    return df_master, meta_info


def extract_production_plan(file_path: str, sheet_name: str = "5월생산계획현황_R04") -> tuple:
    """
    [생산계획서 엇갈림 행 정밀 정제기]
    5월 생산계획서 내 지그재그 엇갈림 행(홀수행:자재코드/대표품명, 짝수행:기종 규명)을
    단일 행으로 완벽 병합하여 표준 '품명: 규격 (자재코드)' 형태로 결합하고,
    동적 발주 계획 수량(요구계획)을 긁어옵니다.
    """
    logging.info(f"생산계획서 로드 시작: 파일={file_path}, 시트={sheet_name}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"생산계획서 파일이 존재하지 않습니다: {file_path}")
        
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    
    # 0행 33열 등에서 근무일수 정보 추출
    plan_working_days = 18.0
    try:
        cell_val = df_raw.iloc[0, 33]
        if pd.notna(cell_val):
            match = re.search(r'(\d+)', str(cell_val))
            if match:
                plan_working_days = float(match.group(1))
        logging.info(f"생산계획서 근무일수 파싱 성공: {plan_working_days}일")
    except Exception as e:
        logging.warning(f"생산계획서 근무일수 파싱 실패: {e}")

    # 데이터 영역 순회 (9행부터 2행 간격으로 지그재그 파싱)
    rows = []
    for idx in range(9, len(df_raw), 2):
        if idx + 1 >= len(df_raw):
            break
        row_odd = df_raw.iloc[idx]
        row_even = df_raw.iloc[idx+1]
        
        # 1) 홀수행(대표 데이터 영역)
        company = row_odd[3]       # 업체명 (또는 대표품명)
        code = row_odd[4]          # CODE (자재코드)
        line_name = row_odd[6]     # 라인명
        req_plan = row_odd[7]      # 요구계획 수량
        
        # 2) 짝수행(상세 스펙 영역)
        spec = row_even[4]         # 세부 규격 (동일한 CODE 열의 짝수행 위치)
        
        # 자재코드와 스펙이 모두 결측치인 무의미 빈 행은 스킵
        if pd.isna(code) and pd.isna(spec):
            continue
            
        # 6행 헤더와 겹치는 정보이거나 텍스트 노이즈가 유입될 시 차단
        if code == 'CODE' or spec == 'CODE' or req_plan == '요구\n계획':
            continue
            
        company_str = str(company).strip() if pd.notna(company) else ""
        spec_str = str(spec).strip() if pd.notna(spec) else ""
        code_str = str(code).strip() if pd.notna(code) else ""
        line_name_str = str(line_name).strip() if pd.notna(line_name) else ""
        
        # 품명 병합 포맷 확정: '품명: 규격 (자재코드)'
        # 대표품명(업체명)이 비어있을 시 규격과 자재코드로만 구성
        if company_str:
            pm_merged = f"{company_str}: {spec_str} ({code_str})"
        else:
            pm_merged = f"{spec_str} ({code_str})"
            
        # 요구계획 발주수량 정밀 치환 및 안전 예외 가드
        try:
            req_plan_clean = float(req_plan) if pd.notna(req_plan) else 0.0
        except ValueError:
            req_plan_clean = 0.0
            
        rows.append({
            "품명": pm_merged,
            "계획수량": req_plan_clean,
            "라인명": line_name_str,
            "자재코드": code_str,
            "업체명": company_str,
            "세부규격": spec_str
        })
        
    df_plan = pd.DataFrame(rows)
    logging.info(f"생산계획서 파싱 완료. 총 {len(df_plan)}개 품목 로드됨.")
    return df_plan, {"계획근무일수": plan_working_days}


def extract_and_merge_winding_data(capa_file: str, plan_file: str) -> tuple:
    """
    [데이터 융합 메인 파이프라인]
    1. CAPA 분석 원본의 권선 마스터 데이터를 로드하여 Data Guard Harness 검증을 수행합니다.
    2. 5월 생산계획서의 지그재그 엇갈림 행을 정제하여 동적 계획수량 정보를 매칭합니다.
    3. 마스터 품명에 연동된 부분 매칭 키워드를 이용하여 생산계획서의 계획 수량을 지능적으로 합산·치환합니다.
    4. 최종 정제 및 규격화된 DataFrame['품명', '계획수량', 'ST', '가동률', '정원', '가용시간(M.hr)'] 및
       연산용 통합 메타데이터를 반환합니다.
    """
    # 1. 각각의 파일로부터 정밀 데이터 추출
    df_master, meta_capa = extract_capa_master(capa_file)
    df_plan, meta_plan = extract_production_plan(plan_file)
    
    # 2. 통합 결과 복제
    df_merged = df_master.copy()
    
    # 3. 마스터 품명별 지능형 매칭 매핑 사전 정의 (As-Is 마스터 ↔ To-Be 생산계획)
    keyword_map = {
        "태양 자동문": ["태양"],
        "RGC/RGI/153RG": ["RGC", "RGI", "153RG"],
        "태성 자동문": ["태성"],
        "신일자동문": ["신일"],
        "어스텝퍼드": ["어스텝퍼드", "어스텝", "A-STEP", "A_STEP"],
        "JS테크": ["JS테크", "JS"],
        "RSM(1/50)": ["RSM"],
        "덤프": ["덤프"],
        "동아특수": ["동아특수"]
    }
    
    logging.info("마스터 데이터와 생산계획 융합 매칭 시작.")
    
    for idx, row in df_merged.iterrows():
        pm = row["품명"]
        keywords = keyword_map.get(pm, [pm])
        
        matched_sum = 0.0
        has_match = False
        
        for kw in keywords:
            # 대소문자 무시 부분 매칭 조건 설정
            cond = df_plan["품명"].str.contains(kw, case=False, na=False)
            matched_df = df_plan[cond]
            if not matched_df.empty:
                matched_sum += matched_df["계획수량"].sum()
                has_match = True
                
        # 생산계획서에서 실제 계획수량이 매칭된 경우 수량을 동적으로 덮어씀
        if has_match:
            logging.info(f"매칭 성공 | 마스터 [{pm}] ➡️ 계획수량 {matched_sum}EA 치환 완료 (기존: {row['계획수량']}EA)")
            df_merged.at[idx, "계획수량"] = matched_sum
        else:
            logging.info(f"매칭 없음 | 마스터 [{pm}] ➡️ 생산계획 데이터 없음. 기존 원본 수량 유지 ({row['계획수량']}EA)")
            
    # 통합된 메타데이터 구성 (근무일수 변경 등 시뮬레이션을 위한 데이터 결합)
    combined_meta = {
        "마스터_근무일수": meta_capa.get("월근무일수", 22.0),
        "마스터_월근무시간": meta_capa.get("월근무시간", 225.5),
        "마스터_일근무시간": meta_capa.get("일근무시간", 10.25),
        "계획_근무일수": meta_plan.get("계획근무일수", 18.0)
    }
    
    logging.info("데이터 융합 메인 파이프라인 완벽 가동 완료.")
    return df_merged, combined_meta


if __name__ == "__main__":
    # 독립 실행 시 자체 테스트 및 검증 기능 작동 (Phase 2 확인용)
    print("=== [DataArchitect] extractor.py 독립 테스트 가동 ===")
    
    c_file = "CAPA 분석-26년 5월_Rev00_260427.xls"
    p_file = "5월_생산계획대비실적현황_REV04_0515.xlsx"
    
    try:
        final_df, final_meta = extract_and_merge_winding_data(c_file, p_file)
        print("\n[테스트 통과] 융합 데이터 세트 최종 결과:")
        print(final_df)
        print("\n통합 메타데이터:")
        print(final_meta)
    except Exception as ex:
        print(f"\n[테스트 실패] 데이터 추출 중 오류가 감지되었습니다: {ex}")
