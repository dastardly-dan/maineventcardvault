#!/usr/bin/env python3
"""
Main Event Card Vault — website update packet validator.

Validates a ChatGPT research packet against the schema, checks internal
consistency, and matches every record to a permanent card_uid before anything
touches the site.

    python3 build/validate_packet.py build/packets/site_update_packet_2026-08-29.json

Exit codes:  0 = clean   1 = warnings only   2 = blocking errors

SCOPE NOTE. This script does not research, estimate, recalculate or second-guess
any value. It checks that the packet is well formed, internally consistent with
its own stated numbers, and matchable to real cards. Anything it flags is an
arithmetic or referential problem in the packet, never a market opinion.
"""

import json
import sys
import csv
import re
from pathlib import Path
from datetime import date

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit("pip install jsonschema --break-system-packages")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "build" / "site_update_packet.schema.json"
UIDS = ROOT / "build" / "card_uids.tsv"
DEPLOYED = ROOT / "build" / "ratings_current.json"      # last packet actually deployed
HISTORY = ROOT / "build" / "ratings_history.jsonl"      # append-only snapshots

SCHEMA_VERSION = "2.0.0"
CONF_GATE = 60          # publish_ready requires confidence >= this
MER_TOLERANCE = 1.0     # rounding slack on the Main Event Rating formula
MER_W_HEALTH = 0.45
MER_W_UPSIDE = 0.55

errors, warnings, notes = [], [], []


def err(uid, field, msg, expected=""):
    errors.append({"uid": uid, "field": field, "problem": msg, "expected": expected})


def warn(uid, field, msg, expected=""):
    warnings.append({"uid": uid, "field": field, "problem": msg, "expected": expected})


def load_uid_registry():
    if not UIDS.exists():
        sys.exit(f"missing {UIDS} — the permanent card_uid registry")
    with UIDS.open(encoding="utf-8") as fh:
        return {r["card_uid"]: r for r in csv.DictReader(fh, delimiter="\t")}


