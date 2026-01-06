# 🕸️ WebScraping Project Documentation

This project utilizes a Selenium-based crawler to extract job postings and store them in a MongoDB database.

---

## 1. Critical Operational Steps ⚠️

**When running the code, manual intervention is required for the following browser pop-ups:**

* **Privacy Popup:** You MUST either **Accept** or **Cancel** the privacy consent window.
* **Login Window:** You MUST **Cancel** the login prompt (typically by clicking anywhere outside the window or clicking the close button).

---

## 2. MongoDB Configuration

The system supports both local and cloud-based database deployments.

* **Local Deployment:** You can run this on your local MongoDB instance.
* **Atlas Configuration:** This configuration is set to connect with remote MongoDB Atlas. 

---

## 3. Expected Console Output

If the script runs successfully, your terminal output should resemble the following log:

```text
Initialise WebScraping instance
DB MODE:  local
 Connecting to Local MongoDB (mongodb://localhost:27017/)...
✅ Successfully connected to database: BD_final

Clicked 'See more' (1/10)
Clicked 'See more' (2/10)
Clicked 'See more' (3/10)
Clicked 'See more' (4/10)
Clicked 'See more' (5/10)
Clicked 'See more' (6/10)

Finished loading or button not found: Message: 
Stacktrace:
[System Stacktrace Omitted for Brevity]

All pages loaded. Capturing final HTML...
Raw HTML saved to MongoDB! Document ID: 695bd8a15773267e73f5a75a
Found 123 job postings in HTML.
Successfully processed 123 jobs and saved to 'jobs_processed'.
```

# **4. Current Status**



### **4.1 Data Storage**

**Fetched raw HTML and stored into:** `S5520` -> `DB_final` -> `jobs_raw`



### **4.2 Data Schema (Parsed Output)**
** Add must-have skill set from job detail page**
**Extract raw HTML and parse them into the following structure:**


```json

{

"job_title": "string", // Job title extracted from the HTML page

"company_name": "string", // Name of the hiring company

"min_salary": 15000, // Minimum salary (e.g., in Zloty)

"max_salary": 20000, // Maximum salary (e.g., in Zloty)

"location": "string", // City name or "Remote"

"jump_url": "string", // URL to the job detail page

"processed_at": "timestamp", // Time of data extraction

"query_term": "string" // Search keyword (e.g., "business analyst")
  
"must_have_skills": "Array"  //must-have skill set

}
```


