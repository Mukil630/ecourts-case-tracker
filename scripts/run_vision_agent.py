import sys
from app.services.vision_agent import run_vision_agent

if __name__ == "__main__":
    cnr = sys.argv[1] if len(sys.argv) > 1 else "DLND020047882015"
    print("=" * 65)
    print(" 🤖 ECOURTS AUTONOMOUS LANGGRAPH VISION AGENT ")
    print("=" * 65)
    print(f"[*] Target CNR: {cnr}")
    result = run_vision_agent(cnr)
    print(f"\n[+] Status: {result.get('status')}")
    print(f"[+] Output: {result}")
