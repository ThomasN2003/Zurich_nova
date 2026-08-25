from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Premium Estimator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "premium_model.pkl"
ERROR_MARGIN_PATH = BASE_DIR / "error_margin.pkl"
AVERAGE_PREMIUM_PATH = BASE_DIR / "average_premium.pkl"
MODEL_METRICS_PATH = BASE_DIR / "model_metrics.pkl"
FEATURE_IMPORTANCE_PATH = BASE_DIR / "feature_importance.csv"


# ==========================================================
# CLEAN, READABLE STYLING
# ==========================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero {
            padding: 2rem 2.2rem;
            border-radius: 18px;
            background:
                linear-gradient(
                    135deg,
                    #092f57 0%,
                    #0b5cab 100%
                );
            color: white;
            margin-bottom: 1.5rem;
        }

        .hero h1 {
            color: white;
            margin: 0;
            font-size: 2.35rem;
            line-height: 1.2;
        }

        .hero p {
            color: #eaf3fb;
            margin-top: 0.75rem;
            margin-bottom: 0;
            font-size: 1.05rem;
            max-width: 800px;
        }

        .section-card {
            border: 1px solid #dce4ec;
            border-radius: 14px;
            padding: 1.25rem 1.4rem;
            background-color: white;
            margin-bottom: 1rem;
        }

        .result-card {
            border: 1px solid #b8d3ef;
            border-radius: 16px;
            padding: 1.4rem;
            background-color: #f3f8fd;
            min-height: 150px;
        }

        .result-label {
            color: #425466;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
        }

        .result-value {
            color: #092f57;
            font-size: 2rem;
            font-weight: 750;
            line-height: 1.2;
        }

        .result-note {
            color: #526579;
            font-size: 0.9rem;
            margin-top: 0.55rem;
        }

        .comparison-positive {
            color: #9b2c2c;
            font-weight: 700;
        }

        .comparison-negative {
            color: #17663a;
            font-weight: 700;
        }

        div[data-testid="stButton"] > button {
            min-height: 3.25rem;
            border-radius: 10px;
            font-size: 1.05rem;
            font-weight: 700;
        }

        div[data-testid="stMetric"] {
            border: 1px solid #e1e7ed;
            border-radius: 12px;
            padding: 1rem;
            background-color: white;
        }

        .small-note {
            color: #596b7d;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# LOAD SAVED ASSETS
# ==========================================================

required_files = [
    MODEL_PATH,
    ERROR_MARGIN_PATH,
    AVERAGE_PREMIUM_PATH,
    MODEL_METRICS_PATH,
]

missing_files = [
    path.name
    for path in required_files
    if not path.exists()
]

if missing_files:
    st.error(
        "The application cannot start because these trained "
        "model files are missing:"
    )

    for file_name in missing_files:
        st.write(f"- `{file_name}`")

    st.info(
        "Run `python training.py` successfully, then restart "
        "the Streamlit application."
    )

    st.stop()


@st.cache_resource
def load_model_assets():
    """Load trained model artefacts once per app session."""
    loaded_model = joblib.load(MODEL_PATH)
    loaded_error = float(
        joblib.load(ERROR_MARGIN_PATH)
    )
    loaded_average = float(
        joblib.load(AVERAGE_PREMIUM_PATH)
    )
    loaded_metrics = joblib.load(
        MODEL_METRICS_PATH
    )

    return (
        loaded_model,
        loaded_error,
        loaded_average,
        loaded_metrics,
    )


@st.cache_data
def load_feature_importance():
    """Load the saved global feature importance data."""
    if not FEATURE_IMPORTANCE_PATH.exists():
        return None

    return pd.read_csv(
        FEATURE_IMPORTANCE_PATH
    )


model, typical_error, average_premium, metrics = (
    load_model_assets()
)

feature_importance = load_feature_importance()


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def get_bmi_category(bmi):
    """Return an explanatory BMI band."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Healthy range"
    if bmi < 30:
        return "Overweight"
    return "Obese range"


def build_customer_record(
    age,
    bmi,
    children,
    gender,
    discount_eligibility,
    region,
):
    """Build one model-ready customer record."""
    return pd.DataFrame(
        [
            {
                "age": age,
                "bmi": bmi,
                "children": children,
                "gender": gender,
                "discount_eligibility": (
                    discount_eligibility
                ),
                "region": region,
                "age_squared": age ** 2,
                "bmi_squared": bmi ** 2,
                "age_bmi": age * bmi,
            }
        ]
    )


def format_label(value):
    """Make stored category values readable."""
    return str(value).replace("_", " ").title()


# ==========================================================
# SESSION STATE
# ==========================================================

if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None


# ==========================================================
# HEADER
# ==========================================================

st.markdown(
    """
    <div class="hero">
        <h1>Insurance Premium Estimator</h1>
        <p>
            Enter a small set of customer details to receive an
            illustrative premium estimate from the trained XGBoost
            model. The result also includes a typical prediction
            range and a comparison with the dataset average.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.header("About this demonstration")

    st.write(
        "The model predicts the premium using age, BMI, number "
        "of children, gender, region, and discount eligibility."
    )

    st.info(
        "Medical expenses are deliberately excluded to avoid "
        "giving the model information that would not normally "
        "be entered by a customer."
    )

    st.divider()

    st.subheader("Model snapshot")

    st.metric(
        "Test R²",
        f"{float(metrics['test_r2']):.3f}",
    )

    st.metric(
        "Test MAE",
        f"£{float(metrics['test_mae']):,.2f}",
    )

    st.caption(
        "R² measures how much variation the model explains. "
        "MAE is the model's average absolute test error."
    )


# ==========================================================
# INPUT FORM
# ==========================================================

st.header("1. Enter customer details")

st.write(
    "Choose an example profile or enter custom values. "
    "All fields are required."
)

profile_options = {
    "Custom profile": {
        "age": 35,
        "bmi": 27.5,
        "children": 0,
        "gender": "male",
        "discount": "no",
        "region": "northwest",
    },
    "Young individual": {
        "age": 23,
        "bmi": 23.0,
        "children": 0,
        "gender": "female",
        "discount": "yes",
        "region": "northeast",
    },
    "Family household": {
        "age": 38,
        "bmi": 28.0,
        "children": 2,
        "gender": "male",
        "discount": "no",
        "region": "southwest",
    },
    "Older customer": {
        "age": 58,
        "bmi": 30.0,
        "children": 1,
        "gender": "female",
        "discount": "yes",
        "region": "southeast",
    },
}

selected_profile_name = st.selectbox(
    "Example profile",
    list(profile_options.keys()),
)

selected_profile = profile_options[
    selected_profile_name
]

with st.form("premium_prediction_form"):
    input_col_1, input_col_2, input_col_3 = (
        st.columns(3)
    )

    with input_col_1:
        age = st.number_input(
            "Age",
            min_value=18,
            max_value=100,
            value=int(selected_profile["age"]),
            step=1,
            help="Age of the customer in years.",
        )

        gender_options = [
            "male",
            "female",
        ]

        gender = st.selectbox(
            "Gender",
            gender_options,
            index=gender_options.index(
                selected_profile["gender"]
            ),
            format_func=format_label,
        )

    with input_col_2:
        bmi = st.number_input(
            "Body mass index (BMI)",
            min_value=10.0,
            max_value=70.0,
            value=float(selected_profile["bmi"]),
            step=0.1,
            help=(
                "BMI is used here because it is present in the "
                "demonstration training dataset."
            ),
        )

        children = st.number_input(
            "Number of children",
            min_value=0,
            max_value=20,
            value=int(selected_profile["children"]),
            step=1,
        )

    with input_col_3:
        discount_options = [
            "no",
            "yes",
        ]

        discount_eligibility = st.selectbox(
            "Discount eligible",
            discount_options,
            index=discount_options.index(
                selected_profile["discount"]
            ),
            format_func=format_label,
        )

        region_options = [
            "northeast",
            "northwest",
            "southeast",
            "southwest",
        ]

        region = st.selectbox(
            "Region",
            region_options,
            index=region_options.index(
                selected_profile["region"]
            ),
            format_func=format_label,
        )

    submitted = st.form_submit_button(
        "Calculate premium estimate",
        type="primary",
        use_container_width=True,
    )


# ==========================================================
# MAKE PREDICTION
# ==========================================================

if submitted:
    customer_data = build_customer_record(
        age=int(age),
        bmi=float(bmi),
        children=int(children),
        gender=gender,
        discount_eligibility=(
            discount_eligibility
        ),
        region=region,
    )

    raw_prediction = model.predict(
        customer_data
    )[0]

    prediction = max(
        float(raw_prediction),
        0.0,
    )

    lower_estimate = max(
        prediction - typical_error,
        0.0,
    )

    upper_estimate = (
        prediction + typical_error
    )

    difference_amount = (
        prediction - average_premium
    )

    if average_premium != 0:
        difference_percentage = (
            difference_amount
            / average_premium
            * 100
        )
    else:
        difference_percentage = 0.0

    st.session_state.prediction_result = {
        "prediction": prediction,
        "lower_estimate": lower_estimate,
        "upper_estimate": upper_estimate,
        "difference_amount": difference_amount,
        "difference_percentage": (
            difference_percentage
        ),
        "age": int(age),
        "bmi": float(bmi),
        "bmi_category": get_bmi_category(
            float(bmi)
        ),
        "children": int(children),
        "gender": format_label(gender),
        "discount": format_label(
            discount_eligibility
        ),
        "region": format_label(region),
    }


# ==========================================================
# DISPLAY RESULTS
# ==========================================================

result = st.session_state.prediction_result

if result is None:
    st.info(
        "Complete the form and select "
        "'Calculate premium estimate' to see the result."
    )

else:
    st.divider()
    st.header("2. Your premium estimate")

    result_col_1, result_col_2, result_col_3 = (
        st.columns(3)
    )

    with result_col_1:
        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">
                    Predicted premium
                </div>
                <div class="result-value">
                    £{result["prediction"]:,.2f}
                </div>
                <div class="result-note">
                    The central estimate produced by the
                    trained model.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with result_col_2:
        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">
                    Typical estimate range
                </div>
                <div class="result-value">
                    £{result["lower_estimate"]:,.2f}
                    to
                    £{result["upper_estimate"]:,.2f}
                </div>
                <div class="result-note">
                    Based on the model's average absolute
                    error on held-out test data.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with result_col_3:
        comparison_class = (
            "comparison-positive"
            if result["difference_amount"] > 0
            else "comparison-negative"
        )

        comparison_word = (
            "above"
            if result["difference_amount"] > 0
            else "below"
        )

        if result["difference_amount"] == 0:
            comparison_word = "equal to"

        st.markdown(
            f"""
            <div class="result-card">
                <div class="result-label">
                    Compared with dataset average
                </div>
                <div class="result-value">
                    {result["difference_percentage"]:+.1f}%
                </div>
                <div class="result-note">
                    <span class="{comparison_class}">
                        £{abs(result["difference_amount"]):,.2f}
                        {comparison_word} average
                    </span>
                    <br>
                    Dataset average:
                    £{average_premium:,.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(
        "The typical estimate range is not a guaranteed result "
        "or a formal statistical confidence interval."
    )

    st.subheader("Customer summary")

    summary_col_1, summary_col_2, summary_col_3 = (
        st.columns(3)
    )

    with summary_col_1:
        st.metric(
            "Age",
            f"{result['age']} years",
        )

        st.metric(
            "Gender",
            result["gender"],
        )

    with summary_col_2:
        st.metric(
            "BMI",
            f"{result['bmi']:.1f}",
        )

        st.metric(
            "BMI band",
            result["bmi_category"],
        )

    with summary_col_3:
        st.metric(
            "Children",
            result["children"],
        )

        st.metric(
            "Region",
            result["region"],
        )

    if result["discount"] == "Yes":
        st.success(
            "The estimate includes the customer's recorded "
            "discount eligibility."
        )
    else:
        st.info(
            "This profile is not recorded as discount eligible."
        )


# ==========================================================
# MODEL EXPLAINABILITY
# ==========================================================

st.divider()
st.header("3. Understand the model")

explanation_col_1, explanation_col_2 = (
    st.columns([1.15, 0.85])
)

with explanation_col_1:
    st.subheader("What influences predictions overall?")

    st.write(
        "The chart shows which inputs had the greatest overall "
        "influence across the training data. It does not explain "
        "one individual prediction on its own."
    )

    if (
        feature_importance is not None
        and not feature_importance.empty
    ):
        chart_data = (
            feature_importance
            .head(10)
            .set_index("feature")[["importance"]]
        )

        st.bar_chart(
            chart_data,
            horizontal=True,
            color="#2167d5",
        )
    else:
        st.info(
            "Run `python training.py` to generate the feature "
            "importance information."
        )

with explanation_col_2:
    st.subheader("Model performance")

    metric_col_1, metric_col_2 = st.columns(2)

    with metric_col_1:
        st.metric(
            "Test R²",
            f"{float(metrics['test_r2']):.3f}",
            help=(
                "The proportion of variation in test premiums "
                "explained by the model. Higher is generally better."
            ),
        )

        st.metric(
            "Test RMSE",
            f"£{float(metrics['test_rmse']):,.2f}",
            help=(
                "A measure that gives additional weight to "
                "larger prediction errors."
            ),
        )

    with metric_col_2:
        st.metric(
            "Test MAE",
            f"£{float(metrics['test_mae']):,.2f}",
            help=(
                "The average absolute difference between "
                "predicted and actual premiums."
            ),
        )

        st.metric(
            "Cross-validation R²",
            f"{float(metrics['cv_r2_mean']):.3f}",
            help=(
                "Average R² across multiple validation folds."
            ),
        )

    st.write(
        f"The model was trained using "
        f"**{int(metrics['training_rows']):,} records** "
        f"and evaluated on a separate test set."
    )


# ==========================================================
# METHODOLOGY AND LIMITATIONS
# ==========================================================

with st.expander(
    "Methodology and limitations",
    expanded=False,
):
    st.markdown(
        """
        **Method**

        - XGBoost regression model
        - One-hot encoding for categorical values
        - Engineered age, BMI, and interaction features
        - Randomised hyperparameter search
        - Five-fold cross-validation
        - Separate held-out test set

        **Important limitations**

        - The model learns patterns from the supplied demonstration
          dataset and can reproduce limitations or biases in that data.
        - Feature importance describes the model, not causation.
        - The displayed estimate range uses average historical model
          error and is not a guarantee.
        - Medical expenses are excluded to reduce target leakage and
          keep the inputs suitable for a simple user interface.
        - The model has not been calibrated or validated for real
          insurance pricing, underwriting, or eligibility decisions.
        """
    )


# ==========================================================
# FOOTER
# ==========================================================

st.warning(
    "Proof of concept only. The estimate must not be used for "
    "real insurance pricing, underwriting, eligibility, medical, "
    "or financial decisions."
)

st.caption(
    "Demonstration application built with Streamlit, scikit-learn, "
    "and XGBoost."
)