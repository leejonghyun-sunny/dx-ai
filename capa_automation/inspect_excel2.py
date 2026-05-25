import pandas as pd
import io

file_path = "capa_분석-09월_200828-R.XLS"
with open("inspect_output.txt", "w", encoding="utf-8") as f:
    try:
        xl = pd.ExcelFile(file_path)
        f.write(f"시트 목록: {xl.sheet_names}\n\n")
        for sheet in xl.sheet_names:
            f.write(f"=== 시트: {sheet} ===\n")
            # 엑셀은 보통 상단에 타이틀/병합셀이 있으므로 여러 줄을 읽습니다.
            df = pd.read_excel(file_path, sheet_name=sheet, nrows=15)
            f.write("상위 15개 행 미리보기:\n")
            f.write(df.to_string() + "\n")
            f.write("-" * 50 + "\n")
    except Exception as e:
        f.write(f"에러 발생: {e}\n")
