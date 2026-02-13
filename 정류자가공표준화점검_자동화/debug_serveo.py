import subprocess
import time
import sys

def test_serveo():
    print("Testing Serveo connection...")
    cmd = [
        "ssh", 
        "-o", "StrictHostKeyChecking=no", 
        "-R", "80:localhost:8501", 
        "serveo.net"
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8'
    )
    
    start_time = time.time()
    while time.time() - start_time < 20:
        line = process.stdout.readline()
        if not line:
            break
        print(f"OUTPUT: {line.strip()}")
        if "serveo.net" in line and "https://" in line:
            print("SUCCESS: Found URL!")
            process.kill()
            return
            
    print("TIMEOUT or NO URL FOUND")
    process.kill()

if __name__ == "__main__":
    test_serveo()
