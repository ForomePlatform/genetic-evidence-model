#!/usr/bin/env python3
"""Clients for the UMLS UTS REST API used by the crosswalk harness.

Three interchangeable clients, all exposing the same ``search(term, ...)``
interface so the harness and its tests can swap them:

* ``UTSClient``      - the real UTS REST API (https://uts-ws.nlm.nih.gov/rest).
                       Authenticates with an API key passed as the ``apiKey``
                       query parameter (the current UTS scheme; the older
                       ticket-granting-ticket flow is deprecated). Requires a
                       free UMLS licence; see mapping/README.md.
* ``FixtureClient``  - reads canned JSON responses from a directory, for
                       offline unit tests. No network.
* ``NullClient``     - returns no results for everything, so the harness can
                       run end-to-end without a key and produce an honest
                       all-``pending`` crosswalk.

The real client caches every raw response to disk so reruns are cheap and the
exact UMLS payload behind each mapping is auditable.

Requirements for ``UTSClient``: ``requests``.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

UTS_BASE = "https://uts-ws.nlm.nih.gov/rest"


def _cache_key(path: str, params: dict) -> str:
    """Stable hash of an endpoint+params pair (apiKey excluded)."""
    safe = {k: v for k, v in sorted(params.items()) if k != "apiKey"}
    raw = path + "?" + urlencode(safe)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class UTSClient:
    """Live UTS REST client. ``search`` returns the parsed ``result`` block."""

    def __init__(self, api_key: str, version: str = "current",
                 cache_dir: Optional[Path] = None, pause: float = 0.05):
        if not api_key:
            raise ValueError("UTSClient requires a non-empty API key.")
        self.api_key = api_key
        self.version = version
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pause = pause
        # Imported lazily so the module loads without `requests` installed
        # (the fixture/null clients have no such dependency).
        import requests  # noqa: F401
        self._requests = requests

    def _get(self, path: str, params: dict) -> dict:
        params = dict(params)
        params["apiKey"] = self.api_key
        if self.cache_dir:
            cf = self.cache_dir / f"{_cache_key(path, params)}.json"
            if cf.is_file():
                return json.loads(cf.read_text())
        url = f"{UTS_BASE}{path}"
        resp = self._requests.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            # UTS returns 404 for a search that matched nothing; treat as empty.
            data = {"result": {"results": []}}
        else:
            resp.raise_for_status()
            data = resp.json()
        if self.cache_dir:
            cf.write_text(json.dumps(data, indent=2))
        if self.pause:
            time.sleep(self.pause)
        return data

    def search(self, term: str, search_type: str = "words",
               sabs: Optional[str] = None, page_size: int = 200) -> list[dict]:
        """Return a list of candidate concept dicts for ``term``.

        Each candidate is normalised to:
            {cui, name, root_source, semantic_types: [str, ...]}
        Rows with no CUI, a CUI of ``NONE``, no name, or a source-metadata
        ``rootSource == 'SRC'`` are filtered out. ``page_size`` is 200 (the
        only value the UTS search endpoint supports; pagination is not).
        """
        params = {
            "string": term,
            "searchType": search_type,
            "pageSize": page_size,
        }
        if sabs:
            params["sabs"] = sabs
        data = self._get(f"/search/{self.version}", params)
        results = (data.get("result") or {}).get("results") or []
        out = []
        for r in results:
            cui = r.get("ui")
            if not cui or cui == "NONE":
                continue
            if r.get("rootSource") == "SRC":  # source-metadata row, not a concept
                continue
            if not r.get("name"):  # no usable name -> cannot verify a match
                continue
            out.append(_normalise(r))
        return out


def _normalise(r: dict) -> dict:
    sts = r.get("semanticTypes") or []
    names = []
    for s in sts:
        if isinstance(s, str):
            names.append(s)
        elif isinstance(s, dict):
            names.append(s.get("name") or s.get("uri") or "")
    return {
        "cui": r.get("ui"),
        "name": r.get("name"),
        "root_source": r.get("rootSource"),
        "semantic_types": [n for n in names if n],
    }


class FixtureClient:
    """Reads canned search responses from ``fixtures_dir`` for offline tests.

    Lookup key is the search term, slugified, optionally suffixed with the
    search type. A fixture file is the raw UTS JSON payload (the same shape
    the live API returns), so the same parsing path is exercised in tests.
    Fixture filenames are lower-cased by ``slug`` and must be stored
    lower-cased on disk (matters on case-sensitive filesystems).
    """

    def __init__(self, fixtures_dir: Path):
        self.dir = Path(fixtures_dir)

    @staticmethod
    def slug(term: str) -> str:
        keep = [c.lower() if c.isalnum() else "_" for c in term]
        s = "".join(keep)
        while "__" in s:
            s = s.replace("__", "_")
        return s.strip("_")

    def search(self, term: str, search_type: str = "words",
               sabs: Optional[str] = None, page_size: int = 200) -> list[dict]:
        for cand in (self.dir / f"search_{self.slug(term)}__{search_type}.json",
                     self.dir / f"search_{self.slug(term)}.json"):
            if cand.is_file():
                data = json.loads(cand.read_text())
                results = (data.get("result") or {}).get("results") or []
                return [_normalise(r) for r in results
                        if r.get("ui") and r.get("ui") != "NONE"
                        and r.get("rootSource") != "SRC" and r.get("name")]
        return []


class NullClient:
    """Returns nothing for everything; lets the harness run with no key."""

    def search(self, term: str, search_type: str = "words",
               sabs: Optional[str] = None, page_size: int = 200) -> list[dict]:
        return []
