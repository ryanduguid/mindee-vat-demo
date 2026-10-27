# Mindee → OpenAccountants: VAT-on-invoices demo

Demonstrates how Mindee invoice extractions can feed a VAT check using OpenAccountants sample rules, with an optional live MCP connection.

Default runs use bundled sample responses. Their rates, verdicts and reviewer labels are illustrative fixtures, not evidence that an accountant reviewed the demo or a live skill. For live use, check the fetched skill's review status, reviewer, version and review date against the [review method](https://www.openaccountants.com/review-method). A jurisdiction lead's name alone does not establish review. Have a qualified professional review outputs before filing or acting on them.

```
invoice.pdf
  └─ Mindee  →  { supplier_country, customer_country, vat_id, net, vat_rate, vat_amount, lines }
        └─ OpenAccountants MCP  →  load the VAT skill for that jurisdiction
              └─ Verdict:  ✅ reverse charge correctly applied   /   ⚠️ VAT charged in error
                 · the rule that decided it (cited)
                 · the skill's published review status, if present
                 · suggested handoff to a qualified professional
```

![Mindee → OpenAccountants VAT demo](demo.svg)

> Regenerate the visual: `python make_svg.py` (static SVG, no deps) · animated GIF: `brew install vhs && vhs demo.tape`

## Why this is a partnership, not an overlap

- **Mindee = the eyes.** Best-in-class extraction: document → structured JSON. Stops (by design) at *what's in the document*.
- **OpenAccountants** loads skill content through MCP for a working paper. Review status varies by skill version.

Mindee's customers (fintechs, AP automation, accounting platforms) ask one question right after extraction: *"…is this VAT right?"* Today nothing in the pipeline answers it. This demo does — and it makes Mindee's extraction stickier and more valuable without Mindee having to build regulated tax logic or recruit a CPA network.

## What it shows

Three sample invoices (real Mindee extraction shape), run through the OpenAccountants MCP. The bundled Malta response includes an illustrative reviewer label; the demo does not establish review of a live skill:

| Sample | Scenario | Expected verdict |
|--------|----------|------------------|
| `mt_domestic.json` | MT supplier → MT customer, 18% VAT | ✅ Correct domestic VAT |
| `mt_to_fr_reverse_charge.json` | MT → FR, both B2B (VAT IDs), €0 VAT + RC note | ✅ Reverse charge correctly applied |
| `mt_to_fr_WRONG.json` | MT → FR B2B, **but 18% VAT charged** | ⚠️ **VAT charged in error — should be reverse charge** |

That last one is the money shot: Mindee faithfully reads `VAT = €1,800`; **OpenAccountants is the layer that knows it shouldn't be there**; citing the sample rule; live professional review must be checked separately.

## Run it

```bash
git clone https://github.com/openaccountants/mindee-vat-demo
cd mindee-vat-demo
python pipeline.py                 # runs all three samples (mock mode, no keys needed)
python pipeline.py samples/mt_to_fr_WRONG.json
```

### Go live

Two env vars flip it from mocked to real:

```bash
export OA_MCP_TOKEN=...      # OpenAccountants account token (the MCP now requires auth)
export MINDEE_API_KEY=...    # Mindee free-tier key for the invoice model
python pipeline.py --pdf path/to/real_invoice.pdf
```

- With `OA_MCP_TOKEN` set, `oa_client.py` calls the live MCP at `https://www.openaccountants.com/api/mcp` (`start` → `get_skill`); skill content comes back live; inspect its review status and reviewer fields.
- With `MINDEE_API_KEY` set, `mindee_client.py` calls Mindee's invoice model instead of reading a bundled sample.
- With neither, everything runs on the bundled samples so the flow is visible end-to-end today.

## Files

| File | Role |
|------|------|
| `pipeline.py` | Orchestrator + CLI: Mindee → OA → verdict report |
| `mindee_client.py` | Mindee invoice extraction (live API or bundled sample) |
| `oa_client.py` | OpenAccountants MCP JSON-RPC client (live or mock) |
| `vat_check.py` | Applies the loaded OA rules to the extraction → verdict |
| `samples/*.json` | Mindee-shaped invoice extractions |

## Honest notes (read before the pitch)

- The VAT decision logic in `vat_check.py` is a **deliberate simplification** of EU place-of-supply rules (domestic standard-rate vs intra-EU B2B reverse charge); enough to make the demo land. In production the OA *skill* carries the full rule set and an AI agent reasons over it; professional review must be established for the specific skill version and your facts.
- The bundled OA responses mirror the live MCP's shape; values marked `<<from live MCP>>` are sample placeholders. Live mode attempts a separate MCP request; this README does not establish the returned skill's review status.
