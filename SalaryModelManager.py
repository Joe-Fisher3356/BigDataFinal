import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from enum import Enum
from pymongo import MongoClient
from dotenv import load_dotenv

from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from enum import Enum            
from constant import CollectionEnum


class SalaryModelManager:
    def __init__(self):
        """
        Initialize the manager by automatically connecting to the database
        using environment variables.
        """
        load_dotenv()
        self.db = self._init_db()
        self.categorical_features = ["location", "source", "job_level"]

    def _init_db(self):
        """
        Internal method to establish connection with MongoDB (Atlas or Local).
        """
        mode = os.getenv("MONGO_MODE", "local")
        db_name = os.getenv("DB_NAME", "BD_final")

        if mode == "atlas":
            uri = os.getenv("ATLAS_MONGO_URI")
            if not uri:
                raise ValueError("❌ ATLAS_MONGO_URI not found in .env")
            print(f"🌐 Connecting to MongoDB Atlas...")
        else:
            uri = "mongodb://localhost:27017/"
            print(f"🏠 Connecting to Local MongoDB...")

        try:
            client = MongoClient(uri)
            # Send a ping to confirm a successful connection
            client.admin.command('ping')
            print(f"✅ Successfully connected to database: {db_name}")
            return client[db_name]
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    @staticmethod
    def _categorize_job_level(title):
        """
        Internal helper to map job titles to seniority levels.
        """
        title = str(title).lower()
        if "senior" in title:
            return "senior"
        if "junior" in title:
            return "junior"
        if "mid" in title or "regular" in title:
            return "mid"
        return "Other"

    def _fetch_and_clean_data(self, platform_name):
        """
        Retrieve data from MongoDB and perform initial cleaning/feature engineering.
        """
        if platform_name == CollectionEnum.JUST_JOIN:
            data = list(self.db.jobs_processed_jj.find())
        elif platform_name == CollectionEnum.NO_FLUFF_JOBS:
            data = list(self.db.jobs_processed.find())
        else:
            raise NameError(f"Collection for {platform_name} not found.")

        df = pd.DataFrame(data)

        # Select and validate required columns
        required_cols = ["source", "job_title", "min_salary", "max_salary", "location"]
        df = df[[col for col in required_cols if col in df.columns]]

        # Clean salary data
        df = df.dropna(subset=["min_salary", "max_salary"])
        df["avg_salary"] = (df["min_salary"] + df["max_salary"]) / 2

        # Engineering the 'job_level' feature
        df["job_level"] = df["job_title"].apply(self._categorize_job_level)

        return df

    def train_and_evaluate(self, platform_name):
        """
        Main pipeline: Load data, train RandomForest model, and print metrics.
        """
        df = self._fetch_and_clean_data(platform_name)

        if df.empty:
            print(f"⚠️ No data available for {platform_name.value}. Skipping...")
            return None

        X = df[self.categorical_features]
        y = df["avg_salary"]

        # Build Pipeline
        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore"), self.categorical_features)
            ]
        )

        model_pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", RandomForestRegressor(n_estimators=100, random_state=42))
        ])

        # Split and Train
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model_pipeline.fit(X_train, y_train)

        # Evaluation
        y_pred = model_pipeline.predict(X_test)
        print(f"\n--- Result: {platform_name.value} ---")
        print(f"MAE: {mean_absolute_error(y_test, y_pred):.2f} PLN")
        print(f"R²: {r2_score(y_test, y_pred):.2f}")

        # Visualization
        self._run_visualizations(df, platform_name)

        return model_pipeline

    def _run_visualizations(self, df, platform_name):
        """
        Generates statistical plots.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Histogram
        ax1.hist(df["avg_salary"], bins=30, color='skyblue', edgecolor='black')
        ax1.set_title(f"{platform_name.value}: Salary Distribution")
        ax1.set_xlabel("Salary (PLN)")

        # Boxplot
        df.boxplot(column="avg_salary", by="job_level", ax=ax2)
        ax2.set_title(f"Salary by Level ({platform_name.value})")
        plt.suptitle("") # Clear automatic title

        plt.tight_layout()
        plt.show()




