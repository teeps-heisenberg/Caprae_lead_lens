"""Fuzzy deduplication with provenance.

Blocking (same domain, or same name-prefix + city) keeps comparisons cheap; rapidfuzz
token_set_ratio decides matches inside a block; union-find clusters; merge keeps the most
trustworthy value per field and records every conflict so the UI can show it.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from rapidfuzz import fuzz

LEGAL_SUFFIXES = r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|plc|group|holdings|the)\b"
NAME_THRESHOLD = 90


def name_key(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(LEGAL_SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def find_clusters(rows: list[dict[str, Any]]) -> list[list[int]]:
    """Return clusters of row indexes (into `rows`) that refer to the same company."""
    uf = _UnionFind(len(rows))
    keys = [name_key(r.get("company") or "") for r in rows]

    by_domain: dict[str, list[int]] = defaultdict(list)
    by_block: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("domain"):
            by_domain[r["domain"]].append(i)
        k = keys[i]
        if k:
            city = (r.get("city") or "").lower().strip()
            by_block[f"{k[:4]}|{city}"].append(i)
            by_block[f"{k[:4]}|"].append(i)  # also block without city (city may be missing on one row)

    for idxs in by_domain.values():
        for j in idxs[1:]:
            uf.union(idxs[0], j)

    for idxs in by_block.values():
        if len(idxs) < 2:
            continue
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if uf.find(i) == uf.find(j):
                    continue
                if not keys[i] or not keys[j]:
                    continue
                di, dj = rows[i].get("domain"), rows[j].get("domain")
                if di and dj and di != dj:
                    continue  # different websites -> different companies even if names match
                if fuzz.token_set_ratio(keys[i], keys[j]) >= NAME_THRESHOLD:
                    uf.union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(rows)):
        groups[uf.find(i)].append(i)
    return [sorted(g) for g in groups.values()]


def _trust(row: dict[str, Any], flags: list[str]) -> tuple[int, int]:
    """Higher is better: fewer flags, more filled fields."""
    filled = sum(1 for v in row.values() if v not in (None, ""))
    return (-len(flags), filled)


def merge_cluster(
    rows: list[dict[str, Any]], flags: list[list[str]], idxs: list[int], row_ids: list[int]
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    """Merge rows[idxs] into one record. Returns (merged, merged_flags, conflicts)."""
    order = sorted(idxs, key=lambda i: _trust(rows[i], flags[i]), reverse=True)
    best = rows[order[0]]
    merged: dict[str, Any] = dict(best)
    conflicts: list[dict[str, Any]] = []
    merged_flags: set[str] = set(flags[order[0]])

    for f in merged:
        values = [(rows[i].get(f), row_ids[i]) for i in order if rows[i].get(f) not in (None, "")]
        if not values:
            continue
        chosen = values[0][0]
        merged[f] = chosen
        distinct = {str(v) for v, _ in values}
        if len(distinct) > 1:
            conflicts.append({"field": f, "chosen": chosen, "options": [{"value": v, "row": rid} for v, rid in values]})
    for i in order[1:]:
        for fl in flags[i]:
            # keep flags that describe the merged value only
            if fl.startswith(("email", "phone", "website", "linkedin")) and merged.get(fl.split("_")[0]) is None:
                merged_flags.add(fl)
    if len(idxs) > 1:
        merged_flags.add("merged_duplicate")
    return merged, sorted(merged_flags), conflicts
