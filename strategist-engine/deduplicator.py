# deduplicator.py
import hashlib

def _make_hash(sig: dict) -> str:
    """Create a dedup hash from headline + region."""
    key = f"{sig.get('headline','').lower().strip()}|{sig.get('region','').lower()}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def deduplicate(signals: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Remove duplicate signals. Returns (deduped, dedup_log).
    Two signals are duplicates if they share the same dedup_hash.
    """
    seen = {}
    deduped = []
    dedup_log = []

    for sig in signals:
        h = sig.get("dedup_hash") or _make_hash(sig)
        sig["dedup_hash"] = h

        if h not in seen:
            seen[h] = sig["signal_id"]
            deduped.append(sig)
        else:
            dedup_log.append({
                "dropped_id": sig["signal_id"],
                "kept_id":    seen[h],
                "reason":     "duplicate headline+region",
            })

    return deduped, dedup_log