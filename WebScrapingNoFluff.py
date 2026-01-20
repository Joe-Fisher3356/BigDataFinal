import os
import re
import time
from datetime import datetime


from dotenv import load_dotenv


from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Database
from pymongo import MongoClient

# HTML webpage scrapping
class WebScrapingNoFluff:
    def __init__(self, query_term='backend'):
        load_dotenv()
        print('Initialise WebScraping instance')
        self.query_term = query_term
        self.target_url = f"https://nofluffjobs.com/pl/?lang=en&criteria=jobPosition%3D{self.query_term}"
        self.final_html = ''
        # --- init db: local db / Atlas Mongodb ---
        self._init_db()


    def _init_db(self):
        """
        You don't need .env, cause you will deploy on local db
        MONGO_MODE from .env:
        "local": connect with local mongodb
        "atlas": connect with remote mongodb
        """

        mode = os.getenv("MONGO_MODE", "local")
        db_name = os.getenv("DB_NAME", "BD_final")

        print("DB MODE: ", mode)

        if mode == "atlas":
            uri = os.getenv("ATLAS_MONGO_URI")
            if not uri:
                raise ValueError("❌ Error: ATLAS_MONGO_URI not found in .env while mode is 'atlas'")
            print(f"🌐 Connecting to Remote MongoDB Atlas...")
        else:
            uri = "mongodb://localhost:27017/"
            print(f" Connecting to Local MongoDB ({uri})...")

        try:
            self.client = MongoClient(uri)
            # test connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            print(f"✅ Successfully connected to database: {db_name}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def scrape_save_raw_to_db(self, clicks=3):
        driver = webdriver.Chrome()
        driver.get(self.target_url)
        driver.maximize_window()
        # Give you 15 seconds to accept/cancel all popup window
        wait = WebDriverWait(driver, 15)

        # Loop to click "See more offers" button 10 times
        count = 0
        while count < clicks:
            try:
                # Find the button with the nfjloadmore attribute
                load_more_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[nfjloadmore]")))

                # Scroll to the button position to ensure it is in the viewport
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_btn)
                time.sleep(1.5)  # Allow some buffer time for scrolling

                # Click to load more
                if load_more_btn:
                    load_more_btn.click()
                count += 1
                print(f"Clicked 'See more' ({count}/{clicks})")

                # Delay for new content to load
                time.sleep(2.5)
            except Exception as e:
                print(f"Finished loading or button not found: {e}")
                break

        # C. Get the complete HTML after 10 clicks and save it
        print("All pages loaded. Capturing final HTML...")
        self.final_html = driver.page_source
        self.save_raw_to_mongodb()

        driver.quit()

    def save_raw_to_mongodb(self):
        """
        Reference your initial logic to store the raw HTML into NoSQL
        """
        # only hold one raw_json html data
        self.db.jobs_raw.drop()
        website_document = {
            'url': self.target_url,
            'content': self.final_html,
            'date': datetime.now(),
            'query_term': self.query_term
        }

        # Store in the jobs_raw collection
        result = self.db.jobs_raw.insert_one(website_document)
        print(f"Raw HTML saved to MongoDB! Document ID: {result.inserted_id}")

    # parse and split salary to min and max two value
    def parse_salary(self, salary_str):
        """
        Internal helper method: Parse salary string
        Example input: "10 000 - 15 000 PLN", "20 000 PLN", "Undisclosed"
        Output: (min_salary, max_salary)
        """
        if not salary_str or "Undisclosed" in salary_str or "Agreement" in salary_str:
            return None, None

        # Remove spaces and thousands separators
        clean_str = salary_str.replace('\xa0', '').replace(' ', '')

        # Match all digits
        numbers = re.findall(r'\d+', clean_str)

        try:
            if len(numbers) >= 2:
                # Range salary: [10000, 15000]
                return float(numbers[0]), float(numbers[1])
            elif len(numbers) == 1:
                # Fixed salary: [20000]
                return float(numbers[0]), float(numbers[0])
        except Exception:
            pass

        return None, None

    # parse job location
    def parse_location(self, card):
        """
        Internal helper method: Parse location
        """
        location_tag = card.select_one('span.posting-info__location, nfj-posting-item-city')
        if not location_tag:
            return "Unknown"

        loc_text = location_tag.get_text(strip=True)

        # Special case handling: Remote work
        if "Remote" in loc_text or "Zdalna" in loc_text:
            return "Remote"

        # Extract city name (some include '+1', filter via split)
        city = loc_text.split('+')[0].strip()
        return city

    # parse job title,company name, Min/Max Salary,Location, Jump URL and save into db
    def process_and_save(self):
        """
        Read HTML from jobs_raw and extract fields to store in jobs_processed
        extract raw html and parse fields then save into
        """
        # Get the most recently scraped HTML document
        raw_data = self.db.jobs_raw.find_one(sort=[("date", -1)])
        if not raw_data:
            print("No raw data found in MongoDB!")
            return

        soup = BeautifulSoup(raw_data['content'], 'html.parser')

        # Locate all job cards
        postings = soup.select('a.posting-list-item')
        print(f"Found {len(postings)} job postings in HTML.")

        processed_list = []
        base_domain = "https://nofluffjobs.com"  # Used to concatenate the full URL

        for post in postings:
            try:
                # --- Field 1: Job Title ---
                title_el = post.select_one('h3.posting-title__position, .posting-title__can-hide')
                if title_el:
                    # Find and remove any potential "NEW" tags or other badges
                    # NFJ's badge class names usually contain title-badge
                    for badge in title_el.select('.title-badge, .title-badge--new'):
                        badge.decompose()
                    job_title = title_el.get_text(strip=True)
                else:
                    job_title = "N/A"
                # print('JOB TITLE:', job_title)

                # --- Field 2: Company Name ---
                company_el = post.select_one('span.d-block, .company-name')
                company_name = company_el.get_text(strip=True) if company_el else "N/A"

                # --- Fields 3 & 4: Min/Max Salary ---
                salary_el = post.select_one('span.text-truncate, nfj-posting-item-salary')
                salary_str = salary_el.get_text(strip=True) if salary_el else ""
                min_sal, max_sal = self.parse_salary(salary_str)

                # --- Field 5: Location ---
                location = self.parse_location(post)

                # --- Field 6: Jump URL ---
                # Get relative path from the <a> tag's href attribute and concatenate domain
                relative_url = post.get('href')
                jump_url = base_domain + relative_url if relative_url else "N/A"

                # Construct document
                job_doc = {
                    "source": "nofluffjobs",
                    'job_title': job_title,
                    'company_name': company_name,
                    'min_salary': min_sal,
                    'max_salary': max_sal,
                    'location': location,
                    'jump_url': jump_url,  # Add to the document
                    'processed_at': datetime.now(),
                    'query_term': raw_data['query_term']
                }

                processed_list.append(job_doc)

            except Exception as e:
                print(f"Error parsing a single post: {e}")
                continue

        # Batch save to the new collection
        if processed_list:
            self.db.jobs_processed.drop()
            self.db.jobs_processed.insert_many(processed_list)
            print(f"Successfully processed {len(processed_list)} jobs and saved to 'jobs_processed'.")

    # scrape the job detail page and add must-have skill set into each job
    def scrape_must_have_skills(self, limit=0):
        driver = webdriver.Chrome()
        driver.maximize_window()
        wait = WebDriverWait(driver, 15)


        jobs = list(self.db.jobs_processed.find().limit(limit))
        print(f"Scraping Must-have skills for {len(jobs)} jobs")

        for job in jobs:
            url = job.get("jump_url")
            if not url:
                continue

            try:
                driver.get(url)
                time.sleep(2)  # wait for page to render

                soup = BeautifulSoup(driver.page_source, "html.parser")
                must_section = soup.select_one('section[branch="musts"]')

                skills = []
                if must_section:
                    skill_tags = must_section.select('span[id^="item-tag-"]')
                    for tag in skill_tags:
                        skills.append(tag.get_text(strip=True).lower())

                # Update MongoDB document
                self.db.jobs_processed.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"must_have_skills": skills}}
                )

                print(f"✔ {job['job_title']} → {skills}")

            except Exception as e:
                print(f"❌ Error scraping {url} : {e}")

        driver.quit()
        print("Finished scraping Must-have skills.")
        