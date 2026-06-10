"""SEC EDGAR full-text search client for dilution-filing detection.

Uses the free EDGAR full-text search API (efts.sec.gov). Dilution catalysts of
interest (design section 4.2): shelf registrations, ATM offerings, toxic
convertibles, and offering-related 8-Ks.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import requests

from .models import Filing

EDGAR_FTS_URL = "https://efts.sec.gov/LATEST/search-index"

# Form types that signal dilution supply pressure.
DILUTION_FORMS: tuple[str, ...] = ("S-1", "S-3", "424B5", "424B3", "F-1", "F-3", "8-K")

# SEC requests a descriptive User-Agent with contact info on all API traffic.
DEFAULT_USER_AGENT = "lowcap-short-system research contact@example.com"


class EdgarClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.http = session or requests.Session()
        self.http.headers.setdefault("User-Agent", user_agent)

    def recent_dilution_filings(
        self,
        symbol: str,
        since: date,
        forms: tuple[str, ...] = DILUTION_FORMS,
    ) -> list[Filing]:
        """Full-text search for dilution-relevant filings mentioning `symbol`."""
        params = {
            "q": f'"{symbol}"',
            "forms": ",".join(forms),
            "dateRange": "custom",
            "startdt": since.isoformat(),
            "enddt": date.today().isoformat(),
        }
        resp = self.http.get(EDGAR_FTS_URL, params=params, timeout=30)
        resp.raise_for_status()
        hits = (resp.json().get("hits") or {}).get("hits") or []
        filings: list[Filing] = []
        for h in hits:
            src = h.get("_source") or {}
            form = src.get("form_type") or src.get("file_type") or ""
            filed_raw = src.get("file_date") or ""
            try:
                filed_at = datetime.fromisoformat(filed_raw).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            filings.append(
                Filing(
                    symbol=symbol,
                    form_type=form,
                    filed_at=filed_at,
                    accession_no=src.get("accession_no", ""),
                    url=f"https://www.sec.gov/Archives/{src.get('file_name', '')}",
                )
            )
        return filings
