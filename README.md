# **1. Privacy and Login Windows**
**When running the code, you MUST cancel or accept the privacy popup window and cancel the login window (by clicking elsewhere on the screen).**

---

# **2. MongoDB Configuration**
**You can deploy on your local MongoDB. The Atlas MongoDB configuration is for my use, please COMMENT OUT that section to avoid errors (it is currently the default).**

---

# **3. Current Status**

### **3.1 Data Storage**
**Fetched raw HTML and stored into:** `S5520` -> `DB_final` -> `jobs_raw`

### **3.2 Data Schema (Parsed Output)**
**Extract raw HTML and parse them into the following structure:**

```json
{
  "job_title": "string",       // Job title extracted from the HTML page
  "company_name": "string",    // Name of the hiring company
  "min_salary": 15000,         // Minimum salary (e.g., in Zloty)
  "max_salary": 20000,         // Maximum salary (e.g., in Zloty)
  "location": "string",        // City name or "Remote"
  "jump_url": "string",        // URL to the job detail page
  "processed_at": "timestamp", // Time of data extraction
  "query_term": "string"       // Search keyword (e.g., "business analyst")
}