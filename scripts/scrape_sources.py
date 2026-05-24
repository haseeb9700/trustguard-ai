import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

URLS = [
        # Immigration / F-1 / OPT official sources
    "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students",
    "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-extension-for-stem-students-stem-opt",
    "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/students-and-employment",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-5",
    "https://www.ice.gov/sevis/practical-training",
    "https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt",
    "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",

    # AI governance official sources
    "https://www.nist.gov/itl/ai-risk-management-framework",
    "https://airc.nist.gov/airmf-resources/playbook/",
    "https://www.govinfo.gov/app/details/GOVPUB-PREX23-PURL-gpo193638",

    # Model risk / financial governance sources
    "https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html",
    "https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf"
]

HEADERS = {
    "User-Agent": "TrustGuardAI Research Project - Educational Use"
}

def scrape_page(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else "No Title"

    content_tags = soup.find_all(["h2", "h3", "p", "li"])

    text_blocks = []
    for tag in content_tags:
        text = tag.get_text(" ", strip=True)
        if len(text) > 40:
            text_blocks.append(text)

    raw_text = "\n".join(text_blocks)

    return {
        "source_url": url,
        "source_title": title,
        "scraped_at": datetime.now().isoformat(),
        "raw_text": raw_text
    }

def main():
    rows = []

    for url in URLS:
        print(f"Scraping: {url}")
        page_data = scrape_page(url)
        rows.append(page_data)

    df = pd.DataFrame(rows)
    df.to_csv("data/raw_sources.csv", index=False)

    print("Done. Saved file: data/raw_sources.csv")

if __name__ == "__main__":
    main()