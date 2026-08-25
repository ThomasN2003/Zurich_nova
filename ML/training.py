from pathlib import Path
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from xgboost import XGBRegressor


# ==========================================================
# CONFIGURATION
# ==========================================================

RANDOM_STATE = 42
TEST_SIZE = 0.20
CROSS_VALIDATION_FOLDS = 5

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "medical_insurance_processed.csv"

MODEL_PATH = BASE_DIR / "premium_model.pkl"
ERROR_MARGIN_PATH = BASE_DIR / "error_margin.pkl"
AVERAGE_PREMIUM_PATH = BASE_DIR / "average_premium.pkl"
MODEL_METRICS_PATH = BASE_DIR / "model_metrics.pkl"
MODEL_METADATA_PATH = BASE_DIR / "model_metadata.json"

PREDICTION_RESULTS_PATH = BASE_DIR / "prediction_results.csv"
FEATURE_IMPORTANCE_CSV_PATH = BASE_DIR / "feature_importance.csv"
FEATURE_IMPORTANCE_IMAGE_PATH = BASE_DIR / "feature_importance.png"

REQUIRED_COLUMNS = [
    "age",
    "gender",
    "bmi",
    "children",
    "discount_eligibility",
    "region",
    "premium",
]

MODEL_FEATURES = [
    "age",
    "bmi",
    "children",
    "gender",
    "discount_eligibility",
    "region",
    "age_squared",
    "bmi_squared",
    "age_bmi",
]

CATEGORICAL_FEATURES = [
    "gender",
    "discount_eligibility",
    "region",
]

NUMERIC_FEATURES = [
    "age",
    "bmi",
    "children",
    "age_squared",
    "bmi_squared",
    "age_bmi",
]

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def print_heading(title):
    """Print a clear section heading in the terminal."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def validate_and_clean_data(data):
    """Validate required fields and perform lightweight cleaning."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "The dataset is missing these required columns: "
            + ", ".join(missing_columns)
        )

    cleaned = data.copy()

    # Standardise column names.
    cleaned.columns = (
        cleaned.columns
        .str.strip()
        .str.lower()
    )

    # Standardise text values.
    for column in CATEGORICAL_FEATURES:
        cleaned[column] = (
            cleaned[column]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # Convert numerical columns safely.
    numeric_columns = [
        "age",
        "bmi",
        "children",
        "premium",
    ]

    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(
            cleaned[column],
            errors="coerce",
        )

    rows_before = len(cleaned)
    duplicates_before = int(cleaned.duplicated().sum())

    cleaned = cleaned.drop_duplicates()

    # Remove rows that cannot be used for training.
    cleaned = cleaned.dropna(
        subset=REQUIRED_COLUMNS
    )

    # Keep only sensible values for this demonstration dataset.
    cleaned = cleaned[
        cleaned["age"].between(18, 100)
        & cleaned["bmi"].between(10, 70)
        & cleaned["children"].between(0, 20)
        & (cleaned["premium"] >= 0)
    ].copy()

    # Only keep known categories.
    cleaned = cleaned[
        cleaned["gender"].isin(["male", "female"])
        & cleaned["discount_eligibility"].isin(["yes", "no"])
        & cleaned["region"].isin(
            [
                "northeast",
                "northwest",
                "southeast",
                "southwest",
            ]
        )
    ].copy()

    rows_removed = rows_before - len(cleaned)

    print(f"Rows loaded:                 {rows_before}")
    print(f"Duplicate rows found:        {duplicates_before}")
    print(f"Rows removed during cleaning:{rows_removed:>9}")
    print(f"Rows available for training: {len(cleaned)}")

    if len(cleaned) < 50:
        raise ValueError(
            "Too few valid rows remain after cleaning."
        )

    return cleaned


def add_engineered_features(data):
    """Create the same engineered features used by the application."""
    featured = data.copy()

    featured["age_squared"] = (
        featured["age"] ** 2
    )

    featured["bmi_squared"] = (
        featured["bmi"] ** 2
    )

    featured["age_bmi"] = (
        featured["age"] * featured["bmi"]
    )

    return featured


def save_feature_importance(trained_pipeline):
    """Save model feature importance as CSV and PNG."""
    feature_names = (
        trained_pipeline
        .named_steps["preprocessor"]
        .get_feature_names_out()
    )

    importance_values = (
        trained_pipeline
        .named_steps["model"]
        .feature_importances_
    )

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importance_values,
        }
    )

    # Remove preprocessing prefixes for clearer display.
    importance_df["feature"] = (
        importance_df["feature"]
        .str.replace("cat__", "", regex=False)
        .str.replace("num__", "", regex=False)
        .str.replace(
            "discount_eligibility_",
            "discount_",
            regex=False,
        )
        .str.replace("_", " ")
        .str.title()
    )

    importance_df = (
        importance_df
        .sort_values(
            by="importance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    importance_df.to_csv(
        FEATURE_IMPORTANCE_CSV_PATH,
        index=False,
    )

    top_features = (
        importance_df
        .head(12)
        .sort_values(
            by="importance",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        top_features["feature"],
        top_features["importance"],
        color="#2167d5",
    )

    ax.set_title(
        "Overall Model Feature Importance",
        fontsize=15,
        fontweight="bold",
    )

    ax.set_xlabel("Relative importance")
    ax.set_ylabel("Feature")
    ax.grid(
        axis="x",
        alpha=0.20,
    )

    fig.tight_layout()

    fig.savefig(
        FEATURE_IMPORTANCE_IMAGE_PATH,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

    return importance_df


# ==========================================================
# LOAD AND PREPARE THE DATA
# ==========================================================

print_heading("LOADING AND CLEANING DATA")

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Could not find: {DATA_PATH.name}\n"
        "Place the processed dataset in the same folder "
        "as training.py."
    )

df = pd.read_csv(DATA_PATH)
df = validate_and_clean_data(df)
df = add_engineered_features(df)

X = df[MODEL_FEATURES].copy()
y = df["premium"].copy()

# The expenses field is deliberately excluded because it could
# leak information that would not be available from the UI.

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
)


# ==========================================================
# PREPROCESSING AND MODEL PIPELINE
# ==========================================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
            CATEGORICAL_FEATURES,
        ),
        (
            "numeric",
            "passthrough",
            NUMERIC_FEATURES,
        ),
    ],
    remainder="drop",
)