def check_schema(packet):
    with SCHEMA.open(encoding="utf-8") as fh:
        v = Draft202012Validator(json.load(fh))
    for e in sorted(v.iter_errors(packet), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        uid = ""
        parts = list(e.absolute_path)
        if len(parts) >= 2 and parts[0] == "cards":
            try:
                uid = packet["cards"][parts[1]].get("card_uid", f"index {parts[1]}")
            except Exception:
                uid = f"index {parts[1]}"
        err(uid, path, e.message, str(e.validator_value)[:80])


def check_consistency(packet, registry):
    seen = {}
    group_keys = {g["group_key"] for g in packet.get("set_groups", [])}

    for c in packet.get("cards", []):
        uid = c.get("card_uid", "(missing)")

        # -- primary key integrity ------------------------------------
        if uid in seen:
            err(uid, "card_uid", "duplicate primary key in packet", "unique")
        seen[uid] = True
        if uid not in registry:
            err(uid, "card_uid", "no such card in build/card_uids.tsv", "a registered MECV-#### uid")

        lo, mid, hi = c.get("vault_value_low"), c.get("vault_value_mid"), c.get("vault_value_high")
        health, upside = c.get("market_health"), c.get("upside_potential")
        mer, conf = c.get("main_event_rating"), c.get("confidence")
        pub, status = c.get("publish_ready"), c.get("publication_status")
        pos, ask = c.get("market_position"), c.get("asking_price")

        # -- value range ordering -------------------------------------
        if None not in (lo, mid, hi) and not (lo <= mid <= hi):
            err(uid, "vault_value_*", f"range out of order: {lo} / {mid} / {hi}", "low <= mid <= high")

        # -- Main Event Rating arithmetic ------------------------------
        if None not in (health, upside, mer):
            expect = MER_W_HEALTH * health + MER_W_UPSIDE * upside
            if abs(mer - expect) > MER_TOLERANCE:
                err(uid, "main_event_rating",
                    f"{mer} does not equal 0.45x{health} + 0.55x{upside} = {expect:.2f}",
                    f"within {MER_TOLERANCE:g} of the weighted formula (rounding slack)")

        # -- confidence label matches confidence score -----------------
        lab = c.get("confidence_label")
        if conf is not None and lab:
            want = ("high" if conf >= 80 else "medium" if conf >= 60
                    else "low" if conf >= 40 else "insufficient_evidence")
            if lab != want:
                err(uid, "confidence_label", f"'{lab}' does not match confidence {conf}", want)

        # -- the publication gate --------------------------------------
        if pub is True:
            if conf is None or conf < CONF_GATE:
                err(uid, "publish_ready", f"true with confidence {conf}", f"confidence >= {CONF_GATE}")
            for f in ("market_health", "upside_potential", "main_event_rating", "confidence"):
                if c.get(f) is None:
                    err(uid, f, "null on a publish_ready card", "a value, or publish_ready false")
            if status not in ("published",):
                err(uid, "publication_status", f"'{status}' conflicts with publish_ready true", "published")
        else:
            if status == "published":
                err(uid, "publication_status", "'published' while publish_ready is false", "hidden / research_in_progress")

        if status == "internal_only" and pub is True:
            err(uid, "publication_status", "internal_only cannot be publish_ready", "publish_ready false")

        # -- market_position: arithmetic consistency only -------------
        # Sale format is NOT a gate (research-process decision, v2.0.0). What is
        # checked is that the label agrees with the packet's own numbers, on the
        # all-in basis the schema defines.
        allin = c.get("asking_price_all_in")
        if allin is None and ask is not None:
            allin = ask + (c.get("asking_price_shipping") or 0)

        if pos and pos != "insufficient_evidence":
            if allin is None:
                err(uid, "market_position", "set with no asking price on any basis",
                    "asking_price_all_in, or insufficient_evidence")
            elif None not in (lo, hi):
                tol = 0.05
                want = ("below_estimated_market" if allin < lo * (1 - tol)
                        else "above_estimated_market" if allin > hi * (1 + tol)
                        else "within_estimated_market")
                if pos != want:
                    err(uid, "market_position",
                        f"'{pos}' but all-in {allin} against range {lo}-{hi}", want)
            if conf is not None and conf < CONF_GATE:
                err(uid, "market_position", f"'{pos}' at confidence {conf}",
                    "insufficient_evidence below the confidence gate")
            if c.get("asking_price_all_in") is None and c.get("asking_price_shipping") is None:
                warn(uid, "asking_price_all_in",
                     "absent; compared using asking_price alone, so shipping is excluded on one side only",
                     "asking_price_all_in for a like-for-like basis")

        # -- tier rules -------------------------------------------------
        if c.get("tier") == "T3":
            gk = c.get("set_group_key")
            if not gk:
                err(uid, "set_group_key", "T3 card with no set group", "a group_key from set_groups")
            elif gk not in group_keys:
                err(uid, "set_group_key", f"'{gk}' not present in set_groups", "a declared group_key")
            if pub is True:
                warn(uid, "publish_ready",
                     "T3 is set-group valued, not individually researched",
                     "false, unless the research process intends otherwise")

        # -- evidence hygiene -------------------------------------------
        for i, e in enumerate(c.get("evidence", [])):
            if e.get("format") == "unknown" and pos and pos != "insufficient_evidence":
                warn(uid, f"evidence[{i}].format",
                     "unknown format counted toward a published market_position",
                     "auction / bin / bin_best_offer")

        # -- change discipline ------------------------------------------
        for i, ch in enumerate(c.get("changes_from_last_week", [])):
            try:
                delta = abs(float(ch["to"]) - float(ch["from"]))
            except (TypeError, ValueError):
                continue
            if delta >= 2 and not ch.get("source"):
                warn(uid, f"changes_from_last_week[{i}]",
                     f"{delta:g}-point change with no source URL", "a source for any change >= 2")
            if ch.get("field") == "upside_potential" and delta > 5 and not ch.get("source"):
                err(uid, f"changes_from_last_week[{i}]",
                    f"upside moved {delta:g} points without a cited event", "max 5 without a verified event")

        # -- zero-for-null smell ----------------------------------------
        if c.get("refreshed") and c.get("valuation_basis") == "none" and mid == 0:
            warn(uid, "vault_value_mid", "0 with basis 'none' — is this meant to be null?", "null")


def check_packet_age(packet):
    if not DEPLOYED.exists():
        notes.append("No previously deployed packet found — this will be the first.")
        return
    try:
        prev = json.loads(DEPLOYED.read_text())
        if packet["packet_date"] < prev.get("packet_date", ""):
            err("(packet)", "packet_date",
                f"{packet['packet_date']} is older than the deployed {prev['packet_date']}",
                "a newer packet")
        elif packet["packet_date"] == prev.get("packet_date"):
            warn("(packet)", "packet_date", "same date as the deployed packet", "a new research date")
    except Exception as e:
        warn("(packet)", "packet_date", f"could not read deployed packet: {e}", "")


def report(packet, registry):
    cards = packet.get("cards", [])
    matched = [c for c in cards if c.get("card_uid") in registry]
    pub = [c for c in cards if c.get("publish_ready") is True]
    review = [c for c in cards if c.get("needs_human_review") is True]
    unmatched = [c for c in cards if c.get("card_uid") not in registry]
    missing = sorted(set(registry) - {c.get("card_uid") for c in cards})

    print("\nMain Event Card Vault Update Report")
    print("=" * 60)
    print(f"Research packet date:  {packet.get('packet_date','?')}")
    print(f"Packet version:        {packet.get('packet_version','?')}")
    print(f"Rubric version:        {packet.get('rubric_version','?')}")
    print(f"Deployment status:     {'BLOCKED' if errors else 'Ready'}")
    print("\nRecord summary")
    print(f"  Records received:                 {len(cards)}")
    print(f"  Records validated clean:          {len(cards) - len({e['uid'] for e in errors} - {'(packet)'})}")
    print(f"  Records matched to website cards: {len(matched)}")
    print(f"  Public ratings approved:          {len(pub)}")
    print(f"  Ratings hidden (not approved):    {len(cards) - len(pub)}")
    print(f"  Unmatched records:                {len(unmatched)}")
    print(f"  Registered cards absent:          {len(missing)}")
    print(f"  Records requiring human review:   {len(review)}")

    if unmatched:
        print("\nUnmatched records")
        for c in unmatched:
            print(f"  {c.get('card_uid','(no uid)')}  {str(c.get('ebay_item_id',''))[:20]}")
    if missing:
        print(f"\nRegistered cards absent from packet ({len(missing)})")
        print("  " + ", ".join(missing[:12]) + (" …" if len(missing) > 12 else ""))

    sc = packet.get("site_corrections", [])
    ex = packet.get("external_manual_actions", [])
    if sc or ex:
        print("\nCorrections")
        print(f"  Site corrections to apply:        {len(sc)}")
        for x in sc:
            print(f"    {x['card_uid']}  {x['field']} -> {x['to']}")
        print(f"  External actions (NOT automated): {len(ex)}")
        for x in ex:
            print(f"    {x['card_uid']}  [{x['system']}] {x['action']}")

    for label, items in (("BLOCKING ERRORS", errors), ("Warnings", warnings)):
        if items:
            print(f"\n{label} ({len(items)})")
            for x in items[:60]:
                print(f"  [{x['uid']}] {x['field']}")
                print(f"      problem:  {x['problem']}")
                if x["expected"]:
                    print(f"      expected: {x['expected']}")
            if len(items) > 60:
                print(f"  … {len(items)-60} more")
    for n in notes:
        print(f"\nNote: {n}")

    print("\n" + "=" * 60)
    if errors:
        print("BLOCKED — nothing written. Send the errors above back to the research process.")
        print("The site was not modified. No values were guessed or filled in.")
    elif warnings:
        print("PASSED WITH WARNINGS — safe to deploy; review the warnings.")
    else:
        print("CLEAN — safe to deploy.")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"BLOCKED — {path.name} is not valid JSON: {e}")

    registry = load_uid_registry()
    check_schema(packet)
    if not errors:
        check_consistency(packet, registry)
        check_packet_age(packet)
    report(packet, registry)
    sys.exit(2 if errors else (1 if warnings else 0))


if __name__ == "__main__":
    main()
