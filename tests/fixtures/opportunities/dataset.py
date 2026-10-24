"""Synthetic HTML documents and dataset factory for opportunity extraction testing.

Covers all 18 prompt-mandated test scenarios for rigorous evaluation.
"""

from __future__ import annotations

import uuid

from app.web.models.document import (
    ContentQualityScore,
    PageType,
    WebDocument,
)

COMPLETE_SCHOLARSHIP_HTML = """
<!DOCTYPE html>
<html>
<head><title>DAAD Helmut-Schmidt-Programme Master Scholarships 2026</title></head>
<body>
  <h1>DAAD Helmut-Schmidt-Programme Master Scholarships 2026</h1>
  <p>The German Academic Exchange Service (DAAD) offers scholarships for master's degree courses in Germany.</p>

  <h2>Key Details</h2>
  <p>Location: Bonn, Germany</p>
  <p>Application Deadline: 2026-07-31</p>
  <p>Opening Date: 2026-06-01</p>

  <h2>Funding & Benefits</h2>
  <p>This is a fully funded scholarship programme. The award provides a monthly stipend of €934 per month, travel allowance, and health insurance coverage.</p>

  <h2>Academic Requirements</h2>
  <p>Applicants must hold an accredited Bachelor degree with a minimum CGPA of 3.2 or equivalent 75% percentage.</p>
  <p>Eligible fields: Public Policy, Good Governance, International Relations, Law.</p>

  <h2>Language Proficiency</h2>
  <p>English language proficiency requirement: Minimum IELTS 6.5 overall band score or TOEFL iBT 90. English waivers are permitted for applicants whose previous degree was taught in English.</p>

  <h2>Application Portal</h2>
  <p>Free application with no application fee ($0). Apply online through the official portal: <a href="https://daad.de/apply">Submit Application</a></p>
</body>
</html>
"""

MISSING_DEADLINE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Future Global Leaders Grant</title></head>
<body>
  <h1>Future Global Leaders Grant</h1>
  <p>Offered by Global Leadership Foundation. Applications are evaluated continually.</p>
  <p>Funding: Fully funded scholarship with $2,000 monthly allowance in United States.</p>
  <p>No deadline has been determined for this cycle.</p>
</body>
</html>
"""

ROLLING_DEADLINE_HTML = """
<!DOCTYPE html>
<html>
<head><title>CERN Openlab Summer Internship</title></head>
<body>
  <h1>CERN Openlab Summer Internship</h1>
  <p>CERN offers an exciting summer internship in Switzerland for computing students.</p>
  <p>Applications are reviewed on a rolling basis. Candidates are encouraged to apply early as positions fill quickly.</p>
  <p>Funding: Partially funded with CHF 90 daily allowance.</p>
</body>
</html>
"""

MULTIPLE_DEADLINES_HTML = """
<!DOCTYPE html>
<html>
<head><title>Oxford Clarendon Fellowship</title></head>
<body>
  <h1>Oxford Clarendon Fellowship</h1>
  <p>University of Oxford offers premier graduate funding in United Kingdom.</p>
  <table>
    <tr><th>Stage</th><th>Date</th></tr>
    <tr><td>Application Deadline</td><td>2026-01-20</td></tr>
    <tr><td>Nomination Deadline</td><td>2026-02-15</td></tr>
    <tr><td>Document Deadline</td><td>2026-03-01</td></tr>
  </table>
  <p>Funding: Fully funded covering full tuition fees and £18,000 annual living stipend.</p>
</body>
</html>
"""

ENGLISH_WAIVER_HTML = """
<!DOCTYPE html>
<html>
<head><title>Stanford Postdoctoral Research Fellowship</title></head>
<body>
  <h1>Stanford Postdoctoral Research Fellowship</h1>
  <p>Stanford University offers research opportunities in United States.</p>
  <p>English Requirement: Minimum TOEFL 100 required. An English waiver is granted if your doctoral degree was taught in English.</p>