base_model = XGBRegressor(
    objective="reg:squarederror",
    random_state=RANDOM_STATE,
    n_jobs=1,
    tree_method="hist",
    verbosity=0,
)

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", base_model),
    ]
)


# ==========================================================
# HYPERPARAMETER TUNING
# ==========================================================

parameter_distributions = {
    "model__n_estimators": [
        150,
        250,
        350,
        500,
    ],
    "model__max_depth": [
        2,
        3,
        4,
        5,
    ],
    "model__learning_rate": [
        0.02,
        0.04,
        0.06,
        0.10,
    ],
    "model__subsample": [
        0.75,
        0.90,
        1.00,
    ],
    "model__colsample_bytree": [
        0.75,
        0.90,
        1.00,
    ],
    "model__min_child_weight": [
        1,
        3,
        5,
    ],
    "model__reg_alpha": [
        0.0,
        0.05,
        0.20,
    ],
    "model__reg_lambda": [
        1.0,
        2.0,
        5.0,
    ],
}

search = RandomizedSearchCV(
    estimator=pipeline,
    param_distributions=parameter_distributions,
    n_iter=20,
    scoring="neg_mean_absolute_error",
    cv=CROSS_VALIDATION_FOLDS,
    random_state=RANDOM_STATE,
    n_jobs=1,
    verbose=1,
    refit=True,
    return_train_score=False,
)

print_heading("STARTING HYPERPARAMETER SEARCH")

search.fit(X_train, y_train)
best_pipeline = search.best_estimator_

print("\nBest parameters:")

for parameter, value in search.best_params_.items():
    clean_name = parameter.replace("model__", "")
    print(f"  {clean_name}: {value}")

print(
    "\nBest validation MAE during search: "
    f"£{-search.best_score_:,.2f}"
)


# ==========================================================
# CROSS-VALIDATION AND TEST EVALUATION
# ==========================================================

print_heading("EVALUATING THE MODEL")

cv_mae_scores = -cross_val_score(
    best_pipeline,
    X,
    y,
    scoring="neg_mean_absolute_error",
    cv=CROSS_VALIDATION_FOLDS,
    n_jobs=1,
)

cv_r2_scores = cross_val_score(
    best_pipeline,
    X,
    y,
    scoring="r2",
    cv=CROSS_VALIDATION_FOLDS,
    n_jobs=1,
)

