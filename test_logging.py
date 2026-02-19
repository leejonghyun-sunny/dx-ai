import pandas as pd
import os
import datetime

LOG_FILE = "inspection_logs.csv"

# Function from app.py
def save_log(date, user, freq, rpm, tension, cut_sec, depth, bite, result):
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Date", "User", "Freq", "RPM", "Tension", "Cut_Sec", "Depth", "Bite", "Result", "Timestamp"])
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
    save_log(today, "Tester", 30.0, 1860, 2.70, 16.0, 0.03, "Middle-Lower", "PASS")
    
    # Verify
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        print("CSV Content:")
        print(df)
        if len(df) == 1 and df.iloc[0]['User'] == "Tester":
            print("SUCCESS: Log file created and data verified.")
        else:
            print("FAILURE: Data mismatch.")
    else:
        print("FAILURE: Log file not created.")
        
except Exception as e:
    print(f"ERROR: {e}")
