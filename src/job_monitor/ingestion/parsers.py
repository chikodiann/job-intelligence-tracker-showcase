import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional, Tuple
from ..models.normalized_job import SalaryPeriod


class HTMLSanitizer:
    """Sanitizes HTML content into clean plain text while preserving structure."""

    @staticmethod
    def sanitize(raw_html: Optional[str]) -> str:
        if not raw_html:
            return ""

        # Replace block tags and breaks with newlines
        text = re.sub(r"<(p|div|br|li|h[1-6])\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
        # Remove remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Unescape HTML entities (&amp;, &lt;, &gt;, &quot;, &#39;, etc.)
        text = html.unescape(text)
        # Normalize whitespace (multiple spaces to single space, trim empty lines)
        lines = [line.strip() for line in text.splitlines()]
        non_empty = [line for line in lines if line]
        return "\n".join(non_empty)


class DateParser:
    """Parses source date strings into Python datetime objects."""

    @staticmethod
    def parse_date(date_str: Optional[Any]) -> Optional[datetime]:
        if date_str is None:
            return None

        # 0. Handle integer/float Unix timestamp
        if isinstance(date_str, (int, float)):
            try:
                return datetime.fromtimestamp(date_str, tz=timezone.utc)
            except Exception:
                return None

        if not isinstance(date_str, str):
            return None

        date_str = date_str.strip()
        if not date_str:
            return None

        # Handle string numeric Unix timestamp (e.g. "1791394814")
        if date_str.isdigit():
            try:
                return datetime.fromtimestamp(int(date_str), tz=timezone.utc)
            except Exception:
                pass

        # 1. Try ISO 8601 parsing (standard in Python 3.7+)
        try:
            # Handle 'Z' suffix for UTC
            iso_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            return dt
        except ValueError:
            pass

        # 2. Try RFC 822 / RFC 2822 RSS date format (e.g. Wed, 07 Oct 2026 08:00:00 +0000)
        try:
            dt = parsedate_to_datetime(date_str)
            return dt
        except (TypeError, ValueError):
            pass

        # 3. Common YYYY-MM-DD or YYYY-MM-DD HH:MM:SS fallback
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass

        return None


class SalaryParser:
    """Extracts min/max amounts, currency, period, and annualized USD estimates from raw salary strings."""

    CURRENCY_SYMBOLS = {
        "$": "USD",
        "USD": "USD",
        "€": "EUR",
        "EUR": "EUR",
        "£": "GBP",
        "GBP": "GBP",
        "CAD": "CAD",
        "AUD": "AUD",
    }

    @classmethod
    def parse_salary(cls, raw_salary: Optional[str]) -> Tuple[
        Optional[float], Optional[float], Optional[str], SalaryPeriod, Optional[float], Optional[float]
    ]:
        """Parses salary string into:
        (min_amount, max_amount, currency, salary_period, annualized_min, annualized_max)
        
        Returns None for missing values, never discards jobs.
        """
        if not raw_salary or not isinstance(raw_salary, str):
            return None, None, None, SalaryPeriod.UNKNOWN, None, None

        cleaned = raw_salary.strip()
        if not cleaned or cleaned.lower() in ("competitive", "negotiable", "undisclosed", "n/a", "none"):
            return None, None, None, SalaryPeriod.UNKNOWN, None, None

        # Detect currency
        currency = None
        for sym, code in cls.CURRENCY_SYMBOLS.items():
            if sym in cleaned.upper():
                currency = code
                break

        # Detect period
        period = SalaryPeriod.UNKNOWN
        cleaned_lower = cleaned.lower()
        if "hour" in cleaned_lower or "/hr" in cleaned_lower or "ph" in cleaned_lower:
            period = SalaryPeriod.HOURLY
        elif "month" in cleaned_lower or "/mo" in cleaned_lower:
            period = SalaryPeriod.MONTHLY
        elif "year" in cleaned_lower or "/yr" in cleaned_lower or "annum" in cleaned_lower or "k" in cleaned_lower or "$" in cleaned:
            period = SalaryPeriod.ANNUAL

        # Extract numerical numbers (handling 'k' e.g. 120k -> 120000)
        # Find all numbers like 120k, 150,000, 30.5
        number_matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(k)?", cleaned, re.IGNORECASE)
        numbers = []
        for num_str, k_suffix in number_matches:
            val = float(num_str.replace(",", ""))
            if k_suffix.lower() == "k" or (val < 1000 and period == SalaryPeriod.ANNUAL and val > 15):
                val *= 1000
            numbers.append(val)

        if not numbers:
            return None, None, currency, period, None, None

        min_val = min(numbers)
        max_val = max(numbers)

        # Refine period inference based on value magnitude if period is unknown
        if period == SalaryPeriod.UNKNOWN:
            if max_val <= 200:
                period = SalaryPeriod.HOURLY
            elif max_val <= 20000:
                period = SalaryPeriod.MONTHLY
            else:
                period = SalaryPeriod.ANNUAL

        # Annualize
        annualized_min = None
        annualized_max = None

        # Only compute annualized USD if currency is USD (no fake FX rate conversions)
        if currency == "USD" or currency is None:
            if period == SalaryPeriod.HOURLY:
                annualized_min = min_val * 2080  # 40 hrs/wk * 52 wks
                annualized_max = max_val * 2080
            elif period == SalaryPeriod.MONTHLY:
                annualized_min = min_val * 12
                annualized_max = max_val * 12
            elif period == SalaryPeriod.ANNUAL:
                annualized_min = min_val
                annualized_max = max_val

        return min_val, max_val, currency, period, annualized_min, annualized_max
