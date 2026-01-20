import pandas as pd
import numpy as np               
import matplotlib.pyplot as plt  
from collections import Counter  
from wordcloud import WordCloud  

from enum import Enum            
from constant import CollectionEnum
from pymongo import MongoClient

class JobDataCloudImageGenerator:
    def __init__(self):
        """
        Initialize the visualization class.
        :param db_client: An active MongoDB database instance.
        """
        client = MongoClient('mongodb://localhost:27017/')
        self.db = client['BD_final']
        # Standard configuration for WordCloud generation
        self.max_words=15
        self.wc_params = {
            'width': 600,
            'height': 400,
            'background_color': 'white',
            'colormap': 'viridis'
        }

    def _get_data_from_db(self, platform_name):
        """
        Internal method: Fetches raw data from MongoDB based on platform enum
        and converts it into a pandas DataFrame.
        """
        if platform_name == CollectionEnum.JUST_JOIN:
            data = list(self.db.jobs_processed_jj.find())
        elif platform_name == CollectionEnum.NO_FLUFF_JOBS:
            data = list(self.db.jobs_processed.find())
        else:
            raise NameError(f"Unknown collection name for: {platform_name}")

        return pd.DataFrame(data)

    def _extract_skills(self, df):
        """
        Internal method: Cleans and extracts the list of skills from the DataFrame.
        Handles both list-type and string-type entries in 'must_have_skills' columns.
        """
        skill_cols = [col for col in df.columns if 'must_have_skills' in col]
        raw_skills = df[skill_cols].values.flatten()

        all_skills = []
        for item in raw_skills:
            if isinstance(item, (list, np.ndarray)):
                for s in item:
                    if pd.notna(s) and str(s).strip() != '':
                        all_skills.append(str(s).strip().lower())
            elif pd.notna(item) and str(item).strip() != '':
                all_skills.append(str(item).strip().lower())
        return all_skills

    def draw_word_cloud(self, platform_name, ax, ):
        """
        Core method: Generates and renders a word cloud onto a specific Matplotlib axis.
        """
        df = self._get_data_from_db(platform_name)

        if df.empty:
            ax.set_title(f"{platform_name.value} (No Data Found)")
            ax.axis('off')
            return

        all_skills = self._extract_skills(df)
        skill_counts = Counter(all_skills)

        # Generate WordCloud object from frequency dictionary
        wc = WordCloud(
            **self.wc_params,
            max_words=self.max_words
        ).generate_from_frequencies(skill_counts)

        # Render settings
        ax.imshow(wc, interpolation='bilinear')
        ax.set_title(f"Platform: {platform_name.value}", fontsize=18, fontweight='bold')
        ax.axis('off')

    def compare_platforms(self, platforms, save_path='combined_skills_comparison.png'):
        """
        High-level method: Creates a side-by-side comparison chart for multiple platforms.
        : param platforms: A list of platform enums, e.g., [Enum1, Enum2]
        : param save_path: File path to save the generated image.
        """
        n = len(platforms)
        fig, axes = plt.subplots(1, n, figsize=(10 * n, 10))

        # Ensure axes is iterable even if only one platform is provided
        if n == 1:
            axes = [axes]

        for platform, ax in zip(platforms, axes):
            self.draw_word_cloud(platform, ax)

        plt.tight_layout()
        plt.savefig(save_path)
        print(f"\nThe most important {self.max_words} skills\n")
        plt.show()
        print(f"Comparison chart saved successfully to: {save_path}")