</body>
</html>
"""

NO_IELTS_REQUIRED_HTML = """
<!DOCTYPE html>
<html>
<head><title>Japanese Government MEXT Research Scholarship</title></head>
<body>
  <h1>Japanese Government MEXT Research Scholarship</h1>
  <p>Ministry of Education, Culture, Sports, Science and Technology in Japan.</p>
  <p>Language Requirements: No IELTS required. Japanese or English ability is assessed via interview.</p>
  <p>Funding: Fully funded with 143,000 JPY monthly allowance.</p>
</body>
</html>
"""

IELTS_NOT_MENTIONED_HTML = """
<!DOCTYPE html>
<html>
<head><title>European Quantum Computing Grant</title></head>
<body>
  <h1>European Quantum Computing Grant</h1>
  <p>Grant for quantum researchers in Europe. Funding up to €50,000 per project.</p>
  <p>Deadline: 2026-10-15</p>
  <!-- Note: Language requirements, IELTS, and TOEFL are completely omitted from this page -->
</body>
</html>
"""

FULLY_FUNDED_HTML = """
<!DOCTYPE html>
<html>
<head><title>Gates Cambridge Scholarship</title></head>
<body>
  <h1>Gates Cambridge Scholarship</h1>
  <p>University of Cambridge in United Kingdom.</p>
  <p>Funding: Fully funded. Covers university composition fee and maintenance allowance of £20,000 per annum.</p>
</body>
</html>
"""

PARTIALLY_FUNDED_HTML = """
<!DOCTYPE html>
<html>
<head><title>Melbourne International Undergraduate Fee Remission</title></head>
<body>
  <h1>Melbourne International Undergraduate Fee Remission</h1>
  <p>University of Melbourne in Australia.</p>
  <p>Funding: Partially funded with 50% tuition waiver for undergraduate degrees.</p>
</body>
</html>
"""

EXACT_FUNDING_AMOUNT_HTML = """
<!DOCTYPE html>
<html>
<head><title>Singapore International Graduate Award (SINGA)</title></head>
<body>
  <h1>Singapore International Graduate Award (SINGA)</h1>
  <p>A*STAR research institutes in Singapore.</p>
  <p>Stipend: Exact monthly stipend of SGD 2,700 per month, increasing to SGD 3,200 after qualifying exam.</p>
</body>
</html>
"""

FUNDING_NO_AMOUNT_HTML = """
<!DOCTYPE html>
<html>
<head><title>Nordic Climate Innovation Grant</title></head>
<body>
  <h1>Nordic Climate Innovation Grant</h1>
  <p>Funding is available for selected sustainable technology projects in Sweden.</p>
  <p>Funding type: Financial grant to support research equipment and staff.</p>
</body>
</html>
"""

CONFLICTING_SECONDARY_HTML = """
<!DOCTYPE html>
<html>
<head><title>DAAD Helmut-Schmidt-Programme Master Scholarships 2026 - Aggregator Info</title></head>
<body>
  <h1>DAAD Helmut-Schmidt-Programme Master Scholarships 2026</h1>
  <p>Summary from third-party scholarship aggregator portal.</p>
  <p>Application Deadline: 2026-09-30</p>
  <p>Funding: Stipend of €850 per month</p>
  <p>Application fee: $50 registration fee</p>
</body>
</html>
"""

TABLE_HEAVY_ELIGIBILITY_HTML = """
<!DOCTYPE html>
<html>
<head><title>ETH Zurich Excellence Scholarship Eligibility Table</title></head>
<body>
  <h1>ETH Zurich Excellence Scholarship Eligibility Table</h1>
  <p>Swiss Federal Institute of Technology in Switzerland.</p>
  <table>
    <thead><tr><th>Criterion</th><th>Requirement</th></tr></thead>
    <tbody>
      <tr><td>Degree Level</td><td>Master's Degree</td></tr>
      <tr><td>Minimum CGPA</td><td>Minimum 3.8 / 4.0</td></tr>
      <tr><td>Minimum Grade Percentage</td><td>85%</td></tr>
      <tr><td>IELTS Requirement</td><td>IELTS 7.0</td></tr>
      <tr><td>Deadline</td><td>2026-12-15</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

