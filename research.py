import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

@dataclass
class Study:
    pmid: str
    title: str
    abstract: str
    authors: str
    journal: str
    year: str
    doi: str

def fetch_study(keywords: str, max_results: int = 5) -> Study | None:
    """
    البحث في PubMed وإرجاع أفضل دراسة مناسبة.
    يفضل الدراسات: RCT, meta-analysis, systematic review
    """
    # البحث
    search_params = {
        "db": "pubmed",
        "term": f"{keywords} AND (randomized controlled trial[pt] OR meta-analysis[pt] OR systematic review[pt])",
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
        "datetype": "pdat",
        "mindate": "2015",  # دراسات من 2015 فأحدث فقط
        "maxdate": "2025",
    }

    resp = requests.get(PUBMED_SEARCH, params=search_params, timeout=15)
    data = resp.json()
    ids = data.get("esearchresult", {}).get("idlist", [])

    if not ids:
        # fallback بدون فلتر النوع
        search_params["term"] = keywords
        resp = requests.get(PUBMED_SEARCH, params=search_params, timeout=15)
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])

    if not ids:
        return None

    # جلب تفاصيل أول دراسة
    pmid = ids[0]
    fetch_params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
        "rettype": "abstract",
    }

    resp = requests.get(PUBMED_FETCH, params=fetch_params, timeout=15)
    root = ET.fromstring(resp.content)
    article = root.find(".//PubmedArticle")

    if article is None:
        return None

    title = article.findtext(".//ArticleTitle", default="").strip()
    abstract = " ".join(t.text or "" for t in article.findall(".//AbstractText")).strip()
    journal = article.findtext(".//Journal/Title", default="")
    year = article.findtext(".//PubDate/Year", default="")

    authors = []
    for author in article.findall(".//Author")[:3]:
        last = author.findtext("LastName", "")
        fore = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {fore}".strip())
    authors_str = ", ".join(authors)
    if len(article.findall(".//Author")) > 3:
        authors_str += " et al."

    doi = ""
    for id_el in article.findall(".//ArticleId"):
        if id_el.get("IdType") == "doi":
            doi = id_el.text or ""
            break

    return Study(
        pmid=pmid,
        title=title,
        abstract=abstract[:2000],
        authors=authors_str,
        journal=journal,
        year=year,
        doi=doi,
    )
