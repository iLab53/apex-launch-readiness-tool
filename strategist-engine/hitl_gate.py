"""
STRATEGIST -- HITL Gate (Full)
Presents signals to an analyst and records their decision.
Configurable auto-thresholds. AUTO_APPROVE flag for test mode.
"""
import datetime

# Threshold configuration -- edit these to change review behaviour
AUTO_APPROVE_GRADES = {"HIGH"}   # grades that skip review and auto-approve
AUTO_REJECT_GRADES  = set()      # grades that skip review and auto-reject (empty = never)

# Set True to bypass all input() calls (for automated testing)
AUTO_APPROVE = True

def hitl_gate(signals, region: str = ""):
    reviewed = []
    for signal in signals:
        grade   = signal.get("evidence_grade", "LOW")
        score   = signal.get("confidence_score", 0)
        domain  = signal.get("source_domain", "?")
        tier    = signal.get("source_tier", "?")
        excerpt = signal.get("raw_excerpt", "")[:100]
        notes   = signal.get("grader_notes", "")
        adversarial_verdict = signal.get("adversarial_verdict", "")
        adversarial_notes   = signal.get("adversarial_notes", "")

        # Test mode: bypass all input()
        if AUTO_APPROVE:
            signal["hitl_decision"]  = "APPROVED"
            signal["hitl_notes"]     = "test mode auto-approve"
            signal["hitl_timestamp"] = datetime.datetime.now().isoformat()
            print("  [HITL] " + region + " AUTO-APPROVED (test mode)")
            reviewed.append(signal)
            continue

        # Force manual review if adversarial reviewer challenged the signal
        if adversarial_verdict == "CHALLENGE":
            print("\n" + "=" * 55)
            print("  HITL REVIEW REQUIRED (ADVERSARIAL CHALLENGE)")
            print("  Region  : " + region)
            print("  Source  : " + domain + "  (" + tier + ")")
            print("  Grade   : " + grade + "  |  Score: " + str(round(score, 3)))
            print("  Excerpt : " + excerpt)
            print("  Grader  : " + notes)
            print("  Review  : " + adversarial_notes)
            print("=" * 55)
            print("  [A] Approve   [R] Reject   [O] Override to HIGH")
            raw_decision = input("  Decision: ").strip().upper()
            analyst_notes = input("  Notes (Enter to skip): ").strip()
            if raw_decision == "A":
                signal["hitl_decision"] = "APPROVED"
            elif raw_decision == "R":
                signal["hitl_decision"] = "REJECTED"
            elif raw_decision == "O":
                signal["hitl_decision"] = "OVERRIDE"
                signal["evidence_grade"] = "HIGH"
                print("  [HITL] Grade overridden to HIGH")
            else:
                signal["hitl_decision"] = "APPROVED"
                print("  [HITL] Unrecognised input -- defaulting to APPROVED")
            signal["hitl_notes"] = analyst_notes
            signal["hitl_timestamp"] = datetime.datetime.now().isoformat()
            print("  [HITL] " + region + " -> " + signal["hitl_decision"])
            reviewed.append(signal)
            continue

        # Auto-approve threshold
        if grade in AUTO_APPROVE_GRADES:
            signal["hitl_decision"]  = "APPROVED"
            signal["hitl_notes"]     = "auto-approved: grade " + grade + " meets threshold"
            signal["hitl_timestamp"] = datetime.datetime.now().isoformat()
            print("  [HITL] " + region + " AUTO-APPROVED (grade=" + grade + ")")
            reviewed.append(signal)
            continue

        # Auto-reject threshold
        if grade in AUTO_REJECT_GRADES:
            signal["hitl_decision"]  = "REJECTED"
            signal["hitl_notes"]     = "auto-rejected: grade " + grade + " below threshold"
            signal["hitl_timestamp"] = datetime.datetime.now().isoformat()
            print("  [HITL] " + region + " AUTO-REJECTED (grade=" + grade + ")")
            reviewed.append(signal)
            continue

        # Manual review required
        print("\n" + "=" * 55)
        print("  HITL REVIEW REQUIRED")
        print("  Region  : " + region)
        print("  Source  : " + domain + "  (" + tier + ")")
        print("  Grade   : " + grade + "  |  Score: " + str(round(score, 3)))
        print("  Excerpt : " + excerpt)
        print("  Grader  : " + notes)
        print("=" * 55)
        print("  [A] Approve   [R] Reject   [O] Override to HIGH")
        raw_decision = input("  Decision: ").strip().upper()
        analyst_notes = input("  Notes (Enter to skip): ").strip()
        if raw_decision == "A":
            signal["hitl_decision"] = "APPROVED"
        elif raw_decision == "R":
            signal["hitl_decision"] = "REJECTED"
        elif raw_decision == "O":
            signal["hitl_decision"] = "OVERRIDE"
            signal["evidence_grade"] = "HIGH"
            print("  [HITL] Grade overridden to HIGH")
        else:
            signal["hitl_decision"] = "APPROVED"
            print("  [HITL] Unrecognised input -- defaulting to APPROVED")
        signal["hitl_notes"]     = analyst_notes
        signal["hitl_timestamp"] = datetime.datetime.now().isoformat()
        print("  [HITL] " + region + " -> " + signal["hitl_decision"])
        reviewed.append(signal)

    return reviewed