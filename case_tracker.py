from scripts.case_tracker import track_and_verify_case
import sys

if __name__ == "__main__":
    target_cnr = sys.argv[1] if len(sys.argv) > 1 else "DLND020047882015"
    track_and_verify_case(target_cnr)
