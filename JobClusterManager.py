import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cdist
import matplotlib.patheffects as PathEffects

class JobClusterManager:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="BD_final"):
        """
        Initialize MongoDB connection and class attributes.
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.df = None
        self.vectorizer = None
        self.X_skills = None
        self.kmeans = None
        self.terms = None

    def load_and_preprocess_data(self):
        """
        Retrieve job data from both NoFluffJobs and JustJoin.it, 
        combine them into a pandas DataFrame, and perform basic cleaning.
        (Refers to CELL #8)
        """
        print("Loading data from MongoDB...")
        
        # Combine both sources into one dataset
        query = {"must_have_skills": {"$exists": True, "$ne": []}}
        jobs_nf = list(self.db.jobs_processed.find(query))
        jobs_jj = list(self.db.jobs_processed_jj.find(query))
        jobs = jobs_nf + jobs_jj

        self.df = pd.DataFrame(jobs)[[
            "job_title", "company_name", "must_have_skills", 
            "min_salary", "max_salary", "source"
        ]]

        # Drop rows with empty or missing skills
        self.df = self.df[self.df["must_have_skills"].apply(
            lambda x: isinstance(x, list) and len(x) > 0
        )].copy()

        # Lowercase all skills and join into a single string per job
        self.df["skills_text"] = self.df["must_have_skills"].apply(
            lambda x: " ".join([s.lower() for s in x])
        )
        
        print(f"Loaded {len(self.df)} jobs with standardized skills.")
        return self.df

    def get_skill_frequency_analysis(self):
        """
        Perform advanced aggregation pipeline to analyze skill frequency 
        and salary context across job sources.
        (Refers to CELL #9)
        """
        pipeline = [
            {"$match": {"must_have_skills": {"$exists": True, "$ne": []}}},
            {"$unwind": "$must_have_skills"},
            {
                "$group": {
                    "_id": "$must_have_skills",
                    "job_count": {"$sum": 1},
                    "avg_min_salary": {"$avg": "$min_salary"},
                    "avg_max_salary": {"$avg": "$max_salary"},
                    "example_titles": {"$addToSet": "$job_title"}
                }
            },
            {"$addFields": {"unique_titles_count": {"$size": "$example_titles"}}}
        ]

        skill_analysis_1 = list(self.db.jobs_processed.aggregate(pipeline))
        skill_analysis_2 = list(self.db.jobs_processed_jj.aggregate(pipeline))

        combined_skills = defaultdict(lambda: {
            "job_count": 0, "salary_sum_min": 0, "salary_sum_max": 0,
            "salary_count": 0, "example_titles": set()
        })

        def merge_results(analysis_list):
            for skill in analysis_list:
                name = skill["_id"]
                combined_skills[name]["job_count"] += skill["job_count"]
                if skill.get("avg_min_salary") is not None:
                    combined_skills[name]["salary_sum_min"] += skill["avg_min_salary"] * skill["job_count"]
                    combined_skills[name]["salary_count"] += skill["job_count"]
                if skill.get("avg_max_salary") is not None:
                    combined_skills[name]["salary_sum_max"] += skill["avg_max_salary"] * skill["job_count"]
                combined_skills[name]["example_titles"].update(skill["example_titles"])

        merge_results(skill_analysis_1)
        merge_results(skill_analysis_2)

        final_analysis = []
        for name, data in combined_skills.items():
            doc = {
                "_id": name, "job_count": data["job_count"],
                "unique_titles_count": len(data["example_titles"]),
                "example_titles": list(data["example_titles"])
            }
            if data["salary_count"] > 0:
                doc["avg_min_salary"] = data["salary_sum_min"] / data["salary_count"]
                doc["avg_max_salary"] = data["salary_sum_max"] / data["salary_count"]
            final_analysis.append(doc)

        final_analysis.sort(key=lambda x: x["job_count"], reverse=True)
        return final_analysis

    def vectorize_skills(self, min_df=0.015, max_df=0.99):
        """
        Transform job skills into a numerical TF-IDF matrix.
        (Refers to CELL #10)
        """
        self.vectorizer = TfidfVectorizer(min_df=min_df, max_df=max_df)
        self.X_skills = self.vectorizer.fit_transform(self.df["skills_text"])
        self.terms = self.vectorizer.get_feature_names_out()
        print(f"Skill matrix shape: {self.X_skills.shape}")
        return self.X_skills

    def plot_optimal_k(self, k_range=range(2, 20)):
        """
        Identify the optimal number of clusters using Elbow and Silhouette methods.
        (Refers to CELL #11 & #12)
        """
        X_dense = self.X_skills.toarray()
        distortions = []
        silhouette_scores = []

        print("Evaluating K values...")
        for k in k_range:
            km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
            labels = km.fit_predict(X_dense)
            dist = np.mean(np.min(cdist(X_dense, km.cluster_centers_, 'euclidean'), axis=1))
            distortions.append(dist)
            sil = silhouette_score(X_dense, labels)
            silhouette_scores.append(sil)
            print(f"k={k}, silhouette score={sil:.3f}")

        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(k_range, distortions, 'bx-')
        plt.xlabel("k")
        plt.ylabel("Distortion")
        plt.title("Elbow Method")

        plt.subplot(1, 2, 2)
        plt.plot(k_range, silhouette_scores, 'ro-')
        plt.xlabel("k")
        plt.ylabel("Silhouette Score")
        plt.title("Silhouette Analysis")
        plt.show()

    def run_clustering(self, k_optimal=12):
        """
        Apply KMeans with the chosen optimal k and identify key skills in each group.
        (Refers to CELL #13)
        """
        X_dense = self.X_skills.toarray()
        self.kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init=10)
        self.df["cluster"] = self.kmeans.fit_predict(X_dense)

        cluster_sizes = self.df["cluster"].value_counts().sort_index()
        print("\nJobs distribution per cluster:")
        for cluster_id in range(k_optimal):
            print(f"Cluster {cluster_id}: {cluster_sizes.get(cluster_id, 0)} jobs")
            center = self.kmeans.cluster_centers_[cluster_id]
            top_idx = np.argsort(center)[-10:][::-1]
            top_skills = [self.terms[i] for i in top_idx]
            print(f"  Representative skills: {', '.join(top_skills)}")

    def analyze_salaries(self):
        """
        Analyze salary distribution across skill clusters using IQR for outlier removal.
        (Refers to CELL #14)
        """
        salary_df = self.df[self.df["min_salary"].notna() & self.df["max_salary"].notna()].copy()
        salary_df["avg_salary"] = (salary_df["min_salary"] + salary_df["max_salary"]) / 2

        # Filter outliers using IQR
        Q1, Q3 = salary_df["avg_salary"].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        salary_df_filtered = salary_df[salary_df["avg_salary"] <= (Q3 + 1.5 * IQR)]

        stats = salary_df_filtered.groupby("cluster")["avg_salary"].agg(
            ["count", "mean", "median", "std"]
        ).sort_values(by="median", ascending=False)
        print("\nSalary Statistics by Cluster (Sorted by Median):")
        print(stats)

        # Plotting
        plt.figure(figsize=(14, 8))
        sns.boxplot(x="cluster", y="avg_salary", data=salary_df_filtered, order=stats.index)
        plt.title("Salary Distribution by Skill Cluster (Outliers Removed)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        return stats

    def analyze_skill_gap(self, cluster_stats):
        """
        Identify high-value skills by correlating skill presence with cluster salaries.
        (Refers to CELL #15)
        """
        k_clusters = self.kmeans.n_clusters
        skill_importance = {}
        for term_idx, term in enumerate(self.terms):
            weights = [self.kmeans.cluster_centers_[c][term_idx] for c in range(k_clusters)]
            skill_importance[term] = weights

        skill_df = pd.DataFrame(skill_importance).T
        median_salaries = cluster_stats["median"].to_dict()

        salary_corr = {}
        for skill in skill_df.index:
            # Weighted importance of each skill based on median salaries of clusters it appears in
            weighted_val = sum(skill_df.loc[skill, i] * median_salaries.get(i, 0) for i in range(k_clusters))
            salary_corr[skill] = weighted_val

        analysis = pd.DataFrame({
            "skill": list(salary_corr.keys()),
            "salary_correlation": list(salary_corr.values())
        })
        
        # Calculate demand (normalized frequency)
        analysis["demand"] = analysis["skill"].apply(
            lambda s: self.df["skills_text"].str.contains(r'\b' + s + r'\b').sum() / len(self.df)
        )
        
        # Filter skills with at least 5% market presence
        analysis = analysis[analysis["demand"] >= 0.05].sort_values("salary_correlation", ascending=False)
        
        # Visualization
        self._plot_gap_analysis(analysis)
        return analysis

    def _plot_gap_analysis(self, analysis):
        """
        Helper method to plot High-Value Skills (Salary Correlation vs Demand).
        """
        plt.figure(figsize=(14, 10))
        scatter = plt.scatter(analysis["demand"], analysis["salary_correlation"], 
                             c=analysis["salary_correlation"], cmap='viridis', s=80, alpha=0.8)
        plt.colorbar(scatter, label="Salary Correlation")
        
        # Annotate top 20 skills
        top_20 = analysis.head(20)
        for i, row in top_20.iterrows():
            plt.annotate(
                row["skill"], (row["demand"], row["salary_correlation"]),
                textcoords="offset points", xytext=(5,5), fontsize=10, fontweight='bold',
                path_effects=[PathEffects.withStroke(linewidth=3, foreground='white')]
            )
        plt.title("Top 20 High-Value Skills: Market Demand vs. Salary Potential")
        plt.xlabel("Demand (% of Jobs)")
        plt.ylabel("Salary Correlation Index")
        plt.grid(True, alpha=0.3)
        plt.show()