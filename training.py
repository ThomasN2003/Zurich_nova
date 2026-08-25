import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    cross_val_score
)

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from sklearn.metrics import (
    mean_absolute_error,
    r2_score
)

from xgboost import XGBRegressor

# ==========================================================
# LOAD DATA
# ==========================================================

df = pd.read_csv("medical_insurance_processed.csv")

# ==========================================================
# FEATURE ENGINEERING
# ==========================================================

df["age_squared"] = df["age"] ** 2
df["bmi_squared"] = df["bmi"] ** 2
df["age_bmi"] = df["age"] * df["bmi"]

# ==========================================================
# FEATURES / TARGET
# ==========================================================

X = df[
    [
        "age",
        "bmi",
        "children",
        "gender",
        "discount_eligibility",
        "region",
        "age_squared",
        "bmi_squared",
        "age_bmi"
    ]
]

y = df["premium"]

# ==========================================================
# TRAIN / TEST SPLIT
# ==========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# ==========================================================
# PREPROCESSING
# ==========================================================

categorical_features = [
    "gender",
    "discount_eligibility",
    "region"
]

numeric_features = [
    "age",
    "bmi",
    "children",
    "age_squared",
    "bmi_squared",
    "age_bmi"
]

preprocessor = ColumnTransformer(
    transformers=[
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        ),
        (
            "num",
            "passthrough",
            numeric_features
        )
    ]
)

# ==========================================================
# BASE MODEL
# ==========================================================

xgb_model = XGBRegressor(
    objective="reg:squarederror",
    random_state=42
)

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", xgb_model)
])

# ==========================================================
# HYPERPARAMETER SEARCH
# ==========================================================

param_grid = {
    "model__n_estimators": [200, 300, 500],
    "model__max_depth": [3, 4, 5, 6],
    "model__learning_rate": [0.01, 0.03, 0.05, 0.1],
    "model__subsample": [0.8, 1.0],
    "model__colsample_bytree": [0.8, 1.0]
}

search = RandomizedSearchCV(
    estimator=pipeline,
    param_distributions=param_grid,
    n_iter=20,
    cv=5,
    scoring="r2",
    verbose=1,
    random_state=42,
    n_jobs=1
)

print("=" * 60)
print("STARTING HYPERPARAMETER SEARCH")
print("=" * 60)

search.fit(X_train, y_train)

pipeline = search.best_estimator_

print("\nBest Parameters:")
print(search.best_params_)

print("\nBest Cross Validation Score:")
print(search.best_score_)

# ==========================================================
# CROSS VALIDATION
# ==========================================================

cv_scores = cross_val_score(
    pipeline,
    X,
    y,
    cv=5,
    scoring="r2",
    n_jobs=1
)

print("\nCross Validation Results")
print(f"Mean R² : {cv_scores.mean():.4f}")
print(f"Std  R² : {cv_scores.std():.4f}")

# ==========================================================
# EVALUATE
# ==========================================================

preds = pipeline.predict(X_test)

mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print("\nModel Performance")
print(f"MAE: {mae:.2f}")
print(f"R² : {r2:.4f}")

# ==========================================================
# ERROR MARGIN
# ==========================================================

error_margin = np.abs(y_test - preds).mean()

print(f"\nAverage Error Margin: £{error_margin:.2f}")

# ==========================================================
# SAVE MODEL
# ==========================================================

joblib.dump(
    pipeline,
    "premium_model.pkl"
)

joblib.dump(
    error_margin,
    "error_margin.pkl"
)

print("\nSaved:")
print("- premium_model.pkl")
print("- error_margin.pkl")

# ==========================================================
# SAVE PREDICTIONS
# ==========================================================

results = pd.DataFrame({
    "actual": y_test,
    "predicted": preds
})

results.to_csv(
    "prediction_results.csv",
    index=False
)

print("- prediction_results.csv")

# ==========================================================
# FEATURE IMPORTANCE
# ==========================================================

feature_names = (
    pipeline.named_steps["preprocessor"]
    .get_feature_names_out()
)

importance = (
    pipeline.named_steps["model"]
    .feature_importances_
)

importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": importance
})

importance_df = (
    importance_df
    .sort_values(
        by="importance",
        ascending=False
    )
)

print("\nTop Features")
print(
    importance_df.head(15)
)

plt.figure(figsize=(10, 6))

importance_df.head(15).sort_values(
    by="importance"
).plot(
    x="feature",
    y="importance",
    kind="barh",
    legend=False
)

plt.title("Top Feature Importances")
plt.tight_layout()
plt.savefig("feature_importance.png")
plt.show()

print("\nSaved:")
print("- feature_importance.png")

print("\nTraining Complete")