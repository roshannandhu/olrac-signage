import subprocess, time

adb = r"C:\Users\Roshan Raj\AppData\Local\Android\Sdk\platform-tools\adb.exe"
device = "HNP06KSC"

def shell(*args):
    subprocess.run([adb, "-s", device, "shell"] + list(args))

# Hide keyboard initially
shell("input", "keyevent", "111")
time.sleep(0.5)

# Step 1: Tap Email/Username field
shell("input", "tap", "400", "260")
time.sleep(0.4)
shell("input", "keyevent", "123") # MOVE_END
for _ in range(35):
    shell("input", "keyevent", "67") # Backspace
shell("input", "text", "admin")
time.sleep(0.4)

# Hide keyboard
shell("input", "keyevent", "111")
time.sleep(0.4)

# Step 2: Tap Password field
shell("input", "tap", "400", "350")
time.sleep(0.4)
shell("input", "keyevent", "123")
for _ in range(35):
    shell("input", "keyevent", "67")
shell("input", "text", "Roshan@1100")
time.sleep(0.4)

# Hide keyboard
shell("input", "keyevent", "111")
time.sleep(0.4)

# Step 3: Tap Screen Name field
shell("input", "tap", "400", "440")
time.sleep(0.4)
shell("input", "keyevent", "123")
for _ in range(35):
    shell("input", "keyevent", "67")
shell("input", "text", "LenovoTablet1")
time.sleep(0.4)

# Hide keyboard
shell("input", "keyevent", "111")
time.sleep(0.5)

# Step 4: Tap Link Screen to Workspace Button
shell("input", "tap", "400", "525")
time.sleep(3.0)

print("Step-by-step sign-in submitted!")
