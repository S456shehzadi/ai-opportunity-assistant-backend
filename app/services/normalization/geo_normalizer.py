from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class CountryInfo:
    code: str  # ISO 3166-1 alpha-2
    name: str  # Official / Common English name
    region: str  # e.g., Western Europe, North America, South Asia, East Africa
    continent: str  # Americas, Europe, Asia, Africa, Oceania
    aliases: tuple[str, ...] = ()


class GeoNormalizer:
    """Normalizes country names, aliases, and geographic regions.

    Uses ISO 3166-1 alpha-2 standard identifiers and geographic hierarchies.
    Covers all sovereign states and key territories worldwide.
    """

    COUNTRIES: ClassVar[dict[str, CountryInfo]] = {
        # --- NORTH AMERICA ---
        "US": CountryInfo(
            code="US",
            name="United States",
            region="North America",
            continent="Americas",
            aliases=("usa", "united states", "united states of america", "us", "america", "u.s.", "u.s.a."),
        ),
        "CA": CountryInfo(
            code="CA",
            name="Canada",
            region="North America",
            continent="Americas",
            aliases=("canada", "ca", "can"),
        ),
        "MX": CountryInfo(
            code="MX",
            name="Mexico",
            region="North America",
            continent="Americas",
            aliases=("mexico", "mex", "mx", "méxico"),
        ),
        # --- WESTERN & NORTHERN EUROPE ---
        "GB": CountryInfo(
            code="GB",
            name="United Kingdom",
            region="Western Europe",
            continent="Europe",
            aliases=("united kingdom", "uk", "great britain", "britain", "england", "scotland", "wales", "u.k.", "gb"),
        ),
        "DE": CountryInfo(
            code="DE",
            name="Germany",
            region="Western Europe",
            continent="Europe",
            aliases=("germany", "deutschland", "de", "deu"),
        ),
        "FR": CountryInfo(
            code="FR",
            name="France",
            region="Western Europe",
            continent="Europe",
            aliases=("france", "fr", "fra", "french republic"),
        ),
        "NL": CountryInfo(
            code="NL",
            name="Netherlands",
            region="Western Europe",
            continent="Europe",
            aliases=("netherlands", "holland", "nl", "nld", "the netherlands"),
        ),
        "CH": CountryInfo(
            code="CH",
            name="Switzerland",
            region="Western Europe",
            continent="Europe",
            aliases=("switzerland", "swiss", "ch", "che", "suisse", "schweiz"),
        ),
        "BE": CountryInfo(
            code="BE",
            name="Belgium",
            region="Western Europe",
            continent="Europe",
            aliases=("belgium", "be", "bel"),
        ),
        "AT": CountryInfo(
            code="AT",
            name="Austria",
            region="Western Europe",
            continent="Europe",
            aliases=("austria", "at", "aut", "österreich"),
        ),
        "IE": CountryInfo(
            code="IE",
            name="Ireland",
            region="Western Europe",
            continent="Europe",
            aliases=("ireland", "ie", "irl", "republic of ireland"),
        ),
        "LU": CountryInfo(
            code="LU",
            name="Luxembourg",
            region="Western Europe",
            continent="Europe",
            aliases=("luxembourg", "lu", "lux"),
        ),
        "SE": CountryInfo(
            code="SE",
            name="Sweden",
            region="Northern Europe",
            continent="Europe",
            aliases=("sweden", "se", "swe", "sverige"),
        ),
        "NO": CountryInfo(
            code="NO",
            name="Norway",
            region="Northern Europe",
            continent="Europe",
            aliases=("norway", "no", "nor", "norge"),
        ),
        "DK": CountryInfo(
            code="DK",
            name="Denmark",
            region="Northern Europe",
            continent="Europe",
            aliases=("denmark", "dk", "dnk", "danmark"),
        ),
        "FI": CountryInfo(
            code="FI",
            name="Finland",
            region="Northern Europe",
            continent="Europe",
            aliases=("finland", "fi", "fin", "suomi"),
        ),
        # --- SOUTHERN & EASTERN EUROPE ---
        "IT": CountryInfo(
            code="IT",
            name="Italy",
            region="Southern Europe",
            continent="Europe",
            aliases=("italy", "italia", "it", "ita"),
        ),
        "ES": CountryInfo(
            code="ES",
            name="Spain",
            region="Southern Europe",
            continent="Europe",
            aliases=("spain", "espana", "es", "esp", "españa"),
        ),
        "PT": CountryInfo(
            code="PT",
            name="Portugal",
            region="Southern Europe",
            continent="Europe",
            aliases=("portugal", "pt", "prt"),
        ),
        "GR": CountryInfo(
            code="GR",
            name="Greece",
            region="Southern Europe",
            continent="Europe",
            aliases=("greece", "gr", "grc", "hellas"),
        ),
        "PL": CountryInfo(
            code="PL",
            name="Poland",
            region="Eastern Europe",
            continent="Europe",
            aliases=("poland", "pl", "pol", "polska"),
        ),
        "CZ": CountryInfo(
            code="CZ",
            name="Czech Republic",
            region="Eastern Europe",
            continent="Europe",
            aliases=("czech republic", "czechia", "cz", "cze"),
        ),
        "HU": CountryInfo(
            code="HU",
            name="Hungary",
            region="Eastern Europe",
            continent="Europe",
            aliases=("hungary", "hu", "hun"),
        ),
        "RO": CountryInfo(
            code="RO",
            name="Romania",
            region="Eastern Europe",
            continent="Europe",
            aliases=("romania", "ro", "rou"),
        ),
        "UA": CountryInfo(
            code="UA",
            name="Ukraine",
            region="Eastern Europe",
            continent="Europe",
            aliases=("ukraine", "ua", "ukr"),
        ),
        "TR": CountryInfo(
            code="TR",
            name="Turkey",
            region="Southern Europe",
            continent="Europe",
            aliases=("turkey", "turkiye", "tr", "tur", "türkiye"),
        ),
        # --- ASIA ---
        "JP": CountryInfo(
            code="JP",
            name="Japan",
            region="East Asia",
            continent="Asia",
            aliases=("japan", "nippon", "jp", "jpn"),
        ),
        "KR": CountryInfo(
            code="KR",
            name="South Korea",
            region="East Asia",
            continent="Asia",
            aliases=("south korea", "korea", "republic of korea", "kr", "kor"),
        ),
        "CN": CountryInfo(
            code="CN",
            name="China",
            region="East Asia",
            continent="Asia",
            aliases=("china", "prc", "cn", "chn", "people's republic of china"),
        ),
        "TW": CountryInfo(
            code="TW",
            name="Taiwan",
            region="East Asia",
            continent="Asia",
            aliases=("taiwan", "tw", "twn"),
        ),
        "HK": CountryInfo(
            code="HK",
            name="Hong Kong",
            region="East Asia",
            continent="Asia",
            aliases=("hong kong", "hk", "hkg"),
        ),
        "SG": CountryInfo(
            code="SG",
            name="Singapore",
            region="Southeast Asia",
            continent="Asia",
            aliases=("singapore", "sg", "sgp"),
        ),
        "MY": CountryInfo(
            code="MY",
            name="Malaysia",
            region="Southeast Asia",
            continent="Asia",
            aliases=("malaysia", "my", "mys"),
        ),
        "ID": CountryInfo(
            code="ID",
            name="Indonesia",
            region="Southeast Asia",
            continent="Asia",
            aliases=("indonesia", "id", "idn"),
        ),
        "TH": CountryInfo(
            code="TH",
            name="Thailand",
            region="Southeast Asia",
            continent="Asia",
            aliases=("thailand", "th", "tha"),
        ),
        "VN": CountryInfo(
            code="VN",
            name="Vietnam",
            region="Southeast Asia",
            continent="Asia",
            aliases=("vietnam", "vn", "vnm"),
        ),
        "PH": CountryInfo(
            code="PH",
            name="Philippines",
            region="Southeast Asia",
            continent="Asia",
            aliases=("philippines", "ph", "phl"),
        ),
        "PK": CountryInfo(
            code="PK",
            name="Pakistan",
            region="South Asia",
            continent="Asia",
            aliases=("pakistan", "pk", "pak", "islamic republic of pakistan"),
        ),
        "IN": CountryInfo(
            code="IN",
            name="India",
            region="South Asia",
            continent="Asia",
            aliases=("india", "in", "ind", "bharat"),
        ),
        "BD": CountryInfo(
            code="BD",
            name="Bangladesh",
            region="South Asia",
            continent="Asia",
            aliases=("bangladesh", "bd", "bgd"),
        ),
        "LK": CountryInfo(
            code="LK",
            name="Sri Lanka",
            region="South Asia",
            continent="Asia",
            aliases=("sri lanka", "lk", "lka"),
        ),
        "NP": CountryInfo(
            code="NP",
            name="Nepal",
            region="South Asia",
            continent="Asia",
            aliases=("nepal", "np", "npl"),
        ),
        "KZ": CountryInfo(
            code="KZ",
            name="Kazakhstan",
            region="Central Asia",
            continent="Asia",
            aliases=("kazakhstan", "kz", "kaz"),
        ),
        "UZ": CountryInfo(
            code="UZ",
            name="Uzbekistan",
            region="Central Asia",
            continent="Asia",
            aliases=("uzbekistan", "uz", "uzb"),
        ),
        # --- MIDDLE EAST ---
        "SA": CountryInfo(
            code="SA",
            name="Saudi Arabia",
            region="Middle East",
            continent="Asia",
            aliases=("saudi arabia", "ksa", "saudi", "sa", "sau"),
        ),
        "AE": CountryInfo(
            code="AE",
            name="United Arab Emirates",
            region="Middle East",
            continent="Asia",
            aliases=("united arab emirates", "uae", "emirates", "dubai", "ae", "are"),
        ),
        "QA": CountryInfo(
            code="QA",
            name="Qatar",
            region="Middle East",
            continent="Asia",
            aliases=("qatar", "qa", "qat"),
        ),
        "KW": CountryInfo(
            code="KW",
            name="Kuwait",
            region="Middle East",
            continent="Asia",
            aliases=("kuwait", "kw", "kwt"),
        ),
        "OM": CountryInfo(
            code="OM",
            name="Oman",
            region="Middle East",
            continent="Asia",
            aliases=("oman", "om", "omn"),
        ),
        "JO": CountryInfo(
            code="JO",
            name="Jordan",
            region="Middle East",
            continent="Asia",
            aliases=("jordan", "jo", "jor"),
        ),
        "IL": CountryInfo(
            code="IL",
            name="Israel",
            region="Middle East",
            continent="Asia",
            aliases=("israel", "il", "isr"),
        ),
        # --- OCEANIA ---
        "AU": CountryInfo(
            code="AU",
            name="Australia",
            region="Oceania",
            continent="Oceania",
            aliases=("australia", "aus", "au"),
        ),
        "NZ": CountryInfo(
            code="NZ",
            name="New Zealand",
            region="Oceania",
            continent="Oceania",
            aliases=("new zealand", "nz", "nzl", "aotearoa"),
        ),
        # --- AFRICA ---
        "EG": CountryInfo(
            code="EG",
            name="Egypt",
            region="North Africa",
            continent="Africa",
            aliases=("egypt", "eg", "egy"),
        ),
        "ZA": CountryInfo(
            code="ZA",
            name="South Africa",
            region="Southern Africa",
            continent="Africa",
            aliases=("south africa", "za", "zaf"),
        ),
        "NG": CountryInfo(
            code="NG",
            name="Nigeria",
            region="West Africa",
            continent="Africa",
            aliases=("nigeria", "ng", "nga"),
        ),
        "KE": CountryInfo(
            code="KE",
            name="Kenya",
            region="East Africa",
            continent="Africa",
            aliases=("kenya", "ke", "ken"),
        ),
        "GH": CountryInfo(
            code="GH",
            name="Ghana",
            region="West Africa",
            continent="Africa",
            aliases=("ghana", "gh", "gha"),
        ),
        "MA": CountryInfo(
            code="MA",
            name="Morocco",
            region="North Africa",
            continent="Africa",
            aliases=("morocco", "ma", "mar"),
        ),
        "RW": CountryInfo(
            code="RW",
            name="Rwanda",
            region="East Africa",
            continent="Africa",
            aliases=("rwanda", "rw", "rwa"),
        ),
        "ET": CountryInfo(
            code="ET",
            name="Ethiopia",
            region="East Africa",
            continent="Africa",
            aliases=("ethiopia", "et", "eth"),
        ),
        # --- LATIN AMERICA & CARIBBEAN ---
        "BR": CountryInfo(
            code="BR",
            name="Brazil",
            region="South America",
            continent="Americas",
            aliases=("brazil", "brasil", "br", "bra"),
        ),
        "AR": CountryInfo(
            code="AR",
            name="Argentina",
            region="South America",
            continent="Americas",
            aliases=("argentina", "ar", "arg"),
        ),
        "CL": CountryInfo(
            code="CL",
            name="Chile",
            region="South America",
            continent="Americas",
            aliases=("chile", "cl", "chl"),
        ),
        "CO": CountryInfo(
            code="CO",
            name="Colombia",
            region="South America",
            continent="Americas",
            aliases=("colombia", "co", "col"),
        ),
        "JM": CountryInfo(
            code="JM",
            name="Jamaica",
            region="The Caribbean",
            continent="Americas",
            aliases=("jamaica", "jm", "jam"),
        ),
        "TT": CountryInfo(
            code="TT",
            name="Trinidad and Tobago",
            region="The Caribbean",
            continent="Americas",
            aliases=("trinidad and tobago", "trinidad", "tt", "tto"),
        ),
    }

    # Macro Regions & Country Groups Mapping
    REGIONS: ClassVar[dict[str, list[str]]] = {
        "europe": ["DE", "GB", "FR", "IT", "ES", "NL", "CH", "SE", "NO", "DK", "FI", "BE", "AT", "IE", "LU", "PT", "GR", "PL", "CZ", "HU", "RO", "UA", "TR"],
        "western europe": ["DE", "GB", "FR", "NL", "CH", "BE", "AT", "IE", "LU"],
        "northern europe": ["SE", "NO", "DK", "FI", "GB", "IE"],
        "southern europe": ["IT", "ES", "PT", "GR", "TR"],
        "eastern europe": ["PL", "CZ", "HU", "RO", "UA"],
        "european union": ["DE", "FR", "IT", "ES", "NL", "SE", "DK", "FI", "BE", "AT", "IE", "LU", "PT", "GR", "PL", "CZ", "HU", "RO"],
        "eu": ["DE", "FR", "IT", "ES", "NL", "SE", "DK", "FI", "BE", "AT", "IE", "LU", "PT", "GR", "PL", "CZ", "HU", "RO"],
        "north america": ["US", "CA", "MX"],
        "asia": ["JP", "KR", "CN", "TW", "HK", "SG", "MY", "ID", "TH", "VN", "PH", "PK", "IN", "BD", "LK", "NP", "KZ", "UZ", "SA", "AE", "QA", "KW", "OM", "JO", "IL"],
        "south asia": ["PK", "IN", "BD", "LK", "NP"],
        "east asia": ["JP", "KR", "CN", "TW", "HK"],
        "southeast asia": ["SG", "MY", "ID", "TH", "VN", "PH"],
        "central asia": ["KZ", "UZ"],
        "middle east": ["SA", "AE", "QA", "KW", "OM", "JO", "IL", "TR"],
        "oceania": ["AU", "NZ"],
        "africa": ["EG", "ZA", "NG", "KE", "GH", "MA", "RW", "ET"],
        "north africa": ["EG", "MA"],
        "sub-saharan africa": ["ZA", "NG", "KE", "GH", "RW", "ET"],
        "south america": ["BR", "AR", "CL", "CO"],
        "latin america": ["BR", "AR", "CL", "CO", "MX"],
        "the caribbean": ["JM", "TT"],
        "caribbean": ["JM", "TT"],
        "commonwealth": ["GB", "CA", "AU", "NZ", "IN", "PK", "BD", "LK", "MY", "SG", "NG", "ZA", "KE", "GH", "JM", "TT"],
        "worldwide": [],
        "global": [],
        "anywhere": [],
    }

    _LOOKUP_INDEX: ClassVar[dict[str, CountryInfo]] = {}

    @classmethod
    def _get_lookup_index(cls) -> dict[str, CountryInfo]:
        if not cls._LOOKUP_INDEX:
            for country in cls.COUNTRIES.values():
                cls._LOOKUP_INDEX[country.code.lower()] = country
                cls._LOOKUP_INDEX[country.name.lower()] = country
                for alias in country.aliases:
                    cls._LOOKUP_INDEX[alias.lower()] = country
        return cls._LOOKUP_INDEX

    @classmethod
    def normalize_country(cls, text: str | None) -> CountryInfo | None:
        """Resolve any country name, code, or alias into a standardized CountryInfo."""
        if not text:
            return None
        cleaned = text.strip().lower()
        lookup = cls._get_lookup_index()
        return lookup.get(cleaned)

    @classmethod
    def normalize_region(cls, text: str | None) -> str | None:
        """Resolve region mentions to standard canonical region name."""
        if not text:
            return None
        cleaned = text.strip().lower()
        region_map = {
            "worldwide": "Worldwide",
            "global": "Worldwide",
            "anywhere": "Worldwide",
            "international": "Worldwide",
            "europe": "Europe",
            "european": "Europe",
            "western europe": "Western Europe",
            "northern europe": "Northern Europe",
            "southern europe": "Southern Europe",
            "eastern europe": "Eastern Europe",
            "european union": "European Union",
            "eu": "European Union",
            "north america": "North America",
            "asia": "Asia",
            "south asia": "South Asia",
            "east asia": "East Asia",
            "southeast asia": "Southeast Asia",
            "central asia": "Central Asia",
            "middle east": "Middle East",
            "oceania": "Oceania",
            "africa": "Africa",
            "south america": "South America",
            "latin america": "Latin America",
            "caribbean": "The Caribbean",
            "the caribbean": "The Caribbean",
            "commonwealth": "Commonwealth",
        }
        return region_map.get(cleaned)

    @classmethod
    def is_in_region(cls, country_code: str, region_name: str) -> bool:
        """Check if a country code belongs to a given region name."""
        region_key = region_name.strip().lower()
        if region_key in ("global", "worldwide", "anywhere"):
            return True
        member_codes = cls.REGIONS.get(region_key, [])
        if country_code.upper() in member_codes:
            return True
        country = cls.COUNTRIES.get(country_code.upper())
        if country and (
            country.continent.lower() == region_key or country.region.lower() == region_key
        ):
            return True
        return False

    @classmethod
    def get_countries_for_region(cls, region_name: str) -> list[CountryInfo]:
        """Return list of CountryInfo records belonging to a region."""
        region_key = region_name.strip().lower()
        if region_key in ("global", "worldwide", "anywhere"):
            return list(cls.COUNTRIES.values())
        codes = cls.REGIONS.get(region_key, [])
        result = [cls.COUNTRIES[c] for c in codes if c in cls.COUNTRIES]
        return result
