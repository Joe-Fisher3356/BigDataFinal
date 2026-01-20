# 🕸️ WebScraping Project Documentation

This project utilizes a Selenium-based crawler to extract job postings and store them in a MongoDB database.



## 0. Project Structure
* **0. Import dependency:** Cell 1
* **1. WebScrapingNoFluff:** Cell 2 3 4 5
* **2. WebScrapingJustJoin:** Cell 6 7
* **3. JobClusterManager:** Cell 8 9 10 11 12 13 14 15
* **4. JobDataCloudImageGenerator:** Cell 16
* **5. SalaryModelManager:** Cell 17


---

## 1. Describe two WebScrappers and DB collection structure:
**About 2 WebScrappers:** 
 * 1.WebScrapingNoFluff, fetch data and parse through HTML pages,
    fetch raw data -> parse to separated jobs -> add skill list into each job
 * 2.WebScrapingJustJoin, fetch data and parse through http response,
    fetch raw data and parse into jobs with skill list
 * 3.Job's structure  from 2 websites are same 
**About the job structure:** 


**Fetch and store path into:** 
 * 1.`S5520` -> `DB_final` -> `jobs_raw` and `jobs_processed`
 * 2.`S5520` -> `DB_final` -> `jobs_processed_jj`

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



## 2. MongoDB Configuration

The system supports both local and cloud-based database deployments.

* **Local Deployment:** You can run this on your local MongoDB instance.
* **Atlas Configuration:** This configuration is set to connect with remote MongoDB Atlas. 

---
## 3. Combine job data from 2 platform and train with K-Means cluster model
* **3.1** Load Jobs from Both Sources into DataFrame
* **3.2** Skill Frequency Analysis with MongoDB Aggregation
* **3.3** TF-IDF Vectorization of Skills
* **3.4** Determine Optimal Number of Clusters
* **3.5**  Apply K-Means Clustering and Analyze Skill Groups
* **3.6** Salary Analysis by Cluster
* **3.7** Skill Gap and Demand Analysis
---

## 4. Word Cloud 

We  will use wordCloud to generate the most frequent skill name.

* **JustJoin** 
* **NoFluffJobs** 

---

## 5. Random forest

* **We use random forest to get MAE/R².**
* **Analysis of job by salary and job level.**
---


