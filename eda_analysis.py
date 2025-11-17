import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Path to your CSV file
DATA_PATH = os.path.join("data", "retail_store_sample.csv")

def load_data():
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    return df

def eda_summary(df):
    print("===== DATA HEAD =====")
    print(df.head())

    print("\n===== DATA INFO =====")
    print(df.info())

    print("\n===== STATISTICS =====")
    print(df.describe())

    print("\n===== MISSING VALUES =====")
    print(df.isna().sum())

def category_distribution(df):
    plt.figure(figsize=(8, 5))
    df['category'].value_counts().plot(kind='bar')
    plt.title("Category Distribution")
    plt.xlabel("Category")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig("eda/category_distribution.png")
    plt.close()

def correlation_heatmap(df):
    plt.figure(figsize=(6, 5))
    sns.heatmap(df[['sales', 'customers']].corr(), annot=True)
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig("eda/correlation_heatmap.png")
    plt.close()


if __name__ == "__main__":
    df = load_data()
    eda_summary(df)
    category_distribution(df)
    correlation_heatmap(df)

    print("\nEDA completed. Plots saved inside the 'eda/' folder.")
