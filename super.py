import os
import sys
import time
import webbrowser
import requests

SERVICE_URL = os.getenv("SERVICE_URL", "https://discord-key-bot-wd75.onrender.com")


def machine_id() -> str:
    import platform, hashlib
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def prompt(prompt_text: str) -> str:
    try:
        return input(prompt_text).strip()
    except KeyboardInterrupt:
        print()
        sys.exit(1)


def activate_if_needed(key: str, user_id: str) -> None:
    try:
        r = requests.get(f"{SERVICE_URL}/api/key-info", params={"key": key}, timeout=8)
        if r.status_code == 200 and r.json().get("exists"):
            # If key exists but is unassigned, bind to user
            info = r.json()
            if (info.get("user_id") in (None, 0)):
                requests.post(
                    f"{SERVICE_URL}/api/activate",
                    data={"key": key, "user_id": str(int(user_id)), "machine_id": machine_id()},
                    timeout=8,
                )
        else:
            # Try activation regardless; server will validate
            requests.post(
                f"{SERVICE_URL}/api/activate",
                data={"key": key, "user_id": str(int(user_id)), "machine_id": machine_id()},
                timeout=8,
            )
    except Exception:
        pass


def main():
    key = os.getenv("KEY") or prompt("Enter your activation key: ")
    user_id = os.getenv("USER_ID") or prompt("Enter your Discord user ID: ")
    try:
        int(user_id)
    except Exception:
        print("Invalid user ID")
        sys.exit(1)

    activate_if_needed(key, user_id)

    url = f"{SERVICE_URL}/login?user_id={user_id}&key={key}"
    print(f"Opening panel: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        print("Open this URL in your browser:")
        print(url)


if __name__ == "__main__":
    main()