MULTIPAGE_OVERVIEW_HTML = """
<!DOCTYPE html>
<html>
<head><title>Rotary Peace Fellowship - Program Overview</title></head>
<body>
  <h1>Rotary Peace Fellowship</h1>
  <p>Rotary Foundation offers peace fellowships in United States, UK, Japan, Australia, and Sweden.</p>
  <p>Category: Fellowship for master's degree and professional development certificate.</p>
</body>
</html>
"""

MULTIPAGE_FUNDING_HTML = """
<!DOCTYPE html>
<html>
<head><title>Rotary Peace Fellowship - Funding & Deadlines</title></head>
<body>
  <h1>Rotary Peace Fellowship - Funding Details</h1>
  <p>The fellowship is fully funded covering tuition and fees, room and board, round-trip transportation, and all internship and field-study expenses.</p>
  <p>Application Deadline: 2026-05-15</p>
  <p>Online portal: <a href="https://rotary.org/apply">Apply Now</a></p>
</body>
</html>
"""

TRACKING_URLS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Schwarzman Scholars at Tsinghua University</title></head>
<body>
  <h1>Schwarzman Scholars</h1>
  <p>Master's degree in Global Affairs at Tsinghua University in China.</p>
  <p>Funding: Fully funded scholarship.</p>
  <p>Application Deadline: 2026-09-19</p>
</body>
</html>
"""

NO_OPPORTUNITY_HTML = """
<!DOCTYPE html>
<html>
<head><title>University Campus Map and Parking Guide</title></head>
<body>
  <h1>Campus Map & Parking Information</h1>
  <p>Find parking garages, visitor lots, and bike stations across the central campus.</p>
  <p>Permits are required Monday through Friday from 7 AM to 5 PM.</p>
</body>
</html>
"""

NOISY_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Top Scholarships Today - Sponsored Ads</title></head>
<body>
  <div class="banner-ad">Advertisement: Best Student Credit Cards 2026!</div>
  <div class="nav">Home | About | Contact | Privacy | Disclaimer</div>
  <h1>Commonwealth Master's Scholarships</h1>
  <p>For candidates from eligible low and middle-income Commonwealth countries in United Kingdom.</p>
  <p>Fully funded scholarship with £1,330 monthly stipend.</p>
  <p>Deadline: 2026-10-17</p>
  <div class="footer-ad">Sponsored Links: Cheap Flights for Students</div>
</body>
</html>
"""

INCOMPLETE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Scholarship</title></head>
<body>
  <h1>Scholarship Information</h1>
  <p>Loading details...</p>
</body>
</html>
"""


def build_synthetic_document(
    title: str,
    html: str,
    url: str,
    domain: str,
    page_type: PageType = PageType.OPPORTUNITY_PAGE,
) -> WebDocument:
    from app.web.extraction.date_extractor import DateExtractor
    from app.web.extraction.html_parser import parse_html_tree
    from app.web.extraction.link_extractor import LinkExtractor
    from app.web.extraction.main_content import MainContentExtractor
    from app.web.extraction.table_extractor import TableExtractor

    tree = parse_html_tree(html)
    tables = TableExtractor.extract_tables(tree)
    links = LinkExtractor.extract_links(tree, url)
    clean_text, headings, word_count = MainContentExtractor.extract_clean_content(tree, tables)
    extracted_dates = DateExtractor.extract_dates(clean_text)

    return WebDocument(
        id=uuid.uuid4(),
        original_url=url,
        final_url=url,
        domain=domain,
        title=title,
        clean_text=clean_text,
        headings=headings,
        tables=tables,
        links=links,
        extracted_dates=extracted_dates,
        page_type=page_type,
        word_count=word_count,
        content_quality=ContentQualityScore(composite_score=0.9),
    )
