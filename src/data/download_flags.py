"""Download flag images for the 2026 World Cup participating nations."""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.config import FLAGS_DIR

logger = logging.getLogger(__name__)

TEAM_ISO_MAP = {
    "Algeria": "dz",
    "Argentina": "ar",
    "Australia": "au",
    "Austria": "at",
    "Belgium": "be",
    "Bosnia and Herzegovina": "ba",
    "Brazil": "br",
    "Canada": "ca",
    "Cape Verde": "cv",
    "Colombia": "co",
    "Croatia": "hr",
    "Curaçao": "cw",
    "Curaao": "cw", # fallback for encoding issues
    "Czech Republic": "cz",
    "DR Congo": "cd",
    "Ecuador": "ec",
    "Egypt": "eg",
    "England": "gb-eng",
    "France": "fr",
    "Germany": "de",
    "Ghana": "gh",
    "Haiti": "ht",
    "Iran": "ir",
    "Iraq": "iq",
    "Ivory Coast": "ci",
    "Japan": "jp",
    "Jordan": "jo",
    "Mexico": "mx",
    "Morocco": "ma",
    "Netherlands": "nl",
    "New Zealand": "nz",
    "Norway": "no",
    "Panama": "pa",
    "Paraguay": "py",
    "Portugal": "pt",
    "Qatar": "qa",
    "Saudi Arabia": "sa",
    "Scotland": "gb-sct",
    "Senegal": "sn",
    "South Africa": "za",
    "South Korea": "kr",
    "Spain": "es",
    "Sweden": "se",
    "Switzerland": "ch",
    "Tunisia": "tn",
    "Turkey": "tr",
    "United States": "us",
    "Uruguay": "uy",
    "Uzbekistan": "uz"
}

def download_flags() -> None:
    """Download flags to the FLAGS_DIR."""
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    
    session = requests.Session()
    
    for team, iso in TEAM_ISO_MAP.items():
        # Avoid invalid names
        if team == "Curaao":
            continue
            
        file_path = FLAGS_DIR / f"{team}.png"
        if file_path.exists():
            logger.info(f"Flag for {team} already exists.")
            continue
            
        url = f"https://flagcdn.com/w80/{iso}.png"
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Downloaded flag for {team}")
        except Exception as e:
            logger.error(f"Failed to download flag for {team} from {url}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_flags()
