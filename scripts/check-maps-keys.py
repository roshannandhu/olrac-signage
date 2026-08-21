"""Check the Google Maps keys and say plainly what is wrong with them.

Run this after pasting keys, instead of rebuilding the dashboard and squinting at a grey
box:

    python scripts/check-maps-keys.py

The server key gets a real verdict: Google's Static Maps endpoint returns a 403 with a
readable reason, so a wrong key, a disabled API and unlinked billing are all told apart.

The browser key cannot be checked from here, and no tool can. It is referrer-restricted by
design, so a request from a script is *supposed* to fail, and the JavaScript API reports a
bad key only at runtime inside the page (via gm_authFailure) rather than in its response.
This checks it is present and well-formed; the dashboard itself names the real failure.
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"


def read_env(path: Path, name: str) -> str:
    """Value of `name` in a .env file, or '' when absent - no dependency on dotenv."""
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(f"{name}=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def check_server_key(key: str) -> tuple[bool, str]:
    """Ask Static Maps for a real image; its rejection text is the diagnosis."""
    url = (
        "https://maps.googleapis.com/maps/api/staticmap?size=200x200"
        f"&markers=9.9312,76.2673&key={key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            if response.headers.get_content_maintype() == "image":
                return True, "returned a map image"
            return False, response.read(300).decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        return False, exc.read(300).decode("utf-8", "replace").strip()
    except Exception as exc:  # network down, proxy, DNS
        return False, f"could not reach Google ({exc})"


def main() -> int:
    server_key = read_env(ROOT / "backend" / ".env", "GOOGLE_MAPS_API_KEY")
    browser_key = read_env(
        ROOT / "frontend" / ".env.local", "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY"
    )

    print(f"\n{DIM}Reading backend/.env and frontend/.env.local{RESET}\n")
    failures = 0

    # --- server key -------------------------------------------------------------
    print("Server key (report PDFs, Maps Static API)")
    if not server_key:
        print(f"  {YELLOW}not set{RESET} - GOOGLE_MAPS_API_KEY in backend/.env is empty")
        print(f"  {DIM}Reports will print a location table instead of a map.{RESET}")
    else:
        ok, detail = check_server_key(server_key)
        if ok:
            print(f"  {GREEN}works{RESET} - {detail}")
        else:
            failures += 1
            print(f"  {RED}rejected{RESET} - {detail}")
            lowered = detail.lower()
            if "not authorized" in lowered or "api" in lowered and "enable" in lowered:
                print(f"  {DIM}Enable Maps Static API on this key.{RESET}")
            elif "invalid" in lowered:
                print(f"  {DIM}Wrong key, or an IP restriction excluding this machine.{RESET}")
            elif "billing" in lowered:
                print(f"  {DIM}Link a billing account to the project.{RESET}")

    # --- browser key ------------------------------------------------------------
    print("\nBrowser key (dashboard maps, Maps JavaScript API + Places API)")
    if not browser_key:
        print(f"  {YELLOW}not set{RESET} - NEXT_PUBLIC_GOOGLE_MAPS_API_KEY in frontend/.env.local is empty")
        print(f"  {DIM}Screen and ad pages will list locations instead of mapping them.{RESET}")
    elif not re.fullmatch(r"AIza[0-9A-Za-z_\-]{35}", browser_key):
        failures += 1
        print(f"  {RED}not a valid key format{RESET} - Google keys are 39 characters starting AIza")
    else:
        print(f"  {GREEN}present and well-formed{RESET}")
        print(f"  {DIM}Only the browser can confirm it: open a screen with a location set.{RESET}")
        print(f"  {DIM}If Google rejects it the map is replaced by a message naming why.{RESET}")

    # --- rebuild reminder -------------------------------------------------------
    build_id = ROOT / "frontend" / ".next" / "BUILD_ID"
    env_local = ROOT / "frontend" / ".env.local"
    if browser_key and build_id.exists() and env_local.exists():
        if env_local.stat().st_mtime > build_id.stat().st_mtime:
            print(
                f"\n{YELLOW}The dashboard was built before this key was set.{RESET}"
                f"\n  {DIM}NEXT_PUBLIC_* values are compiled in, so rerun scripts/start-dev.ps1"
                f" to rebuild.{RESET}"
            )

    print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
