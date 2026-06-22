"""Apply the loaded OpenAccountants VAT rules to a Mindee extraction.

DELIBERATE SIMPLIFICATION: this covers the two cases the demo needs — a domestic
supply (standard rate should apply) and an intra-EU B2B supply (reverse charge:
supplier invoices 0%, customer self-accounts). Real life has many more (goods vs
services, OSS/distance selling, exemptions, special schemes). In production the
OA *skill* carries the full rule set and an AI agent reasons over it; here we do a
transparent check on the core fields so the value is visible without an LLM.
"""

from __future__ import annotations

EU = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR",
    "GR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK",
}


def check(facts: dict, oa_skill: dict) -> dict:
    rules = oa_skill.get("rules", {})
    verifier = oa_skill.get("verifier")
    tier = oa_skill.get("tier")
    base = {
        "oa_skill": oa_skill.get("slug"),
        "oa_skill_name": oa_skill.get("name"),
        "tier": tier,
        "verifier": verifier,
        "source": oa_skill.get("source"),
    }

    sc = facts["supplier_country"]
    cc = facts["customer_country"]
    charged_vat = facts["vat_amount"] > 0.005
    is_b2b = bool(facts.get("customer_vat_id"))

    # --- Domestic supply --------------------------------------------------
    if sc and cc and sc == cc:
        std = rules.get("standard_rate")
        if std is None:
            return {**base, "status": "info",
                    "headline": "Domestic supply — standard rate applies",
                    "detail": "Could not confirm the standard rate from the loaded skill.",
                    "rule_cited": "Domestic supply: standard rate applies."}
        if abs(facts["vat_rate"] - std) < 0.001:
            return {**base, "status": "ok",
                    "headline": f"Correct domestic VAT ({std:.0%})",
                    "detail": f"{sc} domestic supply taxed at the verified standard rate {std:.0%}.",
                    "rule_cited": f"{sc} domestic supply → standard rate {std:.0%}."}
        return {**base, "status": "warn",
                "headline": f"VAT rate looks wrong (invoice {facts['vat_rate']:.0%} vs verified {std:.0%})",
                "detail": f"Invoice applied {facts['vat_rate']:.0%}; the verified {sc} standard rate is {std:.0%}.",
                "rule_cited": f"{sc} domestic supply → standard rate {std:.0%}."}

    # --- Intra-EU B2B supply ---------------------------------------------
    if sc in EU and cc in EU and sc != cc and is_b2b:
        if charged_vat:
            return {**base, "status": "warn",
                    "headline": "VAT charged in error — should be reverse charge",
                    "detail": (f"Intra-EU B2B supply ({sc} → {cc}, customer VAT ID "
                               f"{facts['customer_vat_id']}). Supplier should invoice 0% and the "
                               f"customer self-accounts. This invoice charged "
                               f"{facts['currency']} {facts['vat_amount']:.2f}."),
                    "rule_cited": "Intra-EU B2B: place of supply is the customer's country → reverse charge."}
        return {**base, "status": "ok",
                "headline": "Reverse charge correctly applied",
                "detail": (f"Intra-EU B2B supply ({sc} → {cc}). Supplier correctly invoiced 0% VAT; "
                           f"customer self-accounts."
                           + ("" if facts["reverse_charge_note"] else
                              "  Note: no explicit 'reverse charge' wording detected on the invoice — verify it's present.")),
                "rule_cited": "Intra-EU B2B: place of supply is the customer's country → reverse charge."}

    # --- Everything else --------------------------------------------------
    return {**base, "status": "info",
            "headline": "Scenario outside this demo's rule set",
            "detail": (f"{sc or '?'} → {cc or '?'}"
                       + (", B2B" if is_b2b else ", B2C")
                       + ". Cases like B2C distance selling (OSS), exports, or non-EU parties need the "
                         "full OA skill / an agent reasoning step — not covered by the demo's two rules."),
            "rule_cited": "n/a"}
