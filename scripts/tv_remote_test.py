"""
Drive the setup gate on a real TV with a real remote, and say whether it works.

This is the half of the gate fix that cannot be proved off-device. The JVM tests cover
Compose's focus system, but the thing that actually broke -- keys arriving from the OS into
the Activity, ahead of the buttons -- only exists on hardware. This script performs the
presses an installer would, reads the screen back through uiautomator, and checks the four
things that have to be true:

  1. The gate is up and SOMETHING has focus (nothing focused is the original bug: a D-pad
     has nowhere to move from nowhere, so every key is dropped).
  2. Down travels to the other row, and Up comes back.
  3. Up-Up-Down-Down-OK reaches the maintenance pin prompt. This one is the way out if the
     gate ever strands a TV, so it matters more than it looks.
  4. It gets back to where it started, leaving the TV as it was found.

Usage:
    python scripts/tv_remote_test.py --apk path/to/app-production-release.apk
    python scripts/tv_remote_test.py --serial HNP06KSC          # test what is installed
    python scripts/tv_remote_test.py --adb "C:/.../platform-tools/adb.exe"

Nothing here uninstalls or factory-resets: it installs with -r, which keeps the pairing. An
APK signed with a different key cannot replace the installed one -- Android refuses it -- and
that failure is reported as itself rather than as a broken remote.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PACKAGE = "com.olrac.signage"
GATE_MARKER = "Two switches to turn on"
PIN_MARKER = "Maintenance access"

KEY_UP, KEY_DOWN, KEY_OK, KEY_BACK = "19", "20", "23", "4"


class Adb:
    def __init__(self, adb: str, serial: str | None):
        self.base = [adb] + (["-s", serial] if serial else [])

    def run(self, *args: str, timeout: int = 30) -> str:
        res = subprocess.run(
            self.base + list(args), capture_output=True, text=True, timeout=timeout
        )
        if res.returncode != 0:
            raise RuntimeError(f"adb {' '.join(args)} failed:\n{res.stderr.strip()}")
        return res.stdout

    def shell(self, *args: str, timeout: int = 30) -> str:
        return self.run("shell", *args, timeout=timeout)

    def key(self, code: str) -> None:
        self.shell("input", "keyevent", code)
        time.sleep(0.4)          # let the focus move and the frame settle

    def ui(self) -> ET.Element:
        """The current screen, as uiautomator sees it."""
        for attempt in range(3):
            try:
                self.shell("uiautomator", "dump", "/sdcard/ui.xml", timeout=40)
                return ET.fromstring(self.run("exec-out", "cat", "/sdcard/ui.xml"))
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1.0)
        raise RuntimeError("unreachable")


def texts(root: ET.Element) -> list[str]:
    return [n.get("text", "") for n in root.iter("node") if n.get("text")]


def focused_label(root: ET.Element) -> str | None:
    """The text of whatever currently holds focus, or None if nothing does."""
    for node in root.iter("node"):
        if node.get("focused") == "true":
            label = node.get("text") or node.get("content-desc") or ""
            if label:
                return label
            # Compose reports focus on the clickable node; fall back to its bounds so two
            # unlabelled rows can still be told apart.
            return f"<node at {node.get('bounds')}>"
    return None


def installed_version(adb: "Adb") -> str:
    """versionName as the device reports it, so a run is pinned to a known build."""
    match = re.search(r"versionName=(\S+)", adb.shell("dumpsys", "package", PACKAGE))
    return match.group(1) if match else "unknown"


def on_screen(root: ET.Element, marker: str) -> bool:
    return any(marker.lower() in t.lower() for t in texts(root))


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print(f"        {detail}")
        if not ok:
            self.failures.append(name)
        return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adb", default="adb", help="path to adb (default: adb on PATH)")
    ap.add_argument("--serial", default=None, help="device serial, if more than one")
    ap.add_argument("--apk", default=None, help="APK to install first; omit to test as-is")
    args = ap.parse_args()

    adb = Adb(args.adb, args.serial)
    report = Report()

    try:
        devices = adb.run("devices")
    except Exception as exc:
        print(f"Cannot reach adb: {exc}")
        return 2
    online = [l for l in devices.splitlines()[1:] if l.strip().endswith("device")]
    if not online:
        print("No device. Connect the TV (adb connect <ip> for a networked one) and retry.")
        print(devices)
        return 2
    print(f"Device: {online[0].split()[0]}")

    if args.apk:
        print(f"\nInstalling {args.apk} ...")
        try:
            out = adb.run("install", "-r", args.apk, timeout=300)
            print(f"  {out.strip().splitlines()[-1] if out.strip() else 'installed'}")
        except RuntimeError as exc:
            msg = str(exc)
            if "SIGNATURES" in msg.upper() or "signatures do not match" in msg.lower():
                print("\n  Install refused: this APK is signed with a different key than the")
                print("  one already on the TV. Build it with android-tv/keystore.properties")
                print("  in place -- without it the release build silently falls back to")
                print("  debug signing. Nothing was changed on the device.")
                return 2
            print(f"\n  Install failed: {msg}")
            return 2

    print("\nLaunching ...")
    adb.shell("monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(6)

    print(f"\nVersion on device: {installed_version(adb)}")

    root = adb.ui()
    if not on_screen(root, GATE_MARKER):
        print("\nThe setup gate is not showing. Either both switches are already on (so the")
        print("gate correctly closed itself), or the app is elsewhere. Screen text:")
        for t in texts(root)[:12]:
            print(f"    {t!r}")
        return 3

    print("\nGate is up. Testing the remote:\n")

    first = focused_label(root)
    report.check(first is not None,
                 "something has focus when the gate opens",
                 f"focused: {first!r}" if first else "NOTHING focused -- the D-pad has "
                                                    "nowhere to move from; this is the bug")

    adb.key(KEY_DOWN)
    after_down = focused_label(adb.ui())
    report.check(after_down is not None and after_down != first,
                 "Down travels to the other row",
                 f"{first!r} -> {after_down!r}")

    adb.key(KEY_UP)
    after_up = focused_label(adb.ui())
    report.check(after_up == first,
                 "Up comes back to the first row",
                 f"{after_down!r} -> {after_up!r}")

    print("\n  (escape gesture: Up, Up, Down, Down, OK)")
    for code in (KEY_UP, KEY_UP, KEY_DOWN, KEY_DOWN, KEY_OK):
        adb.key(code)
    time.sleep(1.0)
    pin = adb.ui()
    reached_pin = on_screen(pin, PIN_MARKER)
    report.check(reached_pin,
                 "the gesture reaches the maintenance pin prompt",
                 "this is the way back into a TV the gate would otherwise strand"
                 if reached_pin else
                 f"landed on: {texts(pin)[:6]}")

    if reached_pin:
        adb.key(KEY_BACK)
        time.sleep(1.0)
        report.check(on_screen(adb.ui(), GATE_MARKER),
                     "Back returns to the gate, TV left as found")

    print()
    if report.failures:
        print(f"FAILED: {len(report.failures)} check(s): {', '.join(report.failures)}")
        return 1
    print("All checks passed on real hardware.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
