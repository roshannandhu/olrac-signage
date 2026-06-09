# Olrac Signage TV Wrapper

This is a minimal Android TV kiosk wrapper that hosts the Olrac Signage TV web app in a fullscreen `WebView`. It's built for Android TV / Fire TV devices.

## Features
- Fullscreen immersive mode (hides system bars).
- Screen Wake Lock (keeps the TV screen on indefinitely).
- Autoplay allowed for HTML5 `<video>` elements.
- Auto-starts on boot.
- Auto-reconnects and reloads when network is restored.
- Hardware back-button is disabled to prevent exiting the kiosk.

## Building and Running
1. Open this folder (`android-tv`) in Android Studio.
2. In `gradle.properties`, set `TV_URL` to the URL where your Vite TV app is hosted (e.g., `https://tv.olrac.example.com`).
3. Build the APK via `Build > Build Bundle(s) / APK(s) > Build APK(s)`.

## Sideloading
1. Enable Developer Options and USB Debugging on your Android TV.
2. Connect to your TV via ADB:
   ```bash
   adb connect <TV_IP_ADDRESS>
   ```
3. Install the APK:
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

## KIOSK Lock Instructions
To prevent users from navigating away to the regular Android TV home screen, you have two options:

### Option 1: Set as Home App (Easiest)
When you press the "Home" button on the TV remote after installing, the system will ask you to choose a Home app. Select **Olrac Signage TV** and set it to **"Always"**.

### Option 2: Disable the Stock Launcher via ADB
If you have ADB access, you can completely disable the stock Android TV launcher:
```bash
# Disable
adb shell pm disable-user --user 0 com.google.android.tvlauncher

# Re-enable if needed
adb shell pm enable com.google.android.tvlauncher
```

### Option 3: Screen Pinning / Lock Task (MDM)
If deploying via an MDM (Mobile Device Management) tool, you can set the app to Lock Task mode.
