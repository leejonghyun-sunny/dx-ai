# -*- coding: utf-8 -*-
"""
CAPA 분석 자동화 시스템 - 핵심 계산 모듈 (Logic Tier)
작성자: 로직 계산기 (LogicCalculator)
최초 작성일: 2026-05-25
설명: CAPA 7대 기본 수식을 정밀하게 연산하고, 
      이사님의 핵심 지침인 '추천 채용 인원수' 및 '일평균 권장 잔업 시간'을 역산합니다.
      입력값 검증을 위한 Boundary Guard Harness를 탑재하여 데이터 신뢰성을 보장합니다.
"""

import os
import math
import logging
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import messagebox

# 디버깅을 위한 로깅 설정 (프로젝트 지침서 준수)
logging.basicConfig(
    filename="capa_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

def show_popup_alert(title: str, message: str):
    """
    비정상 입력값이나 연산 오류 발생 시 사용자에게 GUI 경보 팝업을 발생시킵니다.
    비-GUI 환경을 대비하여 예외 처리를 포함합니다.
    """
    logging.warning(f"[계산기 경보 팝업] {title}: {message}")
    try:
        root = tk.Tk()
        root.withdraw()  # 메인 Tk 윈도우 숨기기
        root.attributes("-topmost", True)  # 팝업창을 항상 맨 위에 노출
        messagebox.showerror(title, message)
        root.destroy()
    except Exception as e:
        print(f"\n!!! [바운더리 가드 경보] {title} - {message} (팝업 호출 오류: {e}) !!!\n")


def boundary_guard_harness(df: pd.DataFrame) -> bool:
    """
    [Boundary Guard Harness - 입력 데이터 가드 장치]
    계산에 입력되는 데이터프레임의 모든 값을 검증하여 비정상 입력값을 원천 차단합니다.
    - ST(표준공수): 0 이하 검출 시 즉각 차단
    - 가동률: 1.0 초과 또는 0 이하 검출 시 즉각 차단
    - 계획수량, 정원: 음수 검출 시 즉각 차단
    """
    logging.info("[바운더리 가드] 입력 데이터 정밀 검증을 시작합니다.")
    
    for idx, row in df.iterrows():
        pm = row.get("품명", f"인덱스 {idx}")
        st = row.get("ST", 0.0)
        eff = row.get("가동률", 0.0)
        qty = row.get("계획수량", 0.0)
        operators = row.get("정원", 0.0)
        
        # 1. ST 검증 (ST <= 0)
        if st <= 0:
            error_msg = f"[{pm}] 기종의 ST(표준 공수시간)가 0 이하로 입력되었습니다 (값: {st}). ST는 0보다 커야 합니다."
            show_popup_alert("하네스 가드 - ST 오류", error_msg)
            raise ValueError(f"[BoundaryGuardError] {error_msg}")
            
        # 2. 가동률 검증 (0 초과 1.0 이하)
        if not (0.0 < eff <= 1.0):
            error_msg = f"[{pm}] 기종의 가동률이 허용 범위를 벗어났습니다 (값: {eff}). 가동률은 0.0 초과, 1.0 이하여야 합니다."
            show_popup_alert("하네스 가드 - 가동률 오류", error_msg)
            raise ValueError(f"[BoundaryGuardError] {error_msg}")
            
        # 3. 계획수량 검증 (음수 불가)
        if qty < 0:
            error_msg = f"[{pm}] 기종의 계획수량이 음수로 입력되었습니다 (값: {qty}). 0 이상이어야 합니다."
            show_popup_alert("하네스 가드 - 계획수량 오류", error_msg)
            raise ValueError(f"[BoundaryGuardError] {error_msg}")
            
        # 4. 정원 검증 (음수 불가)
        if operators < 0:
            error_msg = f"[{pm}] 기종의 현장 정원이 음수로 입력되었습니다 (값: {operators}). 0 이상이어야 합니다."
            show_popup_alert("하네스 가드 - 정원 오류", error_msg)
            raise ValueError(f"[BoundaryGuardError] {error_msg}")
            
    logging.info("[바운더리 가드] 입력 데이터의 완벽한 무결성이 검증되었습니다.")
    return True


def calculate_capa(
    df: pd.DataFrame, 
    meta_info: dict, 
    overrides: dict = None, 
    global_overrides: dict = None
) -> tuple:
    """
    [CAPA 분석 연산 및 시뮬레이션 엔진]
    
    1. 전역 변수(근무일수, 일근무시간) 및 개별 행(계획수량, 가동률, ST, 정원)의 오버라이드를 적용합니다 (What-If 시뮬레이션).
    2. 입력 데이터에 대해 Boundary Guard Harness 검증을 수행합니다.
    3. CAPA 7대 공식과 이사님의 피드백(채용 가이드, 잔업 시간 역산)을 벡터 연산으로 동적 연산합니다.
    4. 연산 완료된 DataFrame과 적용된 메타데이터를 반환합니다.
    
    [7대 기본 공식]
    - SPH = (3600 ÷ ST) × 가동률
    - 필요시간(M.hr) = 계획수량 ÷ SPH
    - 가용시간(M.hr) = 월근무시간 × 정원
    - 과부족(시간) = 가용시간(M.hr) - 필요시간(M.hr)
    - 과부족(인원) = 과부족(시간) ÷ 월근무시간
    - 과부족(수량) = 과부족(시간) × SPH
    - 과부족(일수) = 과부족(시간) ÷ 일근무시간
    
    [추가 피드백 공식]
    - 추천 추가 채용 인원 = ceil(abs(과부족(시간)) ÷ 월근무시간)  (부족한 경우에만 적용)
    - 일평균 권장 잔업 시간 = abs(과부족(시간)) ÷ (정원 × 월근무일수) (부족한 경우에만 적용)
    """
    logging.info("=== CAPA 로직 계산 가동 시작 ===")
    
    result_df = df.copy()
    
    # 1. 기본 근무조건 파싱 (생산계획서의 실제 계획_근무일수를 기본값으로 우선 반영)
    working_days = meta_info.get("계획_근무일수", meta_info.get("마스터_근무일수", 22.0))
    daily_hours = meta_info.get("마스터_일근무시간", 10.25)
    
    logging.debug(f"[초기 설정] 기본 근무일수: {working_days}일, 일근무시간: {daily_hours}시간")
    
    # 2. 전역 오버라이드(Global Overrides) 적용
    if global_overrides:
        logging.info(f"[시뮬레이션] 전역 변수 오버라이드 감지: {global_overrides}")
        working_days = global_overrides.get("월근무일수", working_days)
        daily_hours = global_overrides.get("일근무시간", daily_hours)
        
    monthly_hours = working_days * daily_hours
    logging.debug(f"[최종 적용] 적용 근무일수: {working_days}일, 적용 일근무시간: {daily_hours}시간, 월기본근무시간: {monthly_hours:.2f}시간")
    
    # 적용된 최종 메타데이터 구성
    applied_meta = {
        "적용_근무일수": working_days,
        "적용_일근무시간": daily_hours,
        "적용_월근무시간": monthly_hours
    }
    
    # 3. 개별 행 오버라이드(What-If Overrides) 적용
    if overrides:
        logging.info(f"[시뮬레이션] 개별 기종 오버라이드 감지: {overrides}")
        for key, changes in overrides.items():
            # 인덱스 번호(int) 기준 매칭
            if isinstance(key, int) and key in result_df.index:
                for col, val in changes.items():
                    if col in result_df.columns:
                        logging.debug(f"[오버라이드] 행 {key} ({result_df.at[key, '품명']}) 의 {col} 값을 {result_df.at[key, col]} -> {val} 로 변경")
                        result_df.at[key, col] = val
            # 품명(str) 기준 매칭
            elif isinstance(key, str):
                cond = result_df["품명"] == key
                if cond.any():
                    for col, val in changes.items():
                        if col in result_df.columns:
                            old_val = result_df.loc[cond, col].values[0]
                            logging.debug(f"[오버라이드] 기종 [{key}] 의 {col} 값을 {old_val} -> {val} 로 변경")
                            result_df.loc[cond, col] = val
                            
    # 4. Boundary Guard Harness 호출하여 입력값 정밀 검증
    boundary_guard_harness(result_df)
    
    # 5. 핵심 CAPA 공식 정밀 계산 (벡터화 연산)
    # SPH = (3600 ÷ ST) × 가동률
    result_df["SPH"] = (3600.0 / result_df["ST"]) * result_df["가동률"]
    
    # 필요시간(M.hr) = 계획수량 ÷ SPH (계획수량이 0이면 필요시간도 0)
    result_df["필요시간(M.hr)"] = np.where(
        result_df["계획수량"] > 0,
        result_df["계획수량"] / result_df["SPH"],
        0.0
    )
    
    # 가용시간(M.hr) = 월근무시간(월근무일수 * 일근무시간) × 정원
    result_df["가용시간(M.hr)"] = monthly_hours * result_df["정원"]
    
    # 과부족(시간) = 가용시간(M.hr) - 필요시간(M.hr)
    result_df["과부족(시간)"] = result_df["가용시간(M.hr)"] - result_df["필요시간(M.hr)"]
    
    # 과부족(인원) = 과부족(시간) ÷ 월근무시간
    result_df["과부족(인원)"] = result_df["과부족(시간)"] / monthly_hours
    
    # 과부족(수량) = 과부족(시간) × SPH
    result_df["과부족(수량)"] = result_df["과부족(시간)"] * result_df["SPH"]
    
    # 과부족(일수) = 과부족(시간) ÷ 일근무시간
    result_df["과부족(일수)"] = result_df["과부족(시간)"] / daily_hours
    
    # 6. 이사님 핵심 피드백 1: 추천 추가 임시직 채용 인원수 계산 (부족 시에만 올림 처리)
    def calc_hires(row):
        deficit = row["과부족(시간)"]
        if deficit < 0:
            # 절대값 부족 시간을 월 기본 근무시간으로 나누어 추천 인원 도출 (올림하여 정수화)
            return math.ceil(abs(deficit) / monthly_hours)
        return 0
        
    result_df["추천_추가채용인원(명)"] = result_df.apply(calc_hires, axis=1)
    
    # 7. 이사님 핵심 피드백 2: 일평균 필수 권장 잔업 시간 역산 (Zero Division Guard 장착)
    def calc_overtime(row):
        deficit = row["과부족(시간)"]
        ops = row["정원"]
        if deficit < 0 and ops > 0 and working_days > 0:
            # 부족 공수를 현원과 근무일수로 나누어 1인당 일평균 필요한 잔업 시간 역산
            return abs(deficit) / (ops * working_days)
        return 0.0
        
    result_df["일평균_권장잔업시간(시간)"] = result_df.apply(calc_overtime, axis=1)
    
    # 로그 파일에 중간 계산값 상세 기록 (프로젝트 지침서 6.2 준수)
    for idx, row in result_df.iterrows():
        logging.debug(
            f"품목: {row['품명']} | "
            f"계획수량: {row['계획수량']:.1f}EA | "
            f"ST: {row['ST']:.2f}초 | "
            f"가동률: {row['가동률']:.2f} | "
            f"정원: {row['정원']:.1f}명 | "
            f"SPH: {row['SPH']:.2f}EA/hr | "
            f"필요시간: {row['필요시간(M.hr)']:.2f}hr | "
            f"가용시간: {row['가용시간(M.hr)']:.2f}hr | "
            f"과부족시간: {row['과부족(시간)']:.2f}hr | "
            f"추천채용인원: {row['추천_추가채용인원(명)']}명 | "
            f"권장잔업시간: {row['일평균_권장잔업시간(시간)']:.2f}hr"
        )
        
    logging.info("=== CAPA 로직 계산 완수 ===")
    return result_df, applied_meta


if __name__ == "__main__":
    from extractor import extract_and_merge_winding_data
    
    c_file = "CAPA 분석-26년 5월_Rev00_260427.xls"
    p_file = "5월_생산계획대비실적현황_REV04_0515.xlsx"
    
    print("=== [LogicCalculator] 5월 권선 라인 CAPA 시뮬레이션 및 검증 ===")
    
    try:
        # 1. 데이터 추출 및 정제 (Phase 2 Data Tier 연동)
        df_raw, meta_info = extract_and_merge_winding_data(c_file, p_file)
        print("\n[성공] 1. 원시 데이터 및 엇갈림 생산계획 융합 완료.")
        print(f"통합 메타데이터: {meta_info}")
        
        # 2. 기본 시나리오 계산 (생산계획서 근무일수 18.0일 기준)
        print("\n[성공] 2. 기본 시나리오 CAPA 연산 가동 (근무일수 18.0일 적용)")
        df_base, meta_base = calculate_capa(df_raw, meta_info)
        
        # 결과 컬럼 선택 출력
        show_cols = [
            "품명", "계획수량", "정원", "필요시간(M.hr)", "가용시간(M.hr)", 
            "과부족(시간)", "추천_추가채용인원(명)", "일평균_권장잔업시간(시간)"
        ]
        print(df_base[show_cols].to_string(index=False))
        
        # 3. What-If 시뮬레이션 시나리오 1: 이사님의 잔업 대응 및 채용 시뮬레이션
        # 예를 들어, 특정 품목의 가동률 상향 및 계획수량 조정
        print("\n[성공] 3. What-If 시뮬레이션 시나리오 A: 태양 자동문 가동률 상향 (75% -> 85%) 및 RGC/RGI/153RG 계획수량 추가(0 -> 1000EA)")
        overrides = {
            "태양 자동문": {"가동률": 0.85},
            "RGC/RGI/153RG": {"계획수량": 1000.0}
        }
        df_simul_a, meta_simul_a = calculate_capa(df_raw, meta_info, overrides=overrides)
        print(df_simul_a[show_cols].to_string(index=False))
        
        # 4. What-If 시뮬레이션 시나리오 2: 근무 조건 조정 (전역 변수 변경)
        # 5월 생산 계획 근무일수가 18일인데, 마스터 기준 22일로 증일하여 특근을 진행할 경우 시나리오
        print("\n[성공] 4. What-If 시뮬레이션 시나리오 B: 근무일수 18일 -> 22일 증일 시 (특근 시나리오)")
        df_simul_b, meta_simul_b = calculate_capa(df_raw, meta_info, global_overrides={"월근무일수": 22.0})
        print(df_simul_b[show_cols].to_string(index=False))
        
        # 5. What-If 시뮬레이션 시나리오 C: 태양 자동문 계획수량 40,000EA로 폭주 시 (채용 및 잔업 가이드 작동)
        print("\n[성공] 5. What-If 시뮬레이션 시나리오 C: 태양 자동문 계획수량 40,000EA 폭주 시나리오 (채용 및 잔업 역산 가동)")
        overrides_c = {
            "태양 자동문": {"계획수량": 40000.0}
        }
        df_simul_c, meta_simul_c = calculate_capa(df_raw, meta_info, overrides=overrides_c)
        print(df_simul_c[show_cols].to_string(index=False))
        
        # 6. Boundary Guard Harness 오작동 검증 (ST <= 0 입력 시)
        print("\n[성공] 6. Boundary Guard Harness 강제 검증 테스트 (ST 0 이하 입력 시 팝업 및 중단)")
        broken_df = df_raw.copy()
        broken_df.at[0, "ST"] = -10.0  # 비정상 ST 주입
        try:
            calculate_capa(broken_df, meta_info)
        except ValueError as ve:
            print(f"-> [정상 작동] 가드 하네스가 정상적으로 차단했습니다: {ve}")
            
    except Exception as ex:
        print(f"\n[오류 발생] 시뮬레이션 도중 예외가 감지되었습니다: {ex}")
