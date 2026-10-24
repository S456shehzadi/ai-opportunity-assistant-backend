from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class CountryInfo:
    code: str  # ISO 3166-1 alpha-2
    name: str  # Official/Common English name
    region: str  # e.g., Western Europe, North America, South Asia
    continent: str  # Americas, Europe, Asia, Africa, Oceania
    aliases: tuple[str, ...] = ()


class GeoNormalizer:
    """Normalizes country names, aliases, and geographic regions.

    Uses ISO 3166-1 alpha-2 standard identifiers and geographic hierarchies.
    """

    COUNTRIES: ClassVar[dict[str, CountryInfo]] = {
        "US": CountryInfo(
            code="US",
            name="United States",
            region="North America",
            continent="Americas",
            aliases=(
                "usa",
                "united states",
                "united states of america",
                "us",
                "america",
                "u.s.",
                "u.s.a.",
            ),
        ),
        "DE": CountryInfo(
            code="DE",
            name="Germany",
            region="Western Europe",
            continent="Europe",
            aliases=("germany", "deutschland", "de"),
        ),
        "GB": CountryInfo(
            code="GB",
            name="United Kingdom",
            region="Western Europe",
            continent="Europe",
            aliases=(
                "united kingdom",
                "uk",
                "great britain",
                "britain",
                "england",
                "scotland",
                "wales",
                "u.k.",
            ),
        ),
        "CA": CountryInfo(
            code="CA",
            name="Canada",
            region="North America",
            continent="Americas",
            aliases=("canada", "ca"),
        ),
        "AU": CountryInfo(
            code="AU",
            name="Australia",
            region="Oceania",
            continent="Oceania",
            aliases=("australia", "aus", "au"),
        ),
        "FR": CountryInfo(
            code="FR",
            name="France",
            region="Western Europe",
            continent="Europe",
            aliases=("france", "fr"),
        ),
        "IT": CountryInfo(
            code="IT",
            name="Italy",
            region="Southern Europe",
            continent="Europe",
            aliases=("italy", "italia", "it"),
        ),
        "ES": CountryInfo(
            code="ES",
            name="Spain",
            region="Southern Europe",
            continent="Europe",
            aliases=("spain", "espana", "es"),
        ),
        "NL": CountryInfo(
            code="NL",
            name="Netherlands",
            region="Western Europe",
            continent="Europe",
            aliases=("netherlands", "holland", "nl"),
        ),
        "CH": CountryInfo(
            code="CH",
            name="Switzerland",
            region="Western Europe",
            continent="Europe",
            aliases=("switzerland", "swiss", "ch"),
        ),
        "SE": CountryInfo(
            code="SE",
            name="Sweden",
            region="Northern Europe",
            continent="Europe",
            aliases=("sweden", "se"),
        ),
        "JP": CountryInfo(
            code="JP",
            name="Japan",
            region="East Asia",
            continent="Asia",
            aliases=("japan", "nippon", "jp"),
        ),
        "PK": CountryInfo(
            code="PK",
            name="Pakistan",
            region="South Asia",
            continent="Asia",
            aliases=("pakistan", "pk"),
        ),
        "IN": CountryInfo(
            code="IN",
            name="India",
            region="South Asia",
            continent="Asia",
            aliases=("india", "in"),
        ),
        "CN": CountryInfo(
            code="CN",
            name="China",
            region="East Asia",
            continent="Asia",
            aliases=("china", "prc", "cn"),
        ),
        "SG": CountryInfo(
            code="SG",
            name="Singapore",
            region="Southeast Asia",
            continent="Asia",
            aliases=("singapore", "sg"),
        ),
        "KR": CountryInfo(
            code="KR",
            name="South Korea",
            region="East Asia",
            continent="Asia",
            aliases=("south korea", "korea", "republic of korea", "kr"),
        ),
        "TR": CountryInfo(
            code="TR",
            name="Turkey",
            region="Southern Europe",
            continent="Europe",
            aliases=("turkey", "turkiye", "tr"),
        ),
        "BR": CountryInfo(
            code="BR",
            name="Brazil",
            region="South America",
            continent="Americas",
            aliases=("brazil", "brasil", "br"),
        ),
        "SA": CountryInfo(
            code="SA",
            name="Saudi Arabia",
            region="Middle East",
            continent="Asia",
            aliases=("saudi arabia", "ksa", "saudi"),
        ),
        "AE": CountryInfo(
            code="AE",
            name="United Arab Emirates",
            region="Middle East",
            continent="Asia",
            aliases=("united arab emirates", "uae", "emirates", "dubai"),
        ),
    }

    # Region groups mapping
    REGIONS: ClassVar[dict[str, list[str]]] = {
        "europe": ["DE", "GB", "FR", "IT", "ES", "NL", "CH", "SE", "TR"],
        "european union": ["DE", "FR", "IT", "ES", "NL", "SE"],
        "eu": ["DE", "FR", "IT", "ES", "NL", "SE"],
        "north america": ["US", "CA"],
        "asia": ["JP", "PK", "IN", "CN", "SG", "KR", "SA", "AE"],
        "south asia": ["PK", "IN"],
        "east asia": ["JP", "CN", "KR"],
        "middle east": ["SA", "AE", "TR"],
        "scandinavia": ["SE"],
        "oceania": ["AU"],
        "americas": ["US", "CA", "BR"],
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
        # Direct lookup
        lookup = cls._get_lookup_index()
        if cleaned in lookup:
            return lookup[cleaned]
        return None

    @classmethod
    def normalize_region(cls, text: str | None) -> str | None:
        """Resolve region mentions (e.g. 'in Europe', 'European') to standard region name."""
        if not text:
            return None
        cleaned = text.strip().lower()
        if cleaned in ("europe", "european", "in europe", "across europe"):
            return "Europe"
        if cleaned in ("european union", "eu"):
            return "European Union"
        if cleaned in ("north america", "north american"):
            return "North America"
        if cleaned in ("asia", "asian"):
            return "Asia"
        if cleaned in ("middle east", "middle eastern"):
            return "Middle East"
        if cleaned in ("scandinavia", "scandinavian", "nordic"):
            return "Scandinavia"
        if cleaned in ("latin america", "south america"):
            return "Latin America"
        if cleaned in ("global", "worldwide", "international", "anywhere"):
            return "Global"
        return None

    @classmethod
    def is_in_region(cls, country_code: str, region_name: str) -> bool:
        """Check if a country code belongs to a given region name."""
        region_key = region_name.strip().lower()
        if region_key in ("global", "anywhere"):
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