predictions = best_pipeline.predict(X_test)
predictions = np.maximum(predictions, 0)

mae = float(
    mean_absolute_error(
        y_test,
        predictions,
    )
)

rmse = float(
    np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )
)

r2 = float(
    r2_score(
        y_test,
        predictions,
    )
)

average_premium = float(
    y.mean()
)

median_premium = float(
    y.median()
)

# This is a typical error range, not a formal confidence interval.
absolute_errors = np.abs(
    y_test.to_numpy() - predictions
)

typical_error = float(
    np.mean(absolute_errors)
)

error_80th_percentile = float(
    np.percentile(
        absolute_errors,
        80,
    )
)

print(f"Test MAE:               £{mae:,.2f}")
print(f"Test RMSE:              £{rmse:,.2f}")
print(f"Test R-squared:          {r2:.4f}")
print(
    "Mean cross-validation MAE: "
    f"£{cv_mae_scores.mean():,.2f}"
)
print(
    "Mean cross-validation R²:  "
    f"{cv_r2_scores.mean():.4f}"
)
print(
    "Cross-validation R² SD:    "
    f"{cv_r2_scores.std():.4f}"
)
print(
    "80% of test errors were no more than: "
    f"£{error_80th_percentile:,.2f}"
)


# ==========================================================
# SAVE MODEL OUTPUTS
# ==========================================================

print_heading("SAVING MODEL OUTPUTS")

joblib.dump(
    best_pipeline,
    MODEL_PATH,
)

joblib.dump(
    typical_error,
    ERROR_MARGIN_PATH,
)

joblib.dump(
    average_premium,
    AVERAGE_PREMIUM_PATH,
)

model_metrics = {
    "test_mae": mae,
    "test_rmse": rmse,
    "test_r2": r2,
    "cv_mae_mean": float(
        cv_mae_scores.mean()
    ),
    "cv_mae_std": float(
        cv_mae_scores.std()
    ),
    "cv_r2_mean": float(
        cv_r2_scores.mean()
    ),
    "cv_r2_std": float(
        cv_r2_scores.std()
    ),
    "typical_error": typical_error,
    "error_80th_percentile": error_80th_percentile,
    "average_premium": average_premium,
    "median_premium": median_premium,
    "training_rows": int(len(df)),
    "training_features": int(len(MODEL_FEATURES)),
}

joblib.dump(
    model_metrics,
    MODEL_METRICS_PATH,
)

model_metadata = {
    "model_type": "XGBoost Regressor",
    "target": "premium",
    "included_features": MODEL_FEATURES,
    "excluded_leakage_fields": [
        "premium",
        "expenses",
    ],
    "best_parameters": {
        key.replace("model__", ""): value
        for key, value in search.best_params_.items()
    },
    "random_state": RANDOM_STATE,
    "test_size": TEST_SIZE,
    "cross_validation_folds": CROSS_VALIDATION_FOLDS,
}

with open(
    MODEL_METADATA_PATH,
    "w",
    encoding="utf-8",
) as metadata_file:
    json.dump(
        model_metadata,
        metadata_file,
        indent=4,
    )

prediction_results = X_test.copy()
prediction_results["actual_premium"] = (
    y_test.to_numpy()
)
prediction_results["predicted_premium"] = (
    predictions
)
prediction_results["absolute_error"] = (
    absolute_errors
)

prediction_results.to_csv(
    PREDICTION_RESULTS_PATH,
    index=False,
)

importance_df = save_feature_importance(
    best_pipeline
)

print("\nTop model features:")
print(
    importance_df
    .head(10)
    .to_string(index=False)
)

print("\nFiles created or updated:")
print(f"  - {MODEL_PATH.name}")
print(f"  - {ERROR_MARGIN_PATH.name}")
print(f"  - {AVERAGE_PREMIUM_PATH.name}")
print(f"  - {MODEL_METRICS_PATH.name}")
print(f"  - {MODEL_METADATA_PATH.name}")
print(f"  - {PREDICTION_RESULTS_PATH.name}")
print(f"  - {FEATURE_IMPORTANCE_CSV_PATH.name}")
print(f"  - {FEATURE_IMPORTANCE_IMAGE_PATH.name}")

print_heading("TRAINING COMPLETE")
print(
    "You can now start the application with:\n"
    "streamlit run app.py"
)