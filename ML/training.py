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
CROSS_VALIDATION_FOLDS = 3

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "medical_insurance_processed.csv"

CONTRIBUTION_MODEL_PATH = (
    BASE_DIR / "treatment_contribution_model.pkl"
)

EXPENSE_MODEL_PATH = (
    BASE_DIR / "annual_expense_model.pkl"
)

MODEL_METRICS_PATH = (
    BASE_DIR / "model_metrics.pkl"
)

REFERENCE_DATA_PATH = (
    BASE_DIR / "pricing_reference.csv"
)

CONTRIBUTION_RESULTS_PATH = (
    BASE_DIR / "contribution_prediction_results.csv"
)

EXPENSE_RESULTS_PATH = (
    BASE_DIR / "expense_prediction_results.csv"
)

CONTRIBUTION_IMPORTANCE_PATH = (
    BASE_DIR / "contribution_feature_importance.csv"
)

EXPENSE_IMPORTANCE_PATH = (
    BASE_DIR / "expense_feature_importance.csv"
)

CONTRIBUTION_IMPORTANCE_IMAGE_PATH = (
    BASE_DIR / "contribution_feature_importance.png"
)

EXPENSE_IMPORTANCE_IMAGE_PATH = (
    BASE_DIR / "expense_feature_importance.png"
)

MODEL_METADATA_PATH = (
    BASE_DIR / "model_metadata.json"
)


# ==========================================================
# DATA DEFINITIONS
# ==========================================================

REQUIRED_COLUMNS = [
    "age",
    "gender",
    "bmi",
    "children",
    "discount_eligibility",
    "region",
    "expenses",
    "premium",
]

CATEGORICAL_FEATURES = [
    "gender",
    "discount_eligibility",
    "region",
]

BASE_NUMERIC_FEATURES = [
    "age",
    "bmi",
    "children",
]

ENGINEERED_FEATURES = [
    "age_squared",
    "bmi_squared",
    "age_bmi",
]

CUSTOMER_FEATURES = [
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

CONTRIBUTION_FEATURES = (
    CUSTOMER_FEATURES + ["expenses"]
)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def print_heading(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def validate_and_clean_data(data):
    """Validate and clean the source dataset."""

    cleaned = data.copy()

    cleaned.columns = (
        cleaned.columns
        .str.strip()
        .str.lower()
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in cleaned.columns
    ]

    if missing_columns:
        raise ValueError(
            "The dataset is missing these required columns: "
            + ", ".join(missing_columns)
        )

    for column in CATEGORICAL_FEATURES:
        cleaned[column] = (
            cleaned[column]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    numeric_columns = [
        "age",
        "bmi",
        "children",
        "expenses",
        "premium",
    ]

    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(
            cleaned[column],
            errors="coerce",
        )

    original_rows = len(cleaned)
    duplicate_rows = int(
        cleaned.duplicated().sum()
    )

    cleaned = cleaned.drop_duplicates()

    cleaned = cleaned.dropna(
        subset=REQUIRED_COLUMNS
    )

    cleaned = cleaned[
        cleaned["age"].between(18, 100)
        & cleaned["bmi"].between(10, 70)
        & cleaned["children"].between(0, 20)
        & (cleaned["expenses"] > 0)
        & (cleaned["premium"] >= 0)
    ].copy()

    cleaned = cleaned[
        cleaned["gender"].isin(
            ["male", "female"]
        )
        & cleaned[
            "discount_eligibility"
        ].isin(["yes", "no"])
        & cleaned["region"].isin(
            [
                "northeast",
                "northwest",
                "southeast",
                "southwest",
            ]
        )
    ].copy()

    removed_rows = original_rows - len(cleaned)

    print(f"Rows loaded:                  {original_rows}")
    print(f"Duplicate rows found:         {duplicate_rows}")
    print(f"Rows removed during cleaning: {removed_rows}")
    print(f"Rows available for training:  {len(cleaned)}")

    if len(cleaned) < 100:
        raise ValueError(
            "Too few valid rows remain for model training."
        )

    return cleaned


def add_engineered_features(data):
    """Add nonlinear features used by both models."""

    result = data.copy()

    result["age_squared"] = (
        result["age"] ** 2
    )

    result["bmi_squared"] = (
        result["bmi"] ** 2
    )

    result["age_bmi"] = (
        result["age"] * result["bmi"]
    )

    return result


def make_preprocessor(include_expenses=False):
    """Build preprocessing for a model."""

    numeric_features = (
        BASE_NUMERIC_FEATURES
        + ENGINEERED_FEATURES
    )

    if include_expenses:
        numeric_features = (
            numeric_features + ["expenses"]
        )

    return ColumnTransformer(
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
                numeric_features,
            ),
        ],
        remainder="drop",
    )


def make_pipeline(include_expenses=False):
    """Create an XGBoost preprocessing pipeline."""

    model = XGBRegressor(
        objective="reg:squarederror",
        random_state=RANDOM_STATE,
        n_jobs=1,
        tree_method="hist",
        verbosity=0,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                make_preprocessor(
                    include_expenses=include_expenses
                ),
            ),
            ("model", model),
        ]
    )


