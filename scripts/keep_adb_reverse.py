import subprocess
import time

def main():
    adb = r"C:\Users\Roshan Raj\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    print("Setting up ADB Reverse...")
    while True:
        try:
            res = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=5)
            if "HNP06KSC" in res.stdout:
                rev = subprocess.run([adb, "-s", "HNP06KSC", "reverse", "--list"], capture_output=True, text=True, timeout=5)
                if "tcp:8000" not in rev.stdout:
                    subprocess.run([adb, "-s", "HNP06KSC", "reverse", "tcp:8000", "tcp:8000"], capture_output=True, text=True, timeout=5)
                    print(f"[{time.strftime('%X')}] Set adb reverse tcp:8000 tcp:8000")
        except Exception as e:
            print(f"[{time.strftime('%X')}] ADB reverse error: {e}")
        time.sleep(15)

if __name__ == "__main__":
    main()
