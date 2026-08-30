import subprocess

adb = r"C:\Users\Roshan Raj\AppData\Local\Android\Sdk\platform-tools\adb.exe"
device = "HNP06KSC"

xml = """<?xml version="1.0" encoding="utf-8" standalone="yes" ?>
<map>
    <string name="device_id">b444c073-6cac-44c9-ad64-9d057a3a646b</string>
    <string name="api_base_url">http://127.0.0.1:8000/</string>
</map>
"""

p = subprocess.Popen(
    [adb, "-s", device, "exec-out", "run-as", "com.olrac.signage", "sh", "-c", "mkdir -p shared_prefs && cat > shared_prefs/signage_prefs.xml"],
    stdin=subprocess.PIPE
)
p.communicate(input=xml.encode())

subprocess.run([adb, "-s", device, "shell", "am", "force-stop", "com.olrac.signage"])
subprocess.run([adb, "-s", device, "shell", "am", "start", "-n", "com.olrac.signage/.MainActivity"])
print("Configured tablet and launched app successfully!")