def tune_model(
    pipeline,
    X_train,
    y_train,
    model_name,
):
    """Perform a quick hyperparameter search."""

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
            0.80,
            0.90,
            1.00,
        ],
        "model__colsample_bytree": [
            0.80,
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
        n_iter=12,
        scoring="neg_mean_absolute_error",
        cv=CROSS_VALIDATION_FOLDS,
        random_state=RANDOM_STATE,
        n_jobs=1,
        verbose=1,
        refit=True,
    )

    print_heading(
        f"TUNING {model_name.upper()}"
    )

    search.fit(
        X_train,
        y_train,
    )

    print(
        "\nBest cross-validation MAE: "
        f"£{-search.best_score_:,.2f}"
    )

    print("\nBest parameters:")

    for parameter, value in (
        search.best_params_.items()
    ):
        clean_name = parameter.replace(
            "model__",
            "",
        )

        print(f"  {clean_name}: {value}")

    return (
        search.best_estimator_,
        search.best_params_,
        float(-search.best_score_),
    )


def evaluate_model(
    model,
    X_test,
    y_test,
    model_name,
):
    """Calculate test metrics and predictions."""

    predictions = model.predict(X_test)

    predictions = np.maximum(
        predictions,
        0,
    )

    actual_values = y_test.to_numpy()

    absolute_errors = np.abs(
        actual_values - predictions
    )

    mae = float(
        mean_absolute_error(
            actual_values,
            predictions,
        )
    )

    rmse = float(
        np.sqrt(
            mean_squared_error(
                actual_values,
                predictions,
            )
        )
    )

    r2 = float(
        r2_score(
            actual_values,
            predictions,
        )
    )

    typical_error = float(
        absolute_errors.mean()
    )

    error_80 = float(
        np.percentile(
            absolute_errors,
            80,
        )
    )

    print_heading(
        f"{model_name.upper()} PERFORMANCE"
    )

    print(f"Test MAE:                    £{mae:,.2f}")
    print(f"Test RMSE:                   £{rmse:,.2f}")
    print(f"Test R-squared:               {r2:.4f}")
    print(
        "80% of test errors within: "
        f"£{error_80:,.2f}"
    )

    metrics = {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "typical_error": typical_error,
        "error_80": error_80,
    }

    return (
        predictions,
        absolute_errors,
        metrics,
    )


