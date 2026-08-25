import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ====================================================
# 1. LOAD DATA
# ====================================================

df = pd.read_csv("medical_insurance.csv")

print("=" * 50)
print("DATA OVERVIEW")
print("=" * 50)
print(df.head())
print("\nShape:", df.shape)

# ====================================================
# 2. DATA QUALITY CHECKS
# ====================================================

print("\nMissing Values")
print(df.isnull().sum())

print("\nDuplicate Rows:", df.duplicated().sum())

print("\nData Types")
print(df.dtypes)

print("\nSummary Statistics")
print(df.describe(include="all"))

# Remove duplicates if present
df = df.drop_duplicates()

# ====================================================
# 3. CLEANING
# ====================================================

# Standardize string columns
for col in ["gender", "discount_eligibility", "region"]:
    df[col] = df[col].astype(str).str.strip().str.lower()

# Convert categoricals
df["discount_eligibility_flag"] = (
    df["discount_eligibility"]
    .map({"yes": 1, "no": 0})
)

df["gender_flag"] = (
    df["gender"]
    .map({"male": 1, "female": 0})
)

# ====================================================
# 4. FEATURE ENGINEERING
# ====================================================

# BMI Categories
def bmi_category(bmi):
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"

df["bmi_category"] = df["bmi"].apply(bmi_category)

# Age Groups
df["age_group"] = pd.cut(
    df["age"],
    bins=[0, 25, 40, 60, 100],
    labels=["young", "adult", "middle_age", "senior"]
)

# Family Size Indicator
df["large_family"] = np.where(df["children"] >= 3, 1, 0)

# Interaction Feature
df["age_bmi_interaction"] = df["age"] * df["bmi"]

# Expense Per Child
df["expense_per_child"] = np.where(
    df["children"] > 0,
    df["expenses"] / df["children"],
    df["expenses"]
)

# Premium Ratio
df["premium_expense_ratio"] = (
    df["premium"] / df["expenses"]
)

# High Cost Customer Flag
high_cost_threshold = df["expenses"].quantile(0.75)

df["high_cost_customer"] = (
    df["expenses"] > high_cost_threshold
).astype(int)

# ====================================================
# 5. EXPLORATORY ANALYSIS
# ====================================================

print("\nAverage Expenses by Region")
print(df.groupby("region")["expenses"].mean().sort_values())

print("\nAverage Expenses by Gender")
print(df.groupby("gender")["expenses"].mean())

print("\nAverage Expenses by BMI Category")
print(df.groupby("bmi_category")["expenses"].mean())

print("\nAverage Expenses by Discount Eligibility")
print(df.groupby("discount_eligibility")["expenses"].mean())

# ====================================================
# 6. VISUALIZATIONS
# ====================================================

sns.set_style("whitegrid")

# Distribution of expenses
plt.figure(figsize=(8, 5))
sns.histplot(df["expenses"], bins=30, kde=True)
plt.title("Distribution of Medical Expenses")
plt.tight_layout()
plt.show()

# Expense by BMI category
plt.figure(figsize=(8, 5))
sns.boxplot(data=df, x="bmi_category", y="expenses")
plt.title("Expenses by BMI Category")
plt.tight_layout()
plt.show()

# Expense by region
plt.figure(figsize=(8, 5))
sns.barplot(
    data=df,
    x="region",
    y="expenses",
    estimator=np.mean
)
plt.title("Average Expenses by Region")
plt.tight_layout()
plt.show()

# Correlation matrix
numeric_cols = df.select_dtypes(include=np.number)

plt.figure(figsize=(10, 8))
sns.heatmap(
    numeric_cols.corr(),
    annot=True,
    cmap="coolwarm",
    fmt=".2f"
)
plt.title("Correlation Matrix")
plt.tight_layout()
plt.show()

# ====================================================
# 7. SAVE PROCESSED DATA
# ====================================================

df.to_csv(
    "medical_insurance_processed.csv",
    index=False
)

print("\nProcessed dataset saved:")
print("medical_insurance_processed.csv")

print("\nFinal Shape:")
print(df.shape)