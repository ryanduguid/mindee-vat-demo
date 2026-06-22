"""Mindee invoice extraction.

In live mode (MINDEE_API_KEY set) this would call Mindee's invoice model. For the
demo it loads a bundled sample with the same field shape Mindee returns, then
normalizes it to the handful of facts the VAT check needs.

Keeping the Mindee SDK call as a thin, swappable seam is deliberate — the live
swap is a few lines, and the rest of the pipeline doesn't change.
"""

from __future__ import annotations

import json
import os

MINDEE_API_KEY = os.environ.get("MINDEE_API_KEY")


def extract(source: str) -> dict:
    """Return a Mindee-shaped invoice prediction.

    source: a path to a bundled sample .json, or (live) a path to a PDF/image.
    """
    if MINDEE_API_KEY and source.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        return _extract_live(source)
    with open(source) as fh:
        return json.load(fh)


def _extract_live(path: str) -> dict:  # pragma: no cover - needs a real key
    """Live Mindee call. Wired but inert until MINDEE_API_KEY + the SDK are present.

        pip install mindee
    """
    from mindee import Client, product  # type: ignore

    mindee_client = Client(api_key=MINDEE_API_KEY)
    doc = mindee_client.source_from_path(path)
    result = mindee_client.parse(product.InvoiceV4, doc)
    pred = result.document.inference.prediction
    # Map the SDK object onto the same dict shape as the bundled samples.
    return {
        "supplier_name": str(pred.supplier_name.value or ""),
        "supplier_country": _country(pred.supplier_address),
        "customer_name": str(pred.customer_name.value or ""),
        "customer_country": _country(pred.customer_address),
        "customer_vat_id": _vat_id(pred.customer_company_registrations),
        "currency": str(pred.locale.currency or ""),
        "total_net": float(pred.total_net.value or 0),
        "total_tax": float(pred.total_tax.value or 0),
        "taxes": [{"rate": float(t.rate or 0), "value": float(t.value or 0)} for t in pred.taxes],
        "notes": " ".join(str(getattr(pred, "notes", "") or "")),
    }


def _country(addr) -> str:  # pragma: no cover
    return (getattr(addr, "country", None) or "").upper()


def _vat_id(regs) -> str | None:  # pragma: no cover
    for r in regs or []:
        if getattr(r, "type", "").upper() in ("VAT NUMBER", "VAT"):
            return str(r.value)
    return None


def normalize(prediction: dict) -> dict:
    """Reduce a Mindee prediction to the facts the VAT check needs."""
    taxes = prediction.get("taxes") or []
    vat_amount = sum(t.get("value", 0) for t in taxes)
    # Mindee gives rate per tax line; take the headline non-zero rate, else 0.
    rates = [t.get("rate", 0) for t in taxes if t.get("value", 0)]
    vat_rate = (rates[0] / 100.0) if rates else 0.0
    notes = (prediction.get("notes") or "").lower()
    return {
        "supplier_name": prediction.get("supplier_name", ""),
        "supplier_country": (prediction.get("supplier_country") or "").upper(),
        "customer_name": prediction.get("customer_name", ""),
        "customer_country": (prediction.get("customer_country") or "").upper(),
        "customer_vat_id": prediction.get("customer_vat_id"),
        "currency": prediction.get("currency", "EUR"),
        "net": float(prediction.get("total_net", 0)),
        "vat_amount": float(vat_amount),
        "vat_rate": float(vat_rate),
        "reverse_charge_note": "reverse charge" in notes,
    }
