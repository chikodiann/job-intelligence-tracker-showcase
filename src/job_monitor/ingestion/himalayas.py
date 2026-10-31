import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional
from ..interfaces.fetcher import BaseJobFetcher
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger

logger = setup_logger("ingestion.himalayas")


class HimalayasFetcher(BaseJobFetcher):
    """Concrete fetcher for Himalayas RSS Feed (https://himalayas.app/jobs/rss)."""

    def __init__(
        self,
        endpoint_url: str = "https://himalayas.app/jobs/rss",
        rate_limit_delay_seconds: float = 2.0,
        user_agent: str = "RemoteJobCashflowMonitor/1.0",
        request_timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name="himalayas",
            rate_limit_delay_seconds=rate_limit_delay_seconds,
            user_agent=user_agent,
        )
        self.endpoint_url = endpoint_url
        self.request_timeout_seconds = request_timeout_seconds

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        """Fetches remote jobs from Himalayas RSS feed."""
        self.enforce_rate_limit()

        headers = {"User-Agent": self.user_agent, "Accept": "application/rss+xml, application/xml, text/xml"}
        req = urllib.request.Request(self.endpoint_url, headers=headers)

        logger.info("Fetching jobs from Himalayas RSS: %s", self.endpoint_url)
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                if response.status != 200:
                    logger.error("Himalayas HTTP error status %d", response.status)
                    return []

                xml_data = response.read().decode("utf-8")
                root = ET.fromstring(xml_data)

                items = root.findall(".//item")
                logger.info("Retrieved %d RSS items from Himalayas", len(items))

                raw_jobs: List[RawJob] = []
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    guid_elem = item.find("guid")
                    pubdate_elem = item.find("pubDate")
                    desc_elem = item.find("description")
                    category_elems = item.findall("category")

                    title = title_elem.text if title_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""
                    guid = guid_elem.text if guid_elem is not None else ""
                    pub_date = pubdate_elem.text if pubdate_elem is not None else ""
                    description = desc_elem.text if desc_elem is not None else ""
                    categories = [c.text for c in category_elems if c.text]

                    ext_id = guid or link
                    if not ext_id:
                        ext_id = hashlib.md5(f"{title}_{link}".encode("utf-8")).hexdigest()

                    payload = {
                        "title": title,
                        "link": link,
                        "guid": guid,
                        "pubDate": pub_date,
                        "category": categories,
                        "description": description,
                    }

                    raw_jobs.append(
                        RawJob(
                            source_name=self.source_name,
                            external_id=ext_id,
                            payload=payload,
                        )
                    )

                if limit and len(raw_jobs) > limit:
                    raw_jobs = raw_jobs[:limit]

                return raw_jobs

        except Exception as e:
            logger.error("Failed to fetch jobs from Himalayas RSS: %s", str(e))
            return []
