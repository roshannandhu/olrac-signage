#!/bin/bash
# Android TV Emulator Validation Script
# Usage: run from the repository root -> bash scripts/validation_script.sh

echo "=========================================="
echo "Phase 3B: Android TV Emulator Validation"
echo "=========================================="

echo "Checking for attached devices..."
adb devices

echo "Installing APK..."
adb install -r "android-tv/app/build/outputs/apk/debug/app-debug.apk"

echo "Launching App..."
adb shell am start -n com.olrac.signage/.MainActivity

echo "Validating BootReceiver..."
echo "Sending ACTION_BOOT_COMPLETED broadcast..."
adb shell am broadcast -a android.intent.action.BOOT_COMPLETED -p com.olrac.signage

echo "=========================================="
echo "Please verify on the Emulator UI:"
echo "1. The app automatically launched."
echo "2. The pairing code is displayed."
echo "3. Caching and playback are working when disconnected from internet."
echo "=========================================="
