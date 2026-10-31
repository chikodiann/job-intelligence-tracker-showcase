import re
from enum import Enum
from typing import Optional, Tuple


class RemoteEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


class EligibilityClassifier:
    """Classifies job location requirements against Nigeria / EMEA candidate location."""

    ELIGIBLE_KEYWORDS = [
        "worldwide",
        "global",
        "international",
        "anywhere",
        "nigeria",
        "africa",
        "emea",
        "europe/africa",
        "africa/europe",
        "latam/emea",
        "allow remote from anywhere",
        "work from anywhere",
        "open to all locations",
    ]

    INELIGIBLE_PATTERNS = [
        r"\bus\s+only\b",
        r"\busa\s+only\b",
        r"\bunited\s+states\s+only\b",
        r"\bcanada\s+only\b",
        r"\buk\s+only\b",
        r"\bunited\s+kingdom\s+only\b",
        r"\beu\s+only\b",
        r"\beurope\s+only\b",
        r"\bamericas\s+only\b",
        r"\bnorth\s+america\s+only\b",
        r"\blatam\s+only\b",
        r"\basia\s+only\b",
        r"\baustralia\s+only\b",
        r"\bindia\s+only\b",
        r"\bisrael\s+only\b",
        r"\bmust\s+be\s+located\s+in\b",
        r"\bus\s+work\s+authorization\b",
        r"\bus\s+citizen\b",
        r"\bgreencard\b",
        r"\bgreen\s+card\b",
        r"\breside\s+in\s+the\s+us\b",
        r"\breside\s+in\s+the\s+uk\b",
        r"\breside\s+in\s+canada\b",
    ]

    RESTRICTED_REGIONS_OR_COUNTRIES = [
        "us", "usa", "united states", "canada", "uk", "united kingdom",
        "eu", "europe", "americas", "latin america", "latam", "apac", "asia",
        "australia", "india", "israel", "north america", "brazil", "germany", "france"
    ]

    @classmethod
    def classify(cls, location_text: Optional[str], description_text: Optional[str] = None) -> Tuple[RemoteEligibility, str]:
        loc_clean = (location_text or "").lower().strip()
        desc_clean = (description_text or "")[:1000].lower().strip()
        combined = f"{loc_clean} {desc_clean}"

        # 1. Check explicit description/combined ineligible patterns (e.g. US citizens only, green card, etc.)
        for pattern in cls.INELIGIBLE_PATTERNS:
            if re.search(pattern, combined):
                return RemoteEligibility.INELIGIBLE, f"Role requires restricted geographic eligibility (matched pattern: '{pattern}')."

        # 2. Check location requirement string specifically
        if loc_clean:
            has_eligible = any(k in loc_clean for k in cls.ELIGIBLE_KEYWORDS)

            found_restricted = []
            for region in cls.RESTRICTED_REGIONS_OR_COUNTRIES:
                if re.search(r"\b" + re.escape(region) + r"\b", loc_clean):
                    found_restricted.append(region)

            if found_restricted and not has_eligible:
                return RemoteEligibility.INELIGIBLE, f"Location requirement '{location_text}' restricts candidates to regions/countries excluding Nigeria ({', '.join(found_restricted)})."

            if has_eligible:
                return RemoteEligibility.ELIGIBLE, f"Role location requirement '{location_text}' explicitly permits Worldwide, EMEA, or Nigeria candidates."

        # 3. Check description text for explicit worldwide / EMEA permission if location header is generic (e.g. 'Remote')
        for k in cls.ELIGIBLE_KEYWORDS:
            if re.search(r"\b" + re.escape(k) + r"\b", desc_clean):
                return RemoteEligibility.ELIGIBLE, f"Description explicitly permits Worldwide/EMEA candidates ('{k}')."

        # Default fallback: UNKNOWN
        return RemoteEligibility.UNKNOWN, f"Listing specifies '{location_text or 'Remote'}' without explicit country/geographic region."

