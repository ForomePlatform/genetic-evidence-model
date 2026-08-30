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
import re
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
               sabs: Optional[str] = None, page_size: int = 200,
               semantic_types: Optional[str] = None,
               partial: bool = False) -> list[dict]:
        """Return a list of candidate concept dicts for ``term``.

        Each candidate is normalised to:
            {cui, name, root_source, semantic_types: [str, ...]}
        Rows with no CUI, a CUI of ``NONE``, no name, or a source-metadata
        ``rootSource == 'SRC'`` are filtered out. ``page_size`` is 200 (the
        only value the UTS search endpoint supports; pagination is not).
        ``semantic_types`` (a comma-joined TUI list) restricts results to those
        semantic types -- used to constrain a value search to its axis's type.
        ``search_type`` must be one the UTS endpoint accepts (words, exact,
        normalizedWords, normalizedString, left/rightTruncation) -- an unknown
        value silently returns nothing. ``partial`` sets partialSearch=true,
        letting a subset of the query words match.
        """
        params = {
            "string": term,
            "searchType": search_type,
            "pageSize": page_size,
        }
        if sabs:
            params["sabs"] = sabs
        if semantic_types:
            params["semanticTypes"] = semantic_types
        if partial:
            params["partialSearch"] = "true"
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

    def sources(self) -> list[dict]:
        """Source vocabularies of this UMLS version ->
        [{sab, name, language}], for the vocabulary picker. Cached like every
        other response."""
        data = self._get(f"/metadata/{self.version}/sources", {})
        res = data.get("result")
        if not isinstance(res, list):
            return []
        out = []
        for r in res:
            sab = r.get("abbreviation")
            if not sab:
                continue
            name = r.get("preferredName") or r.get("expandedForm") or ""
            name = re.sub(r",\s*\d{4}[_\d.-]*\s*$", "", name)   # drop version stamp
            lang = r.get("language")
            if isinstance(lang, dict):
                lang = lang.get("abbreviation")
            out.append({"sab": sab, "name": name, "language": lang or ""})
        return out

    def get_concept(self, cui: str) -> Optional[dict]:
        """Fetch a single concept by CUI (name, semantic types incl. TUIs,
        status, atom count). None if absent."""
        data = self._get(f"/content/{self.version}/CUI/{cui}", {})
        r = data.get("result") or {}
        if not isinstance(r, dict) or not r.get("ui"):
            return None
        sts = r.get("semanticTypes") or []
        return {"cui": r.get("ui"), "name": r.get("name"), "root_source": "MTH",
                "semantic_types": [s.get("name") for s in sts if s.get("name")],
                "semantic_type_details": [{"name": s.get("name"),
                                           "tui": (s.get("uri") or "").rsplit("/TUI/", 1)[-1]}
                                          for s in sts if s.get("name")],
                "status": r.get("status"), "atom_count": r.get("atomCount")}

    def atoms(self, cui: str, page_size: int = 300) -> list[dict]:
        """Atoms of a CUI -> [{sab, tty, name, code, obsolete, suppressible}]."""
        data = self._get(f"/content/{self.version}/CUI/{cui}/atoms",
                         {"pageSize": page_size})
        res = data.get("result")
        if not isinstance(res, list):
            return []
        out = []
        for a in res:
            out.append({"sab": a.get("rootSource"), "tty": a.get("termType"),
                        "name": a.get("name"), "language": a.get("language"),
                        "code": (a.get("code") or "").rsplit("/source/", 1)[-1],
                        "obsolete": str(a.get("obsolete")).lower() == "true",
                        "suppressible": str(a.get("suppressible")).lower() == "true"})
        return out

    def relations(self, cui: str, page_size: int = 400) -> list[dict]:
        """Relations of a CUI -> [{rel, rela, related_cui, related_code,
        related_name, sab}].

        Most relations are *source-asserted*: ``relatedId`` is a
        ``.../source/{SAB}/{code}`` URL, not a ``.../CUI/{cui}`` one, so there
        is no CUI to extract. ``related_code`` is the last path segment (a CUI
        or a source code) -- always present, a stable id for display/dedup --
        while ``related_cui`` is set only for genuine CUI-level relations.
        """
        data = self._get(f"/content/{self.version}/CUI/{cui}/relations",
                         {"pageSize": page_size})
        res = data.get("result")
        if not isinstance(res, list):
            return []
        out = []
        for r in res:
            rid = r.get("relatedId") or ""
            seg = rid.rsplit("/", 1)[-1]
            out.append({"rel": r.get("relationLabel"),
                        "rela": r.get("additionalRelationLabel"),
                        "related_cui": seg if "/CUI/" in rid else None,
                        "related_code": seg,
                        "related_name": r.get("relatedIdName"),
                        "sab": r.get("rootSource")})
        return out

    def source_ancestors(self, sab: str, code: str,
                         page_size: int = 120) -> list[dict]:
        """is_a ancestors of a source-vocabulary code via the UTS source
        ``/ancestors`` endpoint -- the correct way to roll a concept up within
        one vocabulary's hierarchy. Returns [{code, name, sab}] (the metadata
        root, rootSource ``SRC``, is dropped). The endpoint returns the ancestor
        *set*, not ordered by depth.
        """
        data = self._get(
            f"/content/{self.version}/source/{sab}/{code}/ancestors",
            {"pageSize": page_size})
        res = data.get("result")
        if not isinstance(res, list):
            return []
        out = []
        for a in res:
            if a.get("rootSource") == "SRC" or not a.get("ui") or not a.get("name"):
                continue
            out.append({"code": a.get("ui"), "name": a.get("name"),
                        "sab": a.get("rootSource")})
        return out

    def source_children(self, sab: str, code: str,
                        page_size: int = 120) -> list[dict]:
        """Direct is_a children of a source-vocabulary code via the UTS source
        ``/children`` endpoint. Returns [{code, name, sab}]."""
        data = self._get(
            f"/content/{self.version}/source/{sab}/{code}/children",
            {"pageSize": page_size})
        res = data.get("result")
        if not isinstance(res, list):
            return []
        out = []
        for a in res:
            if a.get("rootSource") == "SRC" or not a.get("ui") or not a.get("name"):
                continue
            out.append({"code": a.get("ui"), "name": a.get("name"),
                        "sab": a.get("rootSource")})
        return out

    def rollup(self, cui: str, use_sab: Optional[str] = None,
               sab_allow: Optional[set] = None, node_cap: int = 80) -> list[dict]:
        """Roll a concept up its **is_a** hierarchy within one source
        vocabulary, via that vocabulary's ancestors of the concept's code.

        This is the HSTA rollup: different vocabularies give different is_a
        hierarchies, so pass ``use_sab`` to pick one; with none, the first
        allowed source that has an ancestor chain is used. ``sab_allow`` limits
        the choice (e.g. to English is_a vocabularies). Returns
        [{name, code, sab}], the ancestor set, name-sorted.

        Using the source ``/ancestors`` endpoint (not a CUI PAR walk) matters:
        the is_a edges are source-asserted (``relatedId`` carries no CUI), so a
        CUI walk dead-ends immediately; and a source's ancestors respect its own
        hierarchy, so MeSH's thematic tree never leaks in as pseudo-ancestors.
        """
        cand: list[tuple] = []
        seen: set = set()
        for a in self.atoms(cui):
            sab = a.get("sab")
            if not sab or (sab_allow is not None and sab not in sab_allow):
                continue
            if use_sab and sab != use_sab:
                continue
            code = (a.get("code") or "").rsplit("/", 1)[-1]
            if code and (sab, code) not in seen:
                seen.add((sab, code))
                cand.append((sab, code))
        for sab, code in sorted(cand):
            anc = self.source_ancestors(sab, code, page_size=node_cap)
            if anc:
                return sorted(anc, key=lambda x: x["name"] or "")[:node_cap]
        return []

    def definitions(self, cui: str, page_size: int = 5) -> list[dict]:
        """Return [{source, value}] definitions for a CUI (empty if none)."""
        data = self._get(f"/content/{self.version}/CUI/{cui}/definitions",
                         {"pageSize": page_size})
        res = data.get("result")
        if not isinstance(res, list):  # 404 -> _get returns a search-shaped dict
            return []
        return [{"source": x.get("rootSource"), "value": (x.get("value") or "").strip()}
                for x in res if (x.get("value") or "").strip()]

    def get_semantic_type(self, tui: str) -> Optional[dict]:
        """Fetch a Semantic Network type by TUI: name, tree number, definition."""
        data = self._get(f"/semantic-network/{self.version}/TUI/{tui}", {})
        r = data.get("result") or {}
        if not isinstance(r, dict) or not r.get("ui"):
            return None
        return {"tui": r.get("ui"), "name": r.get("name"),
                "tree_number": r.get("treeNumber"),
                "abbreviation": r.get("abbreviation"),
                "definition": (r.get("definition") or "").strip()}


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
               sabs: Optional[str] = None, page_size: int = 200,
               semantic_types: Optional[str] = None,
               partial: bool = False) -> list[dict]:
        for cand in (self.dir / f"search_{self.slug(term)}__{search_type}.json",
                     self.dir / f"search_{self.slug(term)}.json"):
            if cand.is_file():
                data = json.loads(cand.read_text())
                results = (data.get("result") or {}).get("results") or []
                return [_normalise(r) for r in results
                        if r.get("ui") and r.get("ui") != "NONE"
                        and r.get("rootSource") != "SRC" and r.get("name")]
        return []

    def sources(self) -> list[dict]:
        return []

    def get_concept(self, cui: str) -> Optional[dict]:
        return None

    def definitions(self, cui: str, page_size: int = 5) -> list[dict]:
        return []

    def get_semantic_type(self, tui: str) -> Optional[dict]:
        return None

    def atoms(self, cui: str, page_size: int = 300) -> list[dict]:
        return []

    def relations(self, cui: str, page_size: int = 400) -> list[dict]:
        return []

    def source_ancestors(self, sab: str, code: str, page_size: int = 120) -> list[dict]:
        return []

    def source_children(self, sab: str, code: str, page_size: int = 120) -> list[dict]:
        return []

    def rollup(self, cui: str, use_sab=None, sab_allow=None,
               node_cap: int = 80) -> list[dict]:
        return []


class NullClient:
    """Returns nothing for everything; lets the harness run with no key."""

    def search(self, term: str, search_type: str = "words",
               sabs: Optional[str] = None, page_size: int = 200,
               semantic_types: Optional[str] = None,
               partial: bool = False) -> list[dict]:
        return []

    def sources(self) -> list[dict]:
        return []

    def get_concept(self, cui: str) -> Optional[dict]:
        return None

    def definitions(self, cui: str, page_size: int = 5) -> list[dict]:
        return []

    def get_semantic_type(self, tui: str) -> Optional[dict]:
        return None

    def atoms(self, cui: str, page_size: int = 300) -> list[dict]:
        return []

    def relations(self, cui: str, page_size: int = 400) -> list[dict]:
        return []

    def source_ancestors(self, sab: str, code: str, page_size: int = 120) -> list[dict]:
        return []

    def source_children(self, sab: str, code: str, page_size: int = 120) -> list[dict]:
        return []

    def rollup(self, cui: str, use_sab=None, sab_allow=None,
               node_cap: int = 80) -> list[dict]:
        return []
