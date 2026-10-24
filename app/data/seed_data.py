"""Seed realistic global opportunities for local development and beta testing."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.discovery import get_discovery_engine, get_discovery_indexer
from app.models.opportunity import (
    Opportunity,
    OpportunityCategory,
    OpportunityEvidence,
    OpportunityRequirement,
    OpportunitySource,
    OpportunityStatus,
    RequirementOperator,
    SourceType,
)

logger = logging.getLogger(__name__)

SEED_OPPORTUNITIES = [
    {
        "title": "DAAD Helmut-Schmidt-Programme (Public Policy & Good Governance)",
        "organization": "German Academic Exchange Service (DAAD)",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "Full scholarship for future leaders from developing countries wanting to pursue a Master's degree in public policy, governance, and development in Germany.",
        "country": "Germany",
        "eligible_countries": ["Global", "Developing Countries", "Pakistan", "India", "Nigeria", "Egypt"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's"],
        "fields": ["Public Policy", "Economics", "Law", "Social Sciences", "Political Science"],
        "funding_type": "Fully Funded",
        "funding_amount": "€934/month + tuition + travel",
        "currency": "EUR",
        "opening_date": date(2026, 6, 1),
        "deadline": date(2026, 11, 30),
        "application_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/helmut-schmidt-programme/",
        "official_source_url": "https://www.daad.de/en/",
        "source_domain": "daad.de",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Erasmus Mundus Joint Master Degree in Artificial Intelligence & Data Science",
        "organization": "European Commission",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "High-level integrated international study programme delivered by an international consortium of higher education institutions across Europe.",
        "country": "European Union",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's"],
        "fields": ["Computer Science", "Artificial Intelligence", "Data Science", "Software Engineering"],
        "funding_type": "Fully Funded",
        "funding_amount": "€1,400/month + full tuition + travel allowance",
        "currency": "EUR",
        "opening_date": date(2026, 9, 1),
        "deadline": date(2026, 12, 31),
        "application_url": "https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters",
        "official_source_url": "https://erasmus-plus.ec.europa.eu/",
        "source_domain": "europa.eu",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Fulbright Foreign Student Program",
        "organization": "United States Department of State",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "Enables graduate students, young professionals and artists from abroad to study and conduct research in the United States.",
        "country": "United States",
        "eligible_countries": ["Global", "Pakistan", "India", "Turkey", "Indonesia", "Brazil"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's", "PhD"],
        "fields": ["All Fields", "Engineering", "Humanities", "Natural Sciences", "Social Sciences"],
        "funding_type": "Fully Funded",
        "funding_amount": "Full tuition, living stipend, airfare, health insurance",
        "currency": "USD",
        "opening_date": date(2026, 2, 1),
        "deadline": date(2026, 12, 15),
        "application_url": "https://foreign.fulbrightonline.org/",
        "official_source_url": "https://fulbrightonline.org/",
        "source_domain": "fulbrightonline.org",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "CERN Summer Student Programme 2027",
        "organization": "European Organization for Nuclear Research (CERN)",
        "category": OpportunityCategory.INTERNSHIP,
        "description": "Join multidisciplinary research teams in Geneva, Switzerland. Work on state-of-the-art physics, computing, and engineering projects.",
        "country": "Switzerland",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Undergraduate", "Master's"],
        "fields": ["Physics", "Computer Science", "Engineering", "Mathematics"],
        "funding_type": "Fully Funded",
        "funding_amount": "CHF 90/day stipend + travel allowance",
        "currency": "CHF",
        "opening_date": date(2026, 8, 1),
        "deadline": date(2026, 11, 15),
        "application_url": "https://careers.cern/summer-student-programme",
        "official_source_url": "https://home.cern/",
        "source_domain": "cern.ch",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Gates Cambridge Scholarship",
        "organization": "University of Cambridge",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "Prestigious international postgraduate scholarship awarded to outstanding applicants from countries outside the UK to pursue a full-time postgraduate degree at Cambridge.",
        "country": "United Kingdom",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Non-UK"],
        "degree_levels": ["Master's", "PhD"],
        "fields": ["All Subjects", "Biotechnology", "Computer Science", "Medicine"],
        "funding_type": "Fully Funded",
        "funding_amount": "£20,000/year living allowance + full university fees",
        "currency": "GBP",
        "opening_date": date(2026, 9, 1),
        "deadline": date(2026, 12, 5),
        "application_url": "https://www.gatescambridge.org/apply/",
        "official_source_url": "https://www.gatescambridge.org/",
        "source_domain": "gatescambridge.org",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Max Planck Research Fellowship in Intelligent Systems",
        "organization": "Max Planck Institute",
        "category": OpportunityCategory.FELLOWSHIP,
        "description": "Fellowship supporting exceptionally qualified early-stage researchers in machine learning, computer vision, robotics, and cybernetics.",
        "country": "Germany",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's", "PhD", "Postdoc"],
        "fields": ["Computer Science", "Robotics", "Artificial Intelligence", "Neuroscience"],
        "funding_type": "Fully Funded",
        "funding_amount": "€2,100/month research stipend",
        "currency": "EUR",
        "opening_date": date(2026, 7, 1),
        "deadline": date(2026, 11, 20),
        "application_url": "https://is.mpg.de/fellowships",
        "official_source_url": "https://www.mpg.de/en",
        "source_domain": "mpg.de",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "MEXT Japanese Government Research Scholarship",
        "organization": "Ministry of Education, Culture, Sports, Science and Technology (Japan)",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "Full scholarship for international graduate students to study at leading Japanese universities in Tokyo, Kyoto, Osaka, and Tohoku.",
        "country": "Japan",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's", "PhD"],
        "fields": ["Engineering", "Medicine", "Humanities", "Natural Sciences"],
        "funding_type": "Fully Funded",
        "funding_amount": "144,000 JPY/month + full tuition waiver + flights",
        "currency": "JPY",
        "opening_date": date(2026, 4, 1),
        "deadline": date(2026, 12, 20),
        "application_url": "https://www.studyinjapan.go.jp/en/planning/scholarship/mext-scholarships/",
        "official_source_url": "https://www.mext.go.jp/en/",
        "source_domain": "mext.go.jp",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Google Generation Scholarship (EMEA & Global)",
        "organization": "Google",
        "category": OpportunityCategory.GRANT,
        "description": "Supports women and underrepresented students in computer science, computer engineering, or related technical fields to excel in technology leadership.",
        "country": "Global",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Undergraduate", "Master's", "PhD"],
        "fields": ["Computer Science", "Computer Engineering", "Data Science"],
        "funding_type": "Partial Grant",
        "funding_amount": "€7,000 merit grant + Google retreat",
        "currency": "EUR",
        "opening_date": date(2026, 8, 15),
        "deadline": date(2026, 11, 25),
        "application_url": "https://buildyourfuture.withgoogle.com/scholarships/generation-google-scholarship-emea",
        "official_source_url": "https://buildyourfuture.withgoogle.com/",
        "source_domain": "google.com",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "ETH Zurich Excellence Masters Scholarship (ESOP)",
        "organization": "ETH Zurich",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "Supports outstanding international students with a grant covering study and living costs, and a tuition fee waiver at Switzerland's top technical university.",
        "country": "Switzerland",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's"],
        "fields": ["Architecture", "Engineering", "Mathematics", "Natural Sciences", "Computer Science"],
        "funding_type": "Fully Funded",
        "funding_amount": "CHF 12,000/semester + tuition waiver",
        "currency": "CHF",
        "opening_date": date(2026, 10, 1),
        "deadline": date(2026, 12, 15),
        "application_url": "https://ethz.ch/en/studies/financial/scholarships/excellence-scholarships.html",
        "official_source_url": "https://ethz.ch/en.html",
        "source_domain": "ethz.ch",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "MIT Summer Research Program (MSRP)",
        "organization": "Massachusetts Institute of Technology",
        "category": OpportunityCategory.INTERNSHIP,
        "description": "Intensive nine-week research internship on MIT's campus in Cambridge, MA. Fellows conduct cutting-edge research under faculty supervision.",
        "country": "United States",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Undergraduate"],
        "fields": ["Engineering", "Biology", "Cognitive Science", "Physics", "Chemistry"],
        "funding_type": "Fully Funded",
        "funding_amount": "$4,500 stipend + campus housing + travel",
        "currency": "USD",
        "opening_date": date(2026, 8, 1),
        "deadline": date(2026, 11, 10),
        "application_url": "https://gradapply.mit.edu/msrp",
        "official_source_url": "https://mit.edu/",
        "source_domain": "mit.edu",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Chevening Scholarships for Global Leaders",
        "organization": "Foreign, Commonwealth & Development Office (UK)",
        "category": OpportunityCategory.SCHOLARSHIP,
        "description": "The UK government’s international awards programme aimed at developing global leaders. Covers full one-year master's degrees at any UK university.",
        "country": "United Kingdom",
        "eligible_countries": ["Global", "Chevening-eligible countries"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["Master's"],
        "fields": ["All Fields", "Business", "International Relations", "Public Health", "Climate Science"],
        "funding_type": "Fully Funded",
        "funding_amount": "Full tuition fees + monthly stipend + travel costs",
        "currency": "GBP",
        "opening_date": date(2026, 8, 1),
        "deadline": date(2026, 11, 5),
        "application_url": "https://www.chevening.org/scholarships/",
        "official_source_url": "https://www.chevening.org/",
        "source_domain": "chevening.org",
        "status": OpportunityStatus.ACTIVE,
    },
    {
        "title": "Swiss Government Excellence Scholarships",
        "organization": "Federal Commission for Scholarships for Foreign Students (FCS)",
        "category": OpportunityCategory.FELLOWSHIP,
        "description": "Aimed at young researchers abroad who have completed a master's degree or PhD and at foreign artists holding a bachelor's degree.",
        "country": "Switzerland",
        "eligible_countries": ["Global"],
        "eligible_nationalities": ["Global"],
        "degree_levels": ["PhD", "Postdoc"],
        "fields": ["All Academic Fields", "Life Sciences", "Renewable Energy"],
        "funding_type": "Fully Funded",
        "funding_amount": "CHF 1,920/month stipend + health insurance + flight",
        "currency": "CHF",
        "opening_date": date(2026, 8, 1),
        "deadline": date(2026, 12, 1),
        "application_url": "https://www.sbfi.admin.ch/sbfi/en/home/education/scholarships-and-grants/swiss-government-excellence-scholarships.html",
        "official_source_url": "https://www.sbfi.admin.ch/",
        "source_domain": "admin.ch",
        "status": OpportunityStatus.ACTIVE,
    },
]


async def seed_database_if_empty() -> int:
    """Checks opportunity count and seeds initial verified opportunities if empty."""
    async with async_session_factory() as session:
        count = await session.scalar(select(func.count(Opportunity.id)))
        if count and count > 0:
            logger.info("Database already contains %d opportunities. Skipping seed.", count)
            return count

        logger.info("Database has 0 opportunities. Seeding %d verified opportunities...", len(SEED_OPPORTUNITIES))
        created_opps: list[Opportunity] = []

        now = datetime.now(timezone.utc)
        for data in SEED_OPPORTUNITIES:
            opp_id = uuid.uuid4()
            opp = Opportunity(
                id=opp_id,
                title=data["title"],
                organization=data["organization"],
                category=data["category"],
                description=data["description"],
                country=data["country"],
                eligible_countries=data["eligible_countries"],
                eligible_nationalities=data["eligible_nationalities"],
                degree_levels=data["degree_levels"],
                fields=data["fields"],
                funding_type=data["funding_type"],
                funding_amount=data["funding_amount"],
                currency=data["currency"],
                opening_date=data["opening_date"],
                deadline=data["deadline"],
                application_url=data["application_url"],
                official_source_url=data["official_source_url"],
                source_domain=data["source_domain"],
                status=data["status"],
                last_verified_at=now,
            )
            # Add official source
            source = OpportunitySource(
                id=uuid.uuid4(),
                opportunity_id=opp_id,
                url=data["official_source_url"],
                domain=data["source_domain"],
                source_type=SourceType.OFFICIAL_WEBSITE,
                is_official=True,
                verification_status="verified",
                last_checked_at=now,
            )
            # Add requirement
            req = OpportunityRequirement(
                id=uuid.uuid4(),
                opportunity_id=opp_id,
                requirement_type="degree_level",
                operator=RequirementOperator.EQUALS,
                value=data["degree_levels"],
                is_mandatory=True,
            )
            # Add evidence
            evidence = OpportunityEvidence(
                id=uuid.uuid4(),
                opportunity_id=opp_id,
                source_url=data["official_source_url"],
                field_name="funding_amount",
                evidence_text=f"Official funding coverage: {data['funding_amount']}",
                confidence=1.0,
            )
            opp.sources.append(source)
            opp.requirements.append(req)
            opp.evidences.append(evidence)

            session.add(opp)
            created_opps.append(opp)

        await session.commit()
        logger.info("Successfully persisted %d opportunities in SQLite.", len(created_opps))

        # Re-index all into discovery engine / vector store
        try:
            engine = get_discovery_engine()
            indexer = get_discovery_indexer()
            res = await indexer.reindex_all(session)
            logger.info("Indexed opportunities into Discovery Engine: %s", res)
        except Exception as exc:
            logger.warning("Could not index opportunities immediately: %s", exc)

        return len(created_opps)


if __name__ == "__main__":
    asyncio.run(seed_database_if_empty())
