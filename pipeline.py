#!/usr/bin/env python3
"""Mindee -> OpenAccountants VAT-on-invoices pipeline.

    python pipeline.py                         # run all bundled samples (mock mode)
    python pipeline.py samples/de_to_fr_WRONG.json
    python pipeline.py --pdf invoice.pdf       # live (needs MINDEE_API_KEY + OA_MCP_TOKEN)

The flow:
    Mindee extract  ->  OA MCP (start -> get_skill)  ->  apply rules  ->  verdict
"""

from __future__ import annotations

import glob
import os
import sys

import mindee_client
import vat_check
from oa_client import OAClient

STATUS = {"ok": "✅", "warn": "⚠️ ", "info": "ℹ️ "}


def run_one(source: str, oa: OAClient) -> None:
    prediction = mindee_client.extract(source)
    facts = mindee_client.normalize(prediction)

    # 1. Mindee read the invoice
    print(f"\n📄  {os.path.basename(source)}")
    print(f"    Mindee → {facts['supplier_name']} ({facts['supplier_country']}) "
          f"→ {facts['customer_name']} ({facts['customer_country']})")
    print(f"           net {facts['currency']} {facts['net']:.2f} · "
          f"VAT {facts['currency']} {facts['vat_amount']:.2f} "
          f"({facts['vat_rate']:.0%})"
          + (f" · customer VAT ID {facts['customer_vat_id']}" if facts['customer_vat_id'] else ""))

    # 2. OpenAccountants — which verified rules govern this?
    plan = oa.start("Check VAT treatment on a cross-border invoice", facts["supplier_country"] or "EU")
    slug = (plan.get("skills_to_load") or [None])[0]
    skill = oa.get_skill(slug) if slug else {}

    # 3. Apply the rules
    verdict = vat_check.check(facts, skill)

    # 4. Report
    tier = verdict.get("tier")
    verifier = verdict.get("verifier")
    trust = (f"tier {tier}"
             + (f", signed off by {verifier}" if verifier else ", no named verifier yet"))
    print(f"    OpenAccountants → {verdict.get('oa_skill_name') or 'VAT rules'}  ({trust})")
    print(f"    {STATUS.get(verdict['status'], '')} {verdict['headline']}")
    print(f"       {verdict['detail']}")
    print(f"       rule: {verdict['rule_cited']}")
    if verdict["status"] == "warn":
        print("       → handoff: request_accountant_review (route to the named jurisdiction lead)")


def main(argv: list[str]) -> int:
    oa = OAClient()
    mode = "LIVE" if oa.live else "MOCK (set OA_MCP_TOKEN + MINDEE_API_KEY to go live)"
    print(f"Mindee → OpenAccountants · VAT-on-invoices demo  [{mode}]")

    if "--pdf" in argv:
        source = argv[argv.index("--pdf") + 1]
        run_one(source, oa)
    elif len(argv) > 1:
        run_one(argv[1], oa)
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        for sample in sorted(glob.glob(os.path.join(here, "samples", "*.json"))):
            run_one(sample, oa)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
