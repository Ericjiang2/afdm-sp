#!/usr/bin/env python3
"""Zero-dependency paper search (Python 3 stdlib only: OpenAlex, Crossref, arXiv).

Usage:
  python3 search_papers.py --query "affine frequency division multiplexing" --start-year 2022 --end-year 2026 --max-papers 10 --sources open_alex crossref
"""
import argparse, concurrent.futures, json, re, time, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import date

UA = "Mozilla/5.0 (compatible; idea-funnel-search/1.0)"


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/xml, */*"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt == 0:
                time.sleep(1.0)
                continue
            raise


def _inv_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))[:360]


def fetch_open_alex(q, y0, y1, k):
    params = urllib.parse.urlencode({
        "search": q,
        "filter": f"publication_year:{y0}-{y1}",
        "per-page": min(max(k * 2, 10), 50),
    })
    data = json.loads(_get(f"https://api.openalex.org/works?{params}"))
    out = []
    for w in data.get("results", []):
        title = (w.get("title") or "").strip()
        if not title:
            continue
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name") or ""
        auths = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:5]]
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        pdf = (w.get("open_access") or {}).get("oa_url") or loc.get("pdf_url") or w.get("doi") or w.get("id", "")
        out.append(dict(
            title=title, year=w.get("publication_year") or 0, venue=src,
            authors=", ".join(x for x in auths if x), citations=w.get("cited_by_count") or 0,
            doi=doi, url=pdf, abstract=_inv_abstract(w.get("abstract_inverted_index")), source="open_alex",
        ))
    return out


def fetch_crossref(q, y0, y1, k):
    params = urllib.parse.urlencode({
        "query": q,
        "filter": f"from-pub-date:{y0}-01-01,until-pub-date:{y1}-12-31",
        "rows": min(max(k * 2, 10), 25),
    })
    data = json.loads(_get(f"https://api.crossref.org/works?{params}"))
    out = []
    for it in (data.get("message") or {}).get("items", []):
        titles = it.get("title") or []
        if not titles:
            continue
        yr = ((it.get("published") or it.get("issued") or {}).get("date-parts") or [[0]])[0][0] or 0
        auths = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in (it.get("author") or [])[:5]]
        venue = (it.get("container-title") or [""])[0]
        doi = it.get("DOI") or ""
        abstr = re.sub(r"<[^>]+>", " ", it.get("abstract") or "").strip()[:360]
        out.append(dict(
            title=titles[0].strip(), year=yr, venue=venue, authors=", ".join(x for x in auths if x),
            citations=it.get("is-referenced-by-count") or 0, doi=doi,
            url=f"https://doi.org/{doi}" if doi else (it.get("URL") or ""), abstract=abstr, source="crossref",
        ))
    return out


def fetch_arxiv(q, y0, y1, k):
    params = urllib.parse.urlencode({
        "search_query": f"all:{q}", "start": 0, "max_results": min(max(k * 2, 10), 40),
        "sortBy": "relevance", "sortOrder": "descending",
    })
    root = ET.fromstring(_get(f"http://export.arxiv.org/api/query?{params}"))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        pub = (e.findtext("a:published", "", ns) or "")[:4]
        yr = int(pub) if pub.isdigit() else 0
        if yr and not (y0 <= yr <= y1):
            continue
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        aid_base = re.sub(r"v\d+$", "", aid)
        title = " ".join((e.findtext("a:title", "", ns) or "").split())
        auths = [a.findtext("a:name", "", ns) or "" for a in e.findall("a:author", ns)[:5]]
        abstr = " ".join((e.findtext("a:summary", "", ns) or "").split())[:360]
        out.append(dict(
            title=title, year=yr, venue=f"arXiv:{aid}", authors=", ".join(x for x in auths if x),
            citations=0, doi="", arxiv_id=aid_base, url=f"https://arxiv.org/pdf/{aid}.pdf" if aid else "",
            abstract=abstr, source="arxiv",
        ))
    return out


FETCHERS = {"open_alex": fetch_open_alex, "crossref": fetch_crossref, "arxiv": fetch_arxiv}


def _dedup_key(it):
    doi = (it.get("doi") or "").lower().strip()
    m = re.match(r"^10\.48550/arxiv\.(.+)$", doi)
    if m:
        return f"arxiv:{re.sub(r'v\d+$', '', m.group(1))}"
    if it.get("arxiv_id"):
        return f"arxiv:{it['arxiv_id'].lower()}"
    if doi:
        return f"doi:{doi}"
    return re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:80]


def _score(item, terms):
    hay = f"{item['title']} {item['abstract']} {item['venue']}".lower()
    t_low = item["title"].lower()
    hits = sum((2 if t in t_low else 1) for t in terms if t in hay)
    return (hits, min(item["citations"], 200) / 200.0, item["year"])


def main():
    ap = argparse.ArgumentParser(description="Zero-dependency academic paper search.")
    ap.add_argument("--query", "-q", required=True)
    ap.add_argument("--start-year", type=int, default=2020)
    ap.add_argument("--end-year", type=int, default=date.today().year)
    ap.add_argument("--max-papers", type=int, default=10)
    ap.add_argument("--sources", nargs="+", choices=sorted(FETCHERS), default=["open_alex", "crossref"])
    ap.add_argument("--json", action="store_true", help="emit JSON list")
    a = ap.parse_args()

    raw, errs = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(a.sources)) as ex:
        futs = {ex.submit(FETCHERS[s], a.query, a.start_year, a.end_year, a.max_papers): s for s in a.sources}
        for f, s in futs.items():
            try:
                raw.extend(f.result())
            except Exception as e:
                errs.append(f"{s}: {e}")

    by_key, title_to_key = {}, {}
    for it in raw:
        key = _dedup_key(it)
        if not key:
            continue
        nt = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:80]
        if key not in by_key and len(nt) >= 24 and nt in title_to_key:
            key = title_to_key[nt]
        if key in by_key:
            cur = by_key[key]
            cur["citations"] = max(cur["citations"], it["citations"])
            cur["abstract"] = cur["abstract"] or it["abstract"]
            if not cur["venue"] or (cur["venue"].startswith("arXiv:") and it["venue"] and not it["venue"].startswith("arXiv:")):
                cur["venue"] = it["venue"]
            if (not cur["doi"] or cur["doi"].lower().startswith("10.48550/")) and it["doi"]:
                cur["doi"] = it["doi"]
            if it["source"] not in cur["found_in"]:
                cur["found_in"].append(it["source"])
        else:
            it["found_in"] = [it["source"]]
            by_key[key] = it
            if len(nt) >= 24:
                title_to_key[nt] = key

    terms = [t for t in re.findall(r"[a-z0-9]{2,}", a.query.lower()) if t not in {"the", "and", "for", "with", "under", "from"}]
    ranked = sorted(by_key.values(), key=lambda x: _score(x, terms), reverse=True)[:a.max_papers]

    if a.json:
        print(json.dumps(ranked, ensure_ascii=False, indent=2))
        return
    if errs:
        print(f"# warnings: {'; '.join(errs)}")
    for i, p in enumerate(ranked, 1):
        cite = f" | cites={p['citations']}" if p["citations"] else ""
        doi = f" | doi:{p['doi']}" if p["doi"] else ""
        print(f"[{i}] ({p['year']}) {p['title']}\n    {p['authors']} — {p['venue'] or p['source']}{cite}{doi} [{'+'.join(p['found_in'])}]\n    url: {p['url']}")
        if p["abstract"]:
            print(f"    abs: {p['abstract']}")


if __name__ == "__main__":
    main()
