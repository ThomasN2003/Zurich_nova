from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Insurance Pricing PoC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent

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

CONTRIBUTION_IMPORTANCE_PATH = (
    BASE_DIR / "contribution_feature_importance.csv"
)

EXPENSE_IMPORTANCE_PATH = (
    BASE_DIR / "expense_feature_importance.csv"
)


# ==========================================================
# STYLING
# ==========================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero {
            padding: 2rem 2.2rem;
            border-radius: 18px;
            background: linear-gradient(
                135deg,
                #062f57 0%,
                #0b67b2 100%
            );
            color: white;
            margin-bottom: 1.5rem;
        }

        .hero h1 {
            color: white;
            margin: 0;
            font-size: 2.35rem;
        }

        .hero p {
            color: #eaf4fc;
            margin-top: 0.7rem;
            margin-bottom: 0;
            font-size: 1.05rem;
            max-width: 850px;
        }

        .result-card {
            background-color: #f4f8fc;
            border: 1px solid #bdd4e8;
            border-radius: 14px;
            padding: 1.25rem;
            min-height: 155px;
        }

        .result-label {
            color: #425466;
            font-size: 0.95rem;
            font-weight: 650;
        }

        .result-value {
            color: #07345e;
            font-size: 1.9rem;
            font-weight: 750;
            margin-top: 0.35rem;
        }

        .result-note {
            color: #5c6d7d;
            font-size: 0.88rem;
            margin-top: 0.55rem;
        }

        .breakdown-card {
            border: 1px solid #d9e2ea;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            background-color: white;
            margin-bottom: 0.75rem;
        }

        div[data-testid="stButton"] > button {
            min-height: 3.2rem;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid #e0e7ee;
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
# LOAD ASSETS
# ==========================================================

required_files = [
    CONTRIBUTION_MODEL_PATH,
    EXPENSE_MODEL_PATH,
    MODEL_METRICS_PATH,
    REFERENCE_DATA_PATH,
]

missing_files = [
    path.name
    for path in required_files
    if not path.exists()
]

if missing_files:
    st.error(
        "The application cannot start because trained "
        "model files are missing."
    )

    for file_name in missing_files:
        st.write(f"- `{file_name}`")

    st.info(
        "Run `python training.py` successfully, "
        "then restart Streamlit."
    )

    st.stop()


@st.cache_resource
def load_models():
    contribution_model = joblib.load(
        CONTRIBUTION_MODEL_PATH
    )

    expense_model = joblib.load(
        EXPENSE_MODEL_PATH
    )

    metrics = joblib.load(
        MODEL_METRICS_PATH
    )

    return (
        contribution_model,
        expense_model,
        metrics,
    )


@st.cache_data
def load_reference_data():
    return pd.read_csv(
        REFERENCE_DATA_PATH
    )


@st.cache_data
def load_importance(path):
    if not path.exists():
        return None

    return pd.read_csv(path)


(
    contribution_model,
    expense_model,
    metrics,
) = load_models()

reference_data = load_reference_data()

contribution_importance = load_importance(
    CONTRIBUTION_IMPORTANCE_PATH
)

expense_importance = load_importance(
    EXPENSE_IMPORTANCE_PATH
)


# ==========================================================
# HELPERS
# ==========================================================

def format_label(value):
    return (
        str(value)
        .replace("_", " ")
        .title()
    )


def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"

    if bmi < 25:
        return "Healthy range"

    if bmi < 30:
        return "Overweight"

    return "Obese range"


def get_age_group(age):
    if age <= 25:
        return "18 to 25"

    if age <= 35:
        return "26 to 35"

    if age <= 45:
        return "36 to 45"

    if age <= 55:
        return "46 to 55"

    if age <= 65:
        return "56 to 65"

    return "66 and over"


def build_customer_record(
    age,
    bmi,
    children,
    gender,
    discount_eligibility,
    region,
    expenses=None,
):
    record = {
        "age": int(age),
        "bmi": float(bmi),
        "children": int(children),
        "gender": gender,
        "discount_eligibility": (
            discount_eligibility
        ),
        "region": region,
        "age_squared": float(age) ** 2,
        "bmi_squared": float(bmi) ** 2,
        "age_bmi": float(age) * float(bmi),
    }

    if expenses is not None:
        record["expenses"] = float(expenses)

    return pd.DataFrame([record])


def predict_contribution(
    customer_record,
    treatment_cost,
):
    raw_prediction = contribution_model.predict(
        customer_record
    )[0]

    contribution = max(
        float(raw_prediction),
        0.0,
    )

    # A customer contribution cannot exceed
    # the hospital bill.
    contribution = min(
        contribution,
        float(treatment_cost),
    )

    return contribution


def display_customer_form(
    form_key,
    button_text,
    include_treatment_cost=False,
):
    with st.form(form_key):
        column_1, column_2, column_3 = (
            st.columns(3)
        )

        with column_1:
            age = st.number_input(
                "Age",
                min_value=18,
                max_value=100,
                value=35,
                step=1,
                key=f"{form_key}_age",
            )

            gender = st.selectbox(
                "Gender",
                ["male", "female"],
                format_func=format_label,
                key=f"{form_key}_gender",
            )

        with column_2:
            bmi = st.number_input(
                "Body mass index (BMI)",
                min_value=10.0,
                max_value=70.0,
                value=27.5,
                step=0.1,
                key=f"{form_key}_bmi",
            )

            children = st.number_input(
                "Number of children",
                min_value=0,
                max_value=20,
                value=0,
                step=1,
                key=f"{form_key}_children",
            )

        with column_3:
            discount = st.selectbox(
                "Discount eligible",
                ["no", "yes"],
                format_func=format_label,
                key=f"{form_key}_discount",
            )

            region = st.selectbox(
                "Region",
                [
                    "northeast",
                    "northwest",
                    "southeast",
                    "southwest",
                ],
                format_func=format_label,
                key=f"{form_key}_region",
            )

        treatment_cost = None

        if include_treatment_cost:
            treatment_cost = st.number_input(
                "Hospital treatment cost",
                min_value=1.0,
                max_value=1_000_000.0,
                value=10_000.0,
                step=100.0,
                format="%.2f",
                help=(
                    "The amount requested by the hospital "
                    "for this treatment."
                ),
                key=f"{form_key}_treatment_cost",
            )

        submitted = st.form_submit_button(
            button_text,
            type="primary",
            use_container_width=True,
        )

    return {
        "submitted": submitted,
        "age": int(age),
        "bmi": float(bmi),
        "children": int(children),
        "gender": gender,
        "discount": discount,
        "region": region,
        "treatment_cost": treatment_cost,
    }


def show_feature_chart(
    importance_data,
    title,
):
    st.subheader(title)

    if (
        importance_data is None
        or importance_data.empty
    ):
        st.info(
            "Feature importance data is unavailable. "
            "Run training.py again."
        )
        return

    chart_data = (
        importance_data
        .head(10)
        .set_index("feature")[["importance"]]
    )

    st.bar_chart(
        chart_data,
        horizontal=True,
        color="#2167d5",
    )

    st.caption(
        "This shows overall model importance across "
        "the dataset. It does not prove that a feature "
        "caused a particular result."
    )


# ==========================================================
# SESSION STATE
# ==========================================================

if "claim_result" not in st.session_state:
    st.session_state.claim_result = None

if "policy_result" not in st.session_state:
    st.session_state.policy_result = None


# ==========================================================
# HEADER
# ==========================================================

st.markdown(
    """
    <div class="hero">
        <h1>Insurance Pricing Proof of Concept</h1>
        <p>
            Estimate an existing policyholder's contribution
            towards a hospital treatment, or create an
            illustrative annual policy price from expected
            treatment costs and transparent pricing assumptions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.header("Model overview")

    st.write(
        "Two XGBoost models support this application."
    )

    st.markdown(
        """
        **Treatment contribution model**

        Uses the customer details and hospital bill to
        estimate the amount paid by the customer.

        **Policy illustration model**

        Uses customer details to estimate treatment cost.
        Transparent pricing assumptions are then applied
        to create annual and monthly illustrations.
        """
    )

    st.divider()

    st.metric(
        "Contribution model R²",
        (
            f"{metrics['contribution_model']['r2']:.3f}"
        ),
    )

    st.metric(
        "Expense model R²",
        (
            f"{metrics['expense_model']['r2']:.3f}"
        ),
    )

    st.caption(
        "These scores describe performance on held-out "
        "test data. They do not make the models suitable "
        "for live insurance decisions."
    )


# ==========================================================
# TABS
# ==========================================================

claim_tab, policy_tab, insights_tab = st.tabs(
    [
        "Treatment contribution",
        "Policy illustration",
        "Dataset insights",
    ]
)


# ==========================================================
# TAB 1: TREATMENT CONTRIBUTION
# ==========================================================

with claim_tab:
    st.header(
        "Existing policyholder treatment contribution"
    )

    st.write(
        "Enter the policyholder's details and the amount "
        "requested by the hospital. The model estimates "
        "the amount the customer contributes and the amount "
        "the insurer covers."
    )

    claim_inputs = display_customer_form(
        form_key="claim_form",
        button_text=(
            "Calculate treatment contribution"
        ),
        include_treatment_cost=True,
    )

    if claim_inputs["submitted"]:
        claim_record = build_customer_record(
            age=claim_inputs["age"],
            bmi=claim_inputs["bmi"],
            children=claim_inputs["children"],
            gender=claim_inputs["gender"],
            discount_eligibility=(
                claim_inputs["discount"]
            ),
            region=claim_inputs["region"],
            expenses=(
                claim_inputs["treatment_cost"]
            ),
        )

        customer_contribution = (
            predict_contribution(
                claim_record,
                claim_inputs["treatment_cost"],
            )
        )

        insurer_contribution = max(
            claim_inputs["treatment_cost"]
            - customer_contribution,
            0,
        )

        customer_percentage = (
            customer_contribution
            / claim_inputs["treatment_cost"]
            * 100
        )

        contribution_error = float(
            metrics[
                "contribution_model"
            ]["typical_error"]
        )

        lower_contribution = max(
            customer_contribution
            - contribution_error,
            0,
        )

        upper_contribution = min(
            customer_contribution
            + contribution_error,
            claim_inputs["treatment_cost"],
        )

        st.session_state.claim_result = {
            "treatment_cost": (
                claim_inputs["treatment_cost"]
            ),
            "customer_contribution": (
                customer_contribution
            ),
            "insurer_contribution": (
                insurer_contribution
            ),
            "customer_percentage": (
                customer_percentage
            ),
            "lower_contribution": (
                lower_contribution
            ),
            "upper_contribution": (
                upper_contribution
            ),
            "age": claim_inputs["age"],
            "bmi": claim_inputs["bmi"],
            "bmi_group": get_bmi_category(
                claim_inputs["bmi"]
            ),
            "region": format_label(
                claim_inputs["region"]
            ),
            "discount": format_label(
                claim_inputs["discount"]
            ),
        }

    claim_result = (
        st.session_state.claim_result
    )

    if claim_result is None:
        st.info(
            "Complete the form to calculate the "
            "treatment contribution."
        )

    else:
        st.divider()
        st.subheader("Contribution estimate")

        result_column_1, result_column_2, result_column_3 = (
            st.columns(3)
        )

        with result_column_1:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Hospital treatment cost
                    </div>
                    <div class="result-value">
                        £{claim_result["treatment_cost"]:,.2f}
                    </div>
                    <div class="result-note">
                        Total amount requested by the hospital.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with result_column_2:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Estimated customer contribution
                    </div>
                    <div class="result-value">
                        £{claim_result["customer_contribution"]:,.2f}
                    </div>
                    <div class="result-note">
                        Approximately
                        {claim_result["customer_percentage"]:.2f}%
                        of the treatment bill.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with result_column_3:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Estimated insurer contribution
                    </div>
                    <div class="result-value">
                        £{claim_result["insurer_contribution"]:,.2f}
                    </div>
                    <div class="result-note">
                        Treatment cost less the estimated
                        customer contribution.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.info(
            "Typical customer contribution range: "
            f"£{claim_result['lower_contribution']:,.2f} "
            f"to £{claim_result['upper_contribution']:,.2f}. "
            "This range uses average historical model error "
            "and is not a guarantee."
        )

        st.subheader("Policyholder summary")

        summary_1, summary_2, summary_3, summary_4 = (
            st.columns(4)
        )

        summary_1.metric(
            "Age",
            claim_result["age"],
        )

        summary_2.metric(
            "BMI",
            f"{claim_result['bmi']:.1f}",
        )

        summary_3.metric(
            "BMI band",
            claim_result["bmi_group"],
        )

        summary_4.metric(
            "Region",
            claim_result["region"],
        )

        show_feature_chart(
            contribution_importance,
            (
                "What influences treatment "
                "contributions overall?"
            ),
        )


# ==========================================================
# TAB 2: POLICY ILLUSTRATION
# ==========================================================

with policy_tab:
    st.header("Illustrative policy pricing")

    st.write(
        "The model estimates one expected treatment cost "
        "for the customer. The application then estimates "
        "the insurer-funded portion and adds transparent "
        "administration, uncertainty, and margin assumptions."
    )

    policy_inputs = display_customer_form(
        form_key="policy_form",
        button_text=(
            "Create policy illustration"
        ),
        include_treatment_cost=False,
    )

    st.subheader("Illustrative pricing assumptions")

    assumption_column_1, assumption_column_2, assumption_column_3 = (
        st.columns(3)
    )

    with assumption_column_1:
        claims_per_year = st.number_input(
            "Expected treatments per year",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help=(
                "The dataset contains one claim per person. "
                "The default therefore assumes one treatment "
                "exposure per year."
            ),
        )

    with assumption_column_2:
        administration_rate = st.slider(
            "Administration loading",
            min_value=0,
            max_value=30,
            value=10,
            step=1,
            format="%d%%",
        )

    with assumption_column_3:
        uncertainty_rate = st.slider(
            "Uncertainty and contingency loading",
            min_value=0,
            max_value=30,
            value=10,
            step=1,
            format="%d%%",
        )

    margin_rate = st.slider(
        "Illustrative margin",
        min_value=0,
        max_value=20,
        value=5,
        step=1,
        format="%d%%",
    )

    st.caption(
        "These assumptions are editable demonstration "
        "inputs. They were not learned from the dataset."
    )

    if policy_inputs["submitted"]:
        quote_eligible = all(
            [
                policy_inputs["age"] >= 18,
                policy_inputs["bmi"] > 0,
                policy_inputs["children"] >= 0,
                bool(policy_inputs["gender"]),
                bool(policy_inputs["discount"]),
                bool(policy_inputs["region"]),
            ]
        )

        customer_record = build_customer_record(
            age=policy_inputs["age"],
            bmi=policy_inputs["bmi"],
            children=policy_inputs["children"],
            gender=policy_inputs["gender"],
            discount_eligibility=(
                policy_inputs["discount"]
            ),
            region=policy_inputs["region"],
        )

        predicted_treatment_cost = max(
            float(
                expense_model.predict(
                    customer_record
                )[0]
            ),
            0,
        )

        contribution_record = (
            customer_record.copy()
        )

        contribution_record["expenses"] = (
            predicted_treatment_cost
        )

        predicted_claim_contribution = (
            predict_contribution(
                contribution_record,
                predicted_treatment_cost,
            )
        )

        expected_insurer_cost_per_treatment = max(
            predicted_treatment_cost
            - predicted_claim_contribution,
            0,
        )

        annual_expected_claim_cost = (
            expected_insurer_cost_per_treatment
            * float(claims_per_year)
        )

        administration_amount = (
            annual_expected_claim_cost
            * administration_rate
            / 100
        )

        uncertainty_amount = (
            annual_expected_claim_cost
            * uncertainty_rate
            / 100
        )

        margin_amount = (
            annual_expected_claim_cost
            * margin_rate
            / 100
        )

        annual_policy_price = (
            annual_expected_claim_cost
            + administration_amount
            + uncertainty_amount
            + margin_amount
        )

        monthly_policy_price = (
            annual_policy_price / 12
        )

        expense_error = float(
            metrics[
                "expense_model"
            ]["typical_error"]
        )

        lower_expected_cost = max(
            predicted_treatment_cost
            - expense_error,
            0,
        )

        upper_expected_cost = (
            predicted_treatment_cost
            + expense_error
        )

        st.session_state.policy_result = {
            "eligible": quote_eligible,
            "predicted_treatment_cost": (
                predicted_treatment_cost
            ),
            "lower_expected_cost": (
                lower_expected_cost
            ),
            "upper_expected_cost": (
                upper_expected_cost
            ),
            "predicted_claim_contribution": (
                predicted_claim_contribution
            ),
            "expected_insurer_cost_per_treatment": (
                expected_insurer_cost_per_treatment
            ),
            "annual_expected_claim_cost": (
                annual_expected_claim_cost
            ),
            "administration_amount": (
                administration_amount
            ),
            "uncertainty_amount": (
                uncertainty_amount
            ),
            "margin_amount": margin_amount,
            "annual_policy_price": (
                annual_policy_price
            ),
            "monthly_policy_price": (
                monthly_policy_price
            ),
            "claims_per_year": (
                claims_per_year
            ),
            "administration_rate": (
                administration_rate
            ),
            "uncertainty_rate": (
                uncertainty_rate
            ),
            "margin_rate": margin_rate,
            "age_group": get_age_group(
                policy_inputs["age"]
            ),
            "bmi_group": get_bmi_category(
                policy_inputs["bmi"]
            ),
        }

    policy_result = (
        st.session_state.policy_result
    )

    if policy_result is None:
        st.info(
            "Complete the customer form and select "
            "'Create policy illustration'."
        )

    else:
        st.divider()

        if policy_result["eligible"]:
            st.success(
                "Eligible to receive an indicative policy "
                "illustration, subject to underwriting, "
                "policy terms, and appropriate review."
            )
        else:
            st.error(
                "The application cannot produce an "
                "illustration because required information "
                "is incomplete or invalid."
            )

        st.subheader("Illustrative policy price")

        price_column_1, price_column_2, price_column_3 = (
            st.columns(3)
        )

        with price_column_1:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Expected treatment cost
                    </div>
                    <div class="result-value">
                        £{policy_result["predicted_treatment_cost"]:,.2f}
                    </div>
                    <div class="result-note">
                        Model estimate for one treatment
                        exposure.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with price_column_2:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Indicative annual policy price
                    </div>
                    <div class="result-value">
                        £{policy_result["annual_policy_price"]:,.2f}
                    </div>
                    <div class="result-note">
                        Expected insurer cost plus the selected
                        pricing loadings.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with price_column_3:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Monthly equivalent
                    </div>
                    <div class="result-value">
                        £{policy_result["monthly_policy_price"]:,.2f}
                    </div>
                    <div class="result-note">
                        Annual illustration divided by
                        twelve months.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.info(
            "Typical model range for one expected treatment: "
            f"£{policy_result['lower_expected_cost']:,.2f} "
            f"to £{policy_result['upper_expected_cost']:,.2f}. "
            "This is based on historical prediction error."
        )

        st.subheader("How the annual price was built")

        breakdown = pd.DataFrame(
            {
                "Pricing component": [
                    (
                        "Expected insurer-funded "
                        "treatment cost"
                    ),
                    (
                        "Expected treatments "
                        "per year"
                    ),
                    (
                        "Annual expected claim cost"
                    ),
                    (
                        f"Administration "
                        f"({policy_result['administration_rate']}%)"
                    ),
                    (
                        f"Uncertainty and contingency "
                        f"({policy_result['uncertainty_rate']}%)"
                    ),
                    (
                        f"Illustrative margin "
                        f"({policy_result['margin_rate']}%)"
                    ),
                    "Indicative annual policy price",
                    "Monthly equivalent",
                ],
                "Value": [
                    (
                        f"£{policy_result['expected_insurer_cost_per_treatment']:,.2f}"
                    ),
                    (
                        f"{policy_result['claims_per_year']:.1f}"
                    ),
                    (
                        f"£{policy_result['annual_expected_claim_cost']:,.2f}"
                    ),
                    (
                        f"£{policy_result['administration_amount']:,.2f}"
                    ),
                    (
                        f"£{policy_result['uncertainty_amount']:,.2f}"
                    ),
                    (
                        f"£{policy_result['margin_amount']:,.2f}"
                    ),
                    (
                        f"£{policy_result['annual_policy_price']:,.2f}"
                    ),
                    (
                        f"£{policy_result['monthly_policy_price']:,.2f}"
                    ),
                ],
            }
        )

        st.dataframe(
            breakdown,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "The customer treatment contribution is deducted "
            "before estimating the insurer-funded treatment "
            "cost. The annual policy price is separate from "
            "the contribution paid when treatment occurs."
        )

        show_feature_chart(
            expense_importance,
            (
                "What influences expected treatment "
                "cost overall?"
            ),
        )


# ==========================================================
# TAB 3: DATASET INSIGHTS
# ==========================================================

with insights_tab:
    st.header(
        "Pricing reference from the dataset"
    )

    st.write(
        "These summaries show average treatment costs and "
        "customer contributions across groups in the supplied "
        "data. They provide context for the models but should "
        "not be interpreted as causal relationships."
    )

    overall = metrics["overall_statistics"]

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Records",
        f"{overall['record_count']:,}",
    )

    metric_2.metric(
        "Average treatment cost",
        (
            f"£{overall['average_treatment_cost']:,.2f}"
        ),
    )

    metric_3.metric(
        "Average customer contribution",
        (
            f"£{overall['average_customer_contribution']:,.2f}"
        ),
    )

    metric_4.metric(
        "Average contribution rate",
        (
            f"{overall['average_customer_contribution_rate'] * 100:.2f}%"
        ),
    )

    selected_category = st.selectbox(
        "View reference information by",
        sorted(
            reference_data["category"]
            .dropna()
            .unique()
        ),
    )

    filtered_reference = (
        reference_data[
            reference_data["category"]
            == selected_category
        ]
        .copy()
    )

    filtered_reference[
        "average_treatment_cost"
    ] = filtered_reference[
        "average_treatment_cost"
    ].round(2)

    filtered_reference[
        "median_treatment_cost"
    ] = filtered_reference[
        "median_treatment_cost"
    ].round(2)

    filtered_reference[
        "average_customer_contribution"
    ] = filtered_reference[
        "average_customer_contribution"
    ].round(2)

    filtered_reference[
        "average_contribution_rate"
    ] = filtered_reference[
        "average_contribution_rate"
    ].round(2)

    filtered_reference = (
        filtered_reference.rename(
            columns={
                "group_value": "Group",
                "record_count": "Records",
                "average_treatment_cost": (
                    "Average treatment cost"
                ),
                "median_treatment_cost": (
                    "Median treatment cost"
                ),
                "average_customer_contribution": (
                    "Average customer contribution"
                ),
                "average_contribution_rate": (
                    "Average contribution rate (%)"
                ),
            }
        )
    )

    st.dataframe(
        filtered_reference,
        use_container_width=True,
        hide_index=True,
    )

    chart_reference = (
        filtered_reference[
            [
                "Group",
                "Average treatment cost",
            ]
        ]
        .set_index("Group")
    )

    st.bar_chart(
        chart_reference,
        color="#2167d5",
    )


# ==========================================================
# METHODOLOGY AND DISCLAIMER
# ==========================================================

st.divider()

with st.expander(
    "Methodology, assumptions, and limitations"
):
    st.markdown(
        """
        **Dataset assumptions**

        - Each row is treated as one person and one treatment claim.
        - The `expenses` field is treated as the hospital bill.
        - The `premium` field is treated as the customer's contribution
          towards that treatment.
        - The dataset is assumed to contain no repeat customers.
        - One treatment per year is the default policy-pricing assumption.

        **Treatment contribution model**

        - Uses customer details and treatment cost.
        - Predicts the customer's treatment contribution.
        - The insurer contribution is the hospital bill minus the
          estimated customer contribution.

        **Policy illustration model**

        - Uses customer details to predict one expected treatment cost.
        - Estimates the insurer-funded portion of that treatment.
        - Multiplies the insurer-funded amount by the selected number
          of expected treatments.
        - Adds visible administration, uncertainty, and margin loadings.
        - Divides the annual illustration by twelve for a monthly
          equivalent.

        **Eligibility**

        - Eligibility only means that the application can produce an
          indicative illustration from complete input information.
        - It is not policy approval, underwriting approval, or an
          assessment of legal eligibility.
        - The application does not automatically reject a person based
          on BMI, gender, predicted treatment cost, or another customer
          characteristic.

        **Limitations**

        - The yearly price is a transparent scenario calculation, not
          an actuarially validated insurance premium.
        - The pricing loadings are demonstration assumptions.
        - The data does not contain policy limits, deductibles,
          commissions, taxes, claim frequency history, inflation,
          medical trends, or capital requirements.
        - Model outputs may reproduce limitations or biases in the
          supplied dataset.
        - Feature importance describes model behaviour and does not
          establish causation.
        """
    )

st.warning(
    "Proof of concept only. This application must not be "
    "used for real insurance pricing, underwriting, policy "
    "approval, claims settlement, medical decisions, or "
    "financial decisions."
)

st.caption(
    "Demonstration application built with Streamlit, "
    "scikit-learn, pandas, and XGBoost."
)