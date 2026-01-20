import os
import requests 
from datetime import datetime

from dotenv import load_dotenv

from pymongo import MongoClient

import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class WebScrapingJustJoin:
    def __init__(self, query_term="backend"):
        print("Initialise WebScrapingJustJoin instance")
        self.query_term = query_term
        self.api_url = (
            "https://api.justjoin.it/v2/user-panel/offers/by-cursor"
            "?cityRadiusKm=30"
            "&currency=pln"
            "&from=0"
            "&itemsCount=100"
            f"&keywords[]={query_term.replace(' ', '%20')}"
            "&orderBy=DESC"
            "&sortBy=published"
        )
        self._init_db()

    def _init_db(self):
        mode = os.getenv("MONGO_MODE", "local")
        db_name = os.getenv("DB_NAME", "BD_final")

        if mode == "atlas":
            uri = os.getenv("ATLAS_MONGO_URI")
        else:
            uri = "mongodb://localhost:27017/"

        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        print("✅ JustJoin connected to DB")

    # ---- salary normalization (matches NoFluff logic) ----
    def normalize_salary(self, emp):
        if not emp or emp.get("from") is None:
            return None, None

        from_sal = emp.get("from")
        to_sal = emp.get("to")
        unit = emp.get("unit")  # hour / day / month

        if unit == "hour":
            return from_sal * 160, to_sal * 160
        if unit == "day":
            return from_sal * 20, to_sal * 20

        return from_sal, to_sal  # month

    def scrape_and_process(self):
        import requests

        processed = []
        items_per_request = 100   # max jobs per API request
        max_items = 300           # total jobs we want

        for start in range(0, max_items, items_per_request):
            paged_url = (
                "https://api.justjoin.it/v2/user-panel/offers/by-cursor"
                "?cityRadiusKm=30"
                "&currency=pln"
                f"&from={start}"
                f"&itemsCount={items_per_request}"
                f"&keywords[]={self.query_term.replace(' ', '%20')}"
                "&orderBy=DESC"
                "&sortBy=published"
            )

            response = requests.get(paged_url)
            raw = response.json()

            for job in raw.get("data", []):
                emp = job.get("employmentTypes", [{}])[0]
                min_sal, max_sal = self.normalize_salary(emp)

                processed.append({
                    "source": "justjoin",
                    "job_title": job.get("title"),
                    "company_name": job.get("companyName"),
                    "min_salary": min_sal,
                    "max_salary": max_sal,
                    "location": job.get("city"),
                    "jump_url": f"https://justjoin.it/offers/{job.get('slug')}",
                    "must_have_skills": [
                        skill.lower() for skill in job.get("requiredSkills", [])
                    ],
                    "processed_at": datetime.now(),
                    "query_term": self.query_term

                })
        print(f"✅ Saved {len(processed)} JustJoin jobs")

        self.db.jobs_processed_jj.drop()
        self.db.jobs_processed_jj.insert_many(processed)
