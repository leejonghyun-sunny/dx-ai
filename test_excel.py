import pandas as pd
import datetime
import os

LOG_FILE = "inspection_logs.csv"

# Function to simulate saving log with quality data
def save_log(date, user, freq, rpm, tension, cut_sec, depth, bite, roundness, step, result):
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Date", "User", "Freq", "RPM", "Tension", "Cut_Sec", "Depth", "Bite", "Roundness", "Step", "Result", "Timestamp"])
        df.to_csv(LOG_FILE, index=False)
    
    new_data = pd.DataFrame({
        "Date": [date],
        "User": [user],
        "Freq": [freq],
        "RPM": [rpm],
        "Tension": [tension],
        "Cut_Sec": [cut_sec],
        "Depth": [depth],
        "Bite": [bite],
        "Roundness": [roundness],
        "Step": [step],
        "Result": [result],
        "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    })
    new_data.to_csv(LOG_FILE, mode='a', header=False, index=False)
    print(f"Data saved to {LOG_FILE}")

# Test Execution
try:
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE) # Clean up before test
        
    today = datetime.date.today()
    # Save a test record with quality data
    save_log(today, "ExcelTester", 30.0, 1860, 2.70, 16.0, 0.03, "Middle-Lower", 1.5, 0.5, "PASS")
    
    # Read and Export to Excel
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        excel_file = f"test_export_{today}.xlsx"
        
        # Simulate Streamlit download button logic (writing to buffer/file)
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            
        if os.path.exists(excel_file):
            print(f"SUCCESS: Excel file '{excel_file}' created.")
        else:
            print("FAILURE: Excel file not created.")
    else:
        print("FAILURE: Log file not created.")
        
except Exception as e:
    print(f"ERROR: {e}")
