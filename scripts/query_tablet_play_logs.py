import subprocess

adb = r"C:\Users\Roshan Raj\AppData\Local\Android\Sdk\platform-tools\adb.exe"

def main():
    cmd = [
        adb, "shell",
        "run-as com.olrac.signage sqlite3 databases/signage_database 'SELECT count(*) FROM play_events;'"
    ]
    out = subprocess.check_output(cmd)
    print("Tablet SQLite play_events count:")
    print(out.decode().strip())

if __name__ == "__main__":
    main()
