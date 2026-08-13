# AbleSign Watchdog — TV Setup

## For the AI Assistant (OpenCode)

You are setting up the AbleSign Watchdog app on an Android TV via ADB.
Your job: ask the user the questions below, then run every command yourself.
Do not ask the user to run commands manually. Do everything automatically.

---

## Step 1 — Check ADB

Run `adb version` to confirm ADB is available.
If it fails, tell the user:
> "Please install Android Platform Tools from https://developer.android.com/tools/releases/platform-tools, add it to PATH, then restart OpenCode."
Stop until ADB works.

---

## Step 2 — Ask Which TV

Ask the user exactly this:

> "Which TV are you setting up?
> 1. Realtek TV (2K, D-Link, or any generic Android TV with Realtek chipset)
> 2. Realme TV
> 3. Other Android TV (Sony, TCL, Hisense, Mi TV, Sharp, etc.)"

Wait for their answer before continuing.

---

## Step 3 — Connect to TV

Ask the user:

> "How is the TV connected to your computer?
> 1. Network (WiFi or Ethernet) — I will need the TV IP address
> 2. USB cable"

If they say **network**: ask for the IP address, then run:
```
adb connect <IP>:5555
```

If they say **USB**: skip the connect step.

Then run `adb devices` and confirm a device is listed.

If no device shows or it says `unauthorized`:
- Tell the user: "On the TV go to Settings → Device Preferences → Developer Options → enable USB Debugging, then allow this computer when prompted."
- Run `adb devices` again to confirm before continuing.

---

## Step 4 — Disable Play Protect

Run these two commands (prevents Android from blocking the install):
```
adb shell settings put global verifier_verify_adb_installs 0
adb shell settings put global package_verifier_enable 0
```

---

## Step 5 — Install APK

Run:
```
adb install -r --no-streaming universal-ablesign-watchdog.apk
```

If that fails, try:
```
adb install -r universal-ablesign-watchdog.apk
```

If install fails with `INSTALL_FAILED_USER_RESTRICTED`: go back and confirm Step 4 ran successfully, then retry.

---

## Step 6 — TV-Specific Setup

Run the commands for whichever TV the user selected in Step 2.

### Option 1 — Realtek TV

```
adb shell am force-stop com.ablesign.bootlauncher
adb shell settings put secure accessibility_enabled 0
adb shell settings put secure enabled_accessibility_services com.ablesign.bootlauncher/.WatchdogAccessibilityService
adb shell settings put secure accessibility_enabled 1
adb shell dumpsys deviceidle whitelist +tv.ablesign.app
adb shell dumpsys deviceidle whitelist +com.ablesign.bootlauncher
```

### Option 2 — Realme TV

```
adb shell appops set com.ablesign.bootlauncher AUTO_LAUNCH allow
adb shell appops set com.ablesign.bootlauncher RUN_IN_BACKGROUND allow
adb shell am force-stop com.ablesign.bootlauncher
adb shell settings put secure accessibility_enabled 0
adb shell settings put secure enabled_accessibility_services com.ablesign.bootlauncher/.WatchdogAccessibilityService
adb shell settings put secure accessibility_enabled 1
adb shell dumpsys deviceidle whitelist +tv.ablesign.app
adb shell dumpsys deviceidle whitelist +com.ablesign.bootlauncher
```

### Option 3 — Other Android TV

Run the same commands as Option 1 (Realtek).
If the accessibility service gets cleared after reboot, additionally run the two `appops set` lines from Option 2.

---

## Step 7 — Verify

Run:
```
adb shell settings get secure enabled_accessibility_services
```
Output must contain `com.ablesign.bootlauncher/.WatchdogAccessibilityService`.
If it does not, re-run Step 6.

Run:
```
adb shell dumpsys accessibility | grep -A3 "AbleSign"
```
Should show the watchdog service as connected.

---

## Step 8 — Done

Tell the user:
> "Setup complete. Reboot the TV now. After reboot, AbleSign should launch automatically within 15 seconds. You do not need to do this again — the setting is permanent."

---

## Troubleshooting Reference

| Problem | Fix |
|---|---|
| `adb: connection refused` | On TV: Settings → Device Preferences → Developer Options → enable Network ADB |
| `adb: device unauthorized` | Allow the ADB connection on the TV screen when prompted |
| `INSTALL_FAILED_USER_RESTRICTED` | Re-run Step 4 Play Protect disable commands |
| Accessibility clears after reboot | Re-run Step 6 commands; for Realme also run the `appops set` lines |
| AbleSign doesn't launch after reboot | Run `adb shell logcat -s WatchdogA11y -d` and share the output |