def save_feature_importance(
    trained_pipeline,
    csv_path,
    image_path,
    chart_title,
):
    """Save readable overall feature importance."""

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

    importance_df["feature"] = (
        importance_df["feature"]
        .str.replace(
            "categorical__",
            "",
            regex=False,
        )
        .str.replace(
            "numeric__",
            "",
            regex=False,
        )
        .str.replace(
            "discount_eligibility_",
            "discount_",
            regex=False,
        )
        .str.replace(
            "_",
            " ",
        )
        .str.title()
    )

    importance_df = (
        importance_df
        .sort_values(
            "importance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    importance_df.to_csv(
        csv_path,
        index=False,
    )

    chart_data = (
        importance_df
        .head(12)
        .sort_values(
            "importance",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.barh(
        chart_data["feature"],
        chart_data["importance"],
        color="#2167d5",
    )

    ax.set_title(
        chart_title,
        fontsize=15,
        fontweight="bold",
    )

    ax.set_xlabel(
        "Relative importance"
    )

    ax.grid(
        axis="x",
        alpha=0.20,
    )

    fig.tight_layout()

    fig.savefig(
        image_path,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

    return importance_df


def create_pricing_reference(data):
    """Create summary information for the app."""

    reference_data = data.copy()

    reference_data["age_group"] = pd.cut(
        reference_data["age"],
        bins=[
            17,
            25,
            35,
            45,
            55,
            65,
            100,
        ],
        labels=[
            "18 to 25",
            "26 to 35",
            "36 to 45",
            "46 to 55",
            "56 to 65",
            "66 and over",
        ],
        include_lowest=True,
    )

    reference_data["bmi_group"] = pd.cut(
        reference_data["bmi"],
        bins=[
            0,
            18.5,
            25,
            30,
            float("inf"),
        ],
        labels=[
            "Underweight",
            "Healthy range",
            "Overweight",
            "Obese range",
        ],
        right=False,
    )

    summaries = []

    group_definitions = {
        "Age group": "age_group",
        "BMI group": "bmi_group",
        "Discount eligibility": (
            "discount_eligibility"
        ),
        "Region": "region",
        "Gender": "gender",
        "Children": "children",
    }

    for category_name, column_name in (
        group_definitions.items()
    ):
        grouped = (
            reference_data
            .groupby(
                column_name,
                observed=True,
            )
            .agg(
                record_count=(
                    "expenses",
                    "size",
                ),
                average_treatment_cost=(
                    "expenses",
                    "mean",
                ),
                median_treatment_cost=(
                    "expenses",
                    "median",
                ),
                average_customer_contribution=(
                    "premium",
                    "mean",
                ),
                average_contribution_rate=(
                    "contribution_rate",
                    "mean",
                ),
            )
            .reset_index()
        )

        grouped = grouped.rename(
            columns={
                column_name: "group_value"
            }
        )

        grouped.insert(
            0,
            "category",
            category_name,
        )

        summaries.append(grouped)

    pricing_reference = pd.concat(
        summaries,
        ignore_index=True,
    )

    pricing_reference[
        "average_contribution_rate"
    ] = (
        pricing_reference[
            "average_contribution_rate"
        ]
        * 100
    )

    pricing_reference.to_csv(
        REFERENCE_DATA_PATH,
        index=False,
    )

    return pricing_reference


# ==========================================================
# LOAD AND CLEAN DATA
# ==========================================================

print_heading(
    "LOADING AND CLEANING DATA"
)

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Could not find {DATA_PATH.name}. "
        "Place the processed dataset in the same "
        "folder as training.py."
    )

df = pd.read_csv(DATA_PATH)

df = validate_and_clean_data(df)

df = add_engineered_features(df)

df["contribution_rate"] = np.where(
    df["expenses"] > 0,
    df["premium"] / df["expenses"],
    0,
)

df["insurer_contribution"] = np.maximum(
    df["expenses"] - df["premium"],
    0,
)

print(
    "\nDataset assumptions used by this proof of concept:"
)
print(
    "- Each row represents one person and one treatment claim."
)
print(
    "- expenses is the hospital treatment cost."
)
print(
    "- premium is treated as the customer claim contribution."
)
print(
    "- No person appears more than once."
)


# ==========================================================
# TRAIN SHARED TEST SPLIT
# ==========================================================

train_indices, test_indices = train_test_split(
    df.index,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
)

train_data = df.loc[train_indices].copy()
test_data = df.loc[test_indices].copy()


# ==========================================================
# MODEL 1: TREATMENT CONTRIBUTION
# ==========================================================

X_contribution_train = train_data[
    CONTRIBUTION_FEATURES
].copy()

X_contribution_test = test_data[
    CONTRIBUTION_FEATURES
].copy()

y_contribution_train = train_data[
    "premium"
].copy()

y_contribution_test = test_data[
    "premium"
].copy()

contribution_pipeline = make_pipeline(
    include_expenses=True
)

(
    contribution_model,
    contribution_best_parameters,
    contribution_cv_mae,
) = tune_model(
    contribution_pipeline,
    X_contribution_train,
    y_contribution_train,
    "treatment contribution model",
)

(
    contribution_predictions,
    contribution_absolute_errors,
    contribution_metrics,
) = evaluate_model(
    contribution_model,
    X_contribution_test,
    y_contribution_test,
    "treatment contribution model",
)

joblib.dump(
    contribution_model,
    CONTRIBUTION_MODEL_PATH,
)

contribution_results = (
    X_contribution_test.copy()
)

contribution_results[
    "actual_customer_contribution"
] = y_contribution_test.to_numpy()

contribution_results[
    "predicted_customer_contribution"
] = contribution_predictions

contribution_results[
    "absolute_error"
] = contribution_absolute_errors

contribution_results.to_csv(
    CONTRIBUTION_RESULTS_PATH,
    index=False,
)

contribution_importance = (
    save_feature_importance(
        contribution_model,
        CONTRIBUTION_IMPORTANCE_PATH,
        CONTRIBUTION_IMPORTANCE_IMAGE_PATH,
        (
            "Treatment Contribution Model "
            "Feature Importance"
        ),
    )
)


# ==========================================================
# MODEL 2: EXPECTED TREATMENT EXPENSE
# ==========================================================

X_expense_train = train_data[
    CUSTOMER_FEATURES
].copy()

X_expense_test = test_data[
    CUSTOMER_FEATURES
].copy()

y_expense_train = train_data[
    "expenses"
].copy()

y_expense_test = test_data[
    "expenses"
].copy()

expense_pipeline = make_pipeline(
    include_expenses=False
)

(
    expense_model,
    expense_best_parameters,
    expense_cv_mae,
) = tune_model(
    expense_pipeline,
    X_expense_train,
    y_expense_train,
    "expected treatment expense model",
)

(
    expense_predictions,
    expense_absolute_errors,
    expense_metrics,
) = evaluate_model(
    expense_model,
    X_expense_test,
    y_expense_test,
    "expected treatment expense model",
)

joblib.dump(
    expense_model,
    EXPENSE_MODEL_PATH,
)

expense_results = X_expense_test.copy()

expense_results[
    "actual_treatment_expense"
] = y_expense_test.to_numpy()

expense_results[
    "predicted_treatment_expense"
] = expense_predictions

expense_results[
    "absolute_error"
] = expense_absolute_errors

expense_results.to_csv(
    EXPENSE_RESULTS_PATH,
    index=False,
)

expense_importance = save_feature_importance(
    expense_model,
    EXPENSE_IMPORTANCE_PATH,
    EXPENSE_IMPORTANCE_IMAGE_PATH,
    (
        "Expected Treatment Expense Model "
        "Feature Importance"
    ),
)


# ==========================================================
# REFERENCE DATA AND SAVED METRICS
# ==========================================================

print_heading(
    "CREATING PRICING REFERENCE DATA"
)

pricing_reference = create_pricing_reference(
    df
)

overall_statistics = {
    "record_count": int(len(df)),
    "average_treatment_cost": float(
        df["expenses"].mean()
    ),
    "median_treatment_cost": float(
        df["expenses"].median()
    ),
    "average_customer_contribution": float(
        df["premium"].mean()
    ),
    "median_customer_contribution": float(
        df["premium"].median()
    ),
    "average_customer_contribution_rate": float(
        df["contribution_rate"].mean()
    ),
    "average_insurer_contribution": float(
        df["insurer_contribution"].mean()
    ),
}

model_metrics = {
    "contribution_model": {
        **contribution_metrics,
        "cross_validation_mae": (
            contribution_cv_mae
        ),
    },
    "expense_model": {
        **expense_metrics,
        "cross_validation_mae": (
            expense_cv_mae
        ),
    },
    "overall_statistics": overall_statistics,
}

joblib.dump(
    model_metrics,
    MODEL_METRICS_PATH,
)

metadata = {
    "project_type": (
        "Insurance pricing proof of concept"
    ),
    "dataset_assumptions": [
        (
            "Each row represents one person and "
            "one treatment claim."
        ),
        (
            "Expenses is treated as the hospital "
            "treatment cost."
        ),
        (
            "Premium is treated as the customer's "
            "treatment contribution."
        ),
        (
            "The yearly policy illustration uses "
            "transparent pricing assumptions and "
            "is not actuarially validated."
        ),
    ],
    "contribution_model": {
        "target": "premium",
        "features": CONTRIBUTION_FEATURES,
        "best_parameters": {
            key.replace(
                "model__",
                "",
            ): value
            for key, value in (
                contribution_best_parameters.items()
            )
        },
    },
    "expense_model": {
        "target": "expenses",
        "features": CUSTOMER_FEATURES,
        "best_parameters": {
            key.replace(
                "model__",
                "",
            ): value
            for key, value in (
                expense_best_parameters.items()
            )
        },
    },
}

with open(
    MODEL_METADATA_PATH,
    "w",
    encoding="utf-8",
) as metadata_file:
    json.dump(
        metadata,
        metadata_file,
        indent=4,
    )


# ==========================================================
# FINAL SUMMARY
# ==========================================================

print_heading(
    "TRAINING COMPLETE"
)

print("\nCreated or updated:")

created_files = [
    CONTRIBUTION_MODEL_PATH,
    EXPENSE_MODEL_PATH,
    MODEL_METRICS_PATH,
    REFERENCE_DATA_PATH,
    CONTRIBUTION_RESULTS_PATH,
    EXPENSE_RESULTS_PATH,
    CONTRIBUTION_IMPORTANCE_PATH,
    EXPENSE_IMPORTANCE_PATH,
    CONTRIBUTION_IMPORTANCE_IMAGE_PATH,
    EXPENSE_IMPORTANCE_IMAGE_PATH,
    MODEL_METADATA_PATH,
]

for file_path in created_files:
    print(f"- {file_path.name}")

print(
    "\nStart the application with:"
)
print(
    "streamlit run app.py"
)