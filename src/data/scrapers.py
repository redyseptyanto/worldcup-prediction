"""Scraper for official FIFA World Cup rosters from Wikipedia."""

from __future__ import annotations

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

from src.config import SETTINGS
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)

OFFICIAL_ROSTERS_FILE = SETTINGS.raw_dir / "players" / "official_2026_rosters.csv"

def normalize_name(name: str) -> str:
    """Normalize player name for robust matching."""
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()

def scrape_wikipedia_rosters() -> pd.DataFrame:
    """Scrape the 2026 FIFA World Cup squads Wikipedia page."""
    LOGGER.info("Scraping Wikipedia for official 2026 World Cup rosters...")
    url = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    squads = []
    
    for heading_div in soup.find_all('div', class_=re.compile(r'mw-heading3')):
        h3 = heading_div.find('h3')
        if not h3:
            continue
            
        country = h3.text.strip().replace('[edit]', '')
        
        node = heading_div.find_next_sibling()
        while node and node.name != 'table':
            if node.name == 'div' and 'mw-heading' in node.get('class', []):
                break
            node = node.find_next_sibling()
            
        if node and node.name == 'table':
            rows = node.find_all('tr', class_='nat-fs-player')
            for row in rows:
                th = row.find('th')
                if th:
                    # Strip out (captain) and other tags
                    player_name = th.text.replace('(captain)', '').strip()
                    squads.append({
                        "team": country,
                        "player_name": player_name,
                        "name_norm": normalize_name(player_name)
                    })
    
    df = pd.DataFrame(squads)
    if len(df) > 0:
        OFFICIAL_ROSTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OFFICIAL_ROSTERS_FILE, index=False)
        LOGGER.info(f"Saved {len(df)} players across {df['team'].nunique()} teams to {OFFICIAL_ROSTERS_FILE}")
    else:
        LOGGER.warning("No players found on Wikipedia page.")
        
    return df

if __name__ == "__main__":
    scrape_wikipedia_rosters()
