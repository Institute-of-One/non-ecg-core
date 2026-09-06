"""A recorded prior-art search, so the novelty claim can be checked rather than believed.

A search nobody can repeat is an opinion. Every query below is stored with the database
it was sent to, the date it was sent, the number of records it returned and the records
themselves, so the claim "no prior work states this bound" has something behind it and so
a reviewer can run the same search and disagree.

    python novelty/search_prior_art.py            # run and write novelty/results.json
    python novelty/search_prior_art.py --report   # re-read results.json and print

Two databases are used because they index differently: PubMed covers the clinical and
medical-physics literature, Europe PMC additionally indexes preprints and full text, so a
result buried in a methods section is still reachable.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timezone, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.json"

PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

#: Politeness. NCBI asks for no more than three requests per second without an API key;
#: one per second leaves margin and costs nothing at this scale.
DELAY_SECONDS = 1.0

#: Each query is a question the novelty claim depends on. The comment says what a hit
#: would mean -- a search whose hits you have not decided how to interpret in advance is
#: a search you can talk yourself out of.
QUERIES = [
    (
        "A. image-based cardiac gating in CT",
        "(cardiac[Title/Abstract] AND (self-gating[Title/Abstract] OR "
        "self-gated[Title/Abstract] OR kymogram[Title/Abstract] OR "
        '"image-based gating"[Title/Abstract]) AND (CT[Title/Abstract] OR '
        "tomography[Title/Abstract]))",
        "Crowded field expected. Hits here are prior art for the mechanism, not for the "
        "bound. What matters is whether any of them work on a NON-cardiac protocol.",
    ),
    (
        "B. cardiac phase or heart rate recovered from a non-gated CT",
        '((non-gated[Title/Abstract] OR nongated[Title/Abstract] OR "without '
        'electrocardiogram"[Title/Abstract] OR "without ECG"[Title/Abstract]) AND '
        "(cardiac[Title/Abstract] AND (phase[Title/Abstract] OR "
        "gating[Title/Abstract] OR \"heart rate\"[Title/Abstract])) AND "
        "(CT[Title/Abstract] OR tomography[Title/Abstract]))",
        "The closest neighbours. A hit that RECOVERS timing (rather than correcting for "
        "motion) on a routine scan would be direct prior art.",
    ),
    (
        "C. the sampling bound itself",
        "((helical[Title/Abstract] OR spiral[Title/Abstract]) AND CT[Title/Abstract] AND "
        "(pitch[Title/Abstract] AND (sampling[Title/Abstract] OR "
        "Nyquist[Title/Abstract] OR aliasing[Title/Abstract])) AND "
        "(cardiac[Title/Abstract] OR heart[Title/Abstract]))",
        "The claim. A hit stating a feasibility condition in terms of pitch, rotation "
        "time and heart rate would end this project, and should.",
    ),
    (
        "D. opportunistic cardiac assessment on routine chest CT",
        "(opportunistic[Title/Abstract] AND (cardiac[Title/Abstract] OR "
        "cardiovascular[Title/Abstract]) AND (\"chest CT\"[Title/Abstract] OR "
        '"thoracic CT"[Title/Abstract] OR "computed tomography"[Title/Abstract]))',
        "The genre the new paper would sit in. Expected to be busy and structural -- "
        "calcium, infarct, anatomy. A FUNCTIONAL or temporal hit would be the competitor.",
    ),
    (
        "E. cardiac motion as signal rather than artefact",
        '(("motion artifact"[Title/Abstract] OR "motion correction"[Title/Abstract]) AND '
        "cardiac[Title/Abstract] AND (non-gated[Title/Abstract] OR "
        "nongated[Title/Abstract]) AND (CT[Title/Abstract] OR "
        "tomography[Title/Abstract]))",
        "The active AI direction the bound would constrain. Hits are the audience, not "
        "the competition -- unless one of them already states what is recoverable.",
    ),
]


def _get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "IORN-011 prior-art search"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def search_pubmed(term: str, retmax: int = 40) -> dict:
    query = urllib.parse.urlencode(
        {"db": "pubmed", "term": term, "retmax": retmax, "retmode": "json"}
    )
    found = _get(f"{PUBMED}/esearch.fcgi?{query}")["esearchresult"]
    identifiers = found.get("idlist", [])
    records = []
    if identifiers:
        time.sleep(DELAY_SECONDS)
        summary_query = urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(identifiers), "retmode": "json"}
        )
        summaries = _get(f"{PUBMED}/esummary.fcgi?{summary_query}")["result"]
        for identifier in identifiers:
            entry = summaries.get(identifier, {})
            records.append(
                {
                    "id": identifier,
                    "year": (entry.get("pubdate") or "")[:4],
                    "journal": entry.get("source", ""),
                    "title": entry.get("title", ""),
                }
            )
    return {"total": int(found.get("count", 0)), "returned": len(records), "records": records}


def search_europe_pmc(term: str, page_size: int = 40) -> dict:
    query = urllib.parse.urlencode(
        {"query": term, "format": "json", "pageSize": page_size, "resultType": "lite"}
    )
    found = _get(f"{EUROPE_PMC}?{query}")
    def _venue(record: dict) -> str:
        """Europe PMC returns bookOrReportDetails as an object, not a string.

        Taking it as a venue name put a dict where every consumer expected text, and the
        report crashed on the first book-shaped record rather than on the first run.
        """
        venue = record.get("journalTitle")
        if isinstance(venue, str) and venue.strip():
            return venue
        details = record.get("bookOrReportDetails")
        if isinstance(details, dict):
            return str(details.get("publisher") or "book/report")
        if isinstance(details, str) and details.strip():
            return details
        return "preprint"

    records = [
        {
            "id": r.get("id", ""),
            "year": str(r.get("pubYear", "")),
            "journal": _venue(r),
            "title": str(r.get("title", "")),
        }
        for r in found.get("resultList", {}).get("result", [])
    ]
    return {"total": int(found.get("hitCount", 0)), "returned": len(records), "records": records}


#: Europe PMC does not take PubMed's field tags, so each query is restated in its syntax.
EUROPE_PMC_TERMS = {
    "A. image-based cardiac gating in CT": (
        'TITLE_ABS:(cardiac AND (self-gating OR self-gated OR kymogram OR "image-based '
        'gating") AND (CT OR tomography))'
    ),
    "B. cardiac phase or heart rate recovered from a non-gated CT": (
        'TITLE_ABS:((non-gated OR nongated OR "without electrocardiogram" OR "without '
        'ECG") AND cardiac AND (phase OR gating OR "heart rate") AND (CT OR tomography))'
    ),
    "C. the sampling bound itself": (
        "TITLE_ABS:((helical OR spiral) AND CT AND pitch AND (sampling OR Nyquist OR "
        "aliasing) AND (cardiac OR heart))"
    ),
    "D. opportunistic cardiac assessment on routine chest CT": (
        'TITLE_ABS:(opportunistic AND (cardiac OR cardiovascular) AND ("chest CT" OR '
        '"thoracic CT" OR "computed tomography"))'
    ),
    "E. cardiac motion as signal rather than artefact": (
        'TITLE_ABS:(("motion artifact" OR "motion correction") AND cardiac AND (non-gated '
        "OR nongated) AND (CT OR tomography))"
    ),
}


def run() -> int:
    searched_on = datetime.now(timezone.utc).date().isoformat()
    out = {"searched_on": searched_on, "queries": []}
    for label, term, what_a_hit_means in QUERIES:
        print(f"--- {label}")
        record = {
            "label": label,
            "what_a_hit_means": what_a_hit_means,
            "pubmed_term": term,
            "europe_pmc_term": EUROPE_PMC_TERMS[label],
        }
        try:
            record["pubmed"] = search_pubmed(term)
            print(f"    PubMed     : {record['pubmed']['total']} records")
        except Exception as error:  # noqa: BLE001 - a failed search must be visible, not silent
            record["pubmed"] = {"error": repr(error)}
            print(f"    PubMed     : FAILED {error}")
        time.sleep(DELAY_SECONDS)
        try:
            record["europe_pmc"] = search_europe_pmc(EUROPE_PMC_TERMS[label])
            print(f"    Europe PMC : {record['europe_pmc']['total']} records")
        except Exception as error:  # noqa: BLE001
            record["europe_pmc"] = {"error": repr(error)}
            print(f"    Europe PMC : FAILED {error}")
        time.sleep(DELAY_SECONDS)
        out["queries"].append(record)

    RESULTS.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten: {RESULTS}")
    return 0


def report() -> int:
    if not RESULTS.is_file():
        print("no results.json; run without --report first")
        return 1
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    print(f"searched on {data['searched_on']}\n")
    for query in data["queries"]:
        pubmed = query.get("pubmed", {})
        europe = query.get("europe_pmc", {})
        print(f"=== {query['label']}")
        print(f"    PubMed {pubmed.get('total', '?')}, Europe PMC {europe.get('total', '?')}")
        print(f"    a hit means: {query['what_a_hit_means']}")
        seen = set()
        for record in (pubmed.get("records", []) + europe.get("records", []))[:200]:
            key = record["title"].lower()[:70]
            if key in seen:
                continue
            seen.add(key)
            print(f"      {record['year']:>4}  {record['journal'][:28]:28}  {record['title'][:95]}")
        print()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print the stored results")
    sys.exit(report() if parser.parse_args().report else run())
