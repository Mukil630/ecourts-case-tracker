import os
import sys
import requests
from ecourts_api import get_api_key

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_live_key():
    key = get_api_key()
    if not key or key == "your_api_key_here":
        print("[!] No API key found in .env or environment.")
        print("[*] Current value: 'your_api_key_here'")
        print("[*] Please paste your 'eci_live_...' key into .env and save the file.")
        return False

    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    print(f"[*] Found Key: {masked}")
    print("[*] Testing connection to https://webapi.ecourtsindia.com/api/partner/search/capabilities ...")

    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        res = requests.get("https://webapi.ecourtsindia.com/api/partner/search/capabilities", headers=headers, timeout=15)
        if res.status_code == 200:
            print("[+] SUCCESS! API Key is 100% VALID & ACTIVE.")
            data = res.json().get("data", {})
            print(f"[+] Supported Court Levels: {data.get('courtLevels')}")
            return True
        elif res.status_code == 401:
            print(f"[X] FAILED: 401 Unauthorized. Key '{masked}' was rejected.")
            print(f"    Details: {res.text}")
            return False
        else:
            print(f"[!] Server responded with code {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[X] Network error: {e}")
        return False

if __name__ == "__main__":
    test_live_key()
