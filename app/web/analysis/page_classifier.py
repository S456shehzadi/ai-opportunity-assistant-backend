"""Page type classification heuristic layer for opportunity analysis."""

import re
from urllib.parse import urlparse

from app.web.models.document import PageType

OPPORTUNITY_KEYWORDS = re.compile(
    r"\b(?:scholarship|fellowship|grant|internship|stipend|funding\s+amount|tuition\s+waiver|"
    r"eligibility\s+criteria|application\s+deadline|how\s+to\s+apply|award\s+amount)\b",
    re.IGNORECASE,
)

PROGRAM_KEYWORDS = re.compile(
    r"\b(?:master\s+of|bachelor\s+of|curriculum|degree\s+program|study\s+plan|course\s+structure|"
    r"faculty\s+of|credits\s+ects|admission\s+requirements)\b",
    re.IGNORECASE,
)

ORGANIZATION_KEYWORDS = re.compile(
    r"\b(?:about\s+us|our\s+mission|leadership|board\s+of\s+directors|executive\s+team|"
    r"who\s+we\s+are|history\s+of\s+the\s+organization)\b",
    re.IGNORECASE,
)

NEWS_KEYWORDS = re.compile(
    r"\b(?:press\s+release|news\s+article|latest\s+news|announcement|published\s+on)\b",
    re.IGNORECASE,
)

BLOG_KEYWORDS = re.compile(
    r"\b(?:blog\s+post|leave\s+a\s+comment|author\s+bio|min\s+read)\b",
    re.IGNORECASE,
)

DIRECTORY_KEYWORDS = re.compile(
    r"\b(?:directory|list\s+of\s+scholarships|database\s+search|filter\s+results|all\s+programs)\b",
    re.IGNORECASE,
)

DOCS_KEYWORDS = re.compile(
    r"\b(?:documentation|user\s+guide|frequently\s+asked\s+questions|faq|help\s+center)\b",
    re.IGNORECASE,
)


class PageTypeClassifier:
    """Classifies webpage structure into broad categories based on text, title, and URL signals."""

    @classmethod
    def classify(cls, title: str, clean_text: str, url: str) -> PageType:
        """Determines preliminary PageType for downstream processing."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Root URL check
        if not path:
            return PageType.HOME_PAGE

        combined = f"{title} {clean_text[:2000]}".lower()

        # Score categories
        opp_score = len(OPPORTUNITY_KEYWORDS.findall(combined))
        prog_score = len(PROGRAM_KEYWORDS.findall(combined))
        org_score = len(ORGANIZATION_KEYWORDS.findall(combined))
        news_score = len(NEWS_KEYWORDS.findall(combined))
        blog_score = len(BLOG_KEYWORDS.findall(combined))
        dir_score = len(DIRECTORY_KEYWORDS.findall(combined))
        docs_score = len(DOCS_KEYWORDS.findall(combined))

        # URL path boosts
        if re.search(r"/(?:scholarship|fellowship|grant|internship)s?\b", url, re.I):
            opp_score += 3
        if re.search(r"/(?:programs|degree|masters|curriculum)\b", url, re.I):
            prog_score += 3
        if re.search(r"/(?:about|organization|team)\b", url, re.I):
            org_score += 3
        if re.search(r"/(?:news|press)\b", url, re.I):
            news_score += 3
        if re.search(r"/(?:blog|posts)\b", url, re.I):
            blog_score += 3
        if re.search(r"/(?:search|directory|database)\b", url, re.I):
            dir_score += 3
        if re.search(r"/(?:faq|docs|help)\b", url, re.I):
            docs_score += 3

        scores = [
            (PageType.OPPORTUNITY_PAGE, opp_score),
            (PageType.PROGRAM_PAGE, prog_score),
            (PageType.DIRECTORY_PAGE, dir_score),
            (PageType.ORGANIZATION_PAGE, org_score),
            (PageType.DOCUMENTATION, docs_score),
            (PageType.NEWS_PAGE, news_score),
            (PageType.BLOG_PAGE, blog_score),
        ]

        scores.sort(key=lambda x: x[1], reverse=True)
        top_type, top_score = scores[0]

        if top_score >= 2:
            return top_type

        return PageType.UNKNOWN
