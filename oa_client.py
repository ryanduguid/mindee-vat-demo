"""OpenAccountants MCP client.

Talks to the OpenAccountants MCP server over JSON-RPC 2.0 at
https://www.openaccountants.com/api/mcp. The MCP now requires authentication on
tool calls, so a token (OA_MCP_TOKEN) is needed for live mode. Without one, this
client returns bundled sample responses that mirror the live shape so the demo
runs end to end.

Exposes the two calls the VAT pipeline needs:
  - start(intent, jurisdiction)  -> which verified skill(s) govern this question
  - get_skill(slug)              -> the rules + tier + named verifier
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

MCP_URL = os.environ.get("OA_MCP_URL", "https://www.openaccountants.com/api/mcp")
MCP_TOKEN = os.environ.get("OA_MCP_TOKEN")


class OAClient:
    def __init__(self, token: str | None = MCP_TOKEN, url: str = MCP_URL):
        self.token = token
        self.url = url
        self._id = 0

    @property
    def live(self) -> bool:
        return bool(self.token)

    # -- public API ---------------------------------------------------------

    def start(self, intent: str, jurisdiction: str) -> dict:
        if not self.live:
            return _MOCK_START.get(jurisdiction.upper(), _MOCK_START["_DEFAULT"])
        return self._call("start", {"intent": intent, "jurisdiction": jurisdiction})

    def get_skill(self, slug: str) -> dict:
        if not self.live:
            return _MOCK_SKILL.get(slug, _MOCK_SKILL["_DEFAULT"])
        return self._call("get_skill", {"slug": slug})

    # -- transport ----------------------------------------------------------

    def _call(self, tool: str, arguments: dict) -> dict:
        self._id += 1
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            }
        ).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            # Exact scheme TBD once OA shares the connector token format; Bearer
            # is the assumption. Swap here if OA uses an apikey/header instead.
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OA MCP HTTP {e.code}: {e.read().decode()[:300]}") from e
        if "error" in payload and payload["error"]:
            raise RuntimeError(f"OA MCP error: {payload['error']}")
        result = payload.get("result", {})
        # tool results come back as structuredContent (preferred) or text JSON
        if isinstance(result.get("structuredContent"), (dict, list)):
            return result["structuredContent"]
        text = (result.get("content") or [{}])[0].get("text", "{}")
        return json.loads(text)


# --- Bundled sample responses (mirror live MCP shape) ----------------------
# Values that come from the live MCP are marked <<from live MCP>>.

_MOCK_START = {
    "MT": {
        "jurisdiction": "MT",
        "intent": "VAT treatment on a cross-border invoice",
        "skills_to_load": ["mt-vat-place-of-supply"],
        "next_action": "Load the skill, then apply its rules to the invoice facts.",
    },
    "_DEFAULT": {
        "jurisdiction": "EU",
        "skills_to_load": ["eu-vat-place-of-supply"],
        "next_action": "Load the skill, then apply its rules to the invoice facts.",
    },
}

_MOCK_SKILL = {
    # Malta has a named lead verifier in OpenAccountants (Michael Cutajar, the
    # MT jurisdiction lead), so the demo shows the full trust line. Live, these
    # fields come straight from get_skill.
    "mt-vat-place-of-supply": {
        "slug": "mt-vat-place-of-supply",
        "name": "Malta — VAT place of supply & reverse charge",
        "jurisdiction": "MT",
        "tier": 1,  # <<from live MCP>>
        "verifier": "Michael Cutajar, CPA (Malta)",  # <<from live MCP>>
        "rules": {
            # Illustrative — production reads these from the skill markdown / via an LLM.
            "standard_rate": 0.18,
            "reduced_rates": [0.07, 0.05],
            "intra_eu_b2b": "reverse_charge",  # supplier invoices 0%, customer self-accounts
        },
        "source": "https://www.openaccountants.com/skills/mt-vat-place-of-supply",
    },
    "_DEFAULT": {
        "slug": "eu-vat-place-of-supply",
        "name": "EU — VAT place of supply & reverse charge",
        "jurisdiction": "EU",
        "tier": 2,
        "verifier": None,
        "rules": {"standard_rate": None, "intra_eu_b2b": "reverse_charge"},
        "source": "https://www.openaccountants.com/skills",
    },
}
