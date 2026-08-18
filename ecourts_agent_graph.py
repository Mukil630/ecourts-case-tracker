import sys
from app.services.vision_agent import (
    run_vision_agent,
    build_ecourts_agent_graph,
    AgentState,
    manager,
)

__all__ = [
    "run_vision_agent",
    "build_ecourts_agent_graph",
    "AgentState",
    "manager",
]

if __name__ == "__main__":
    target_cnr = sys.argv[1] if len(sys.argv) > 1 else "DLND020047882015"
    print("=" * 65)
    print(" 🤖 ECOURTS AUTONOMOUS LANGGRAPH VISION AGENT ")
    print("=" * 65)
    print(f"[*] Target CNR: {target_cnr}")
    result = run_vision_agent(target_cnr)
    print(f"\n[+] Final Status: {result.get('status')}")
    print(f"[+] Result: {result}")
