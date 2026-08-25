import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, r2_score

from xgboost import XGBRegressor

# =========================
# LOAD
# =========================

df = pd.read_csv("medical_insurance_processed.csv")

# =========================
# FEATURES / TARGET
# =========================

X = df[
    [
        "age",
        "gender",
        "bmi",
        "children",
        "discount_eligibility",
        "region"
    ]
]

y = df["premium"]

# =========================
# PREPROCESSING
# =========================

categorical_features = [
    "gender",
    "discount_eligibility",
    "region"
]

numeric_features = [
    "age",
    "bmi",
    "children"
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

# =========================
# MODEL
# =========================

model = XGBRegressor(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    random_state=42
)

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", model)
])

# =========================
# TRAIN TEST SPLIT
# =========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

pipeline.fit(X_train, y_train)

# =========================
# EVALUATION
# =========================

preds = pipeline.predict(X_test)

mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print("\nModel Performance")
print(f"MAE: {mae:.2f}")
print(f"R² : {r2:.3f}")

# =========================
# SAVE
# =========================

joblib.dump(
    pipeline,
    "premium_model.pkl"
)

print("\nModel saved as premium_model.pkl")