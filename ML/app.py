import streamlit as st
import pandas as pd
import joblib

# =====================================
# LOAD MODEL
# =====================================

model = joblib.load("premium_model.pkl")
error_margin = joblib.load("error_margin.pkl")

# =====================================
# PAGE SETTINGS
# =====================================

st.set_page_config(
    page_title="Insurance Premium Predictor",
    page_icon="💰",
    layout="wide"
)

# =====================================
# HEADER
# =====================================

st.title("💰 Insurance Premium Predictor")

st.markdown("""
Predict an insurance premium based on customer characteristics.

This model was trained using XGBoost with feature engineering and cross-validation.
""")

# =====================================
# INPUT SECTION
# =====================================

st.header("Customer Details")

col1, col2 = st.columns(2)

with col1:

    age = st.slider(
        "Age",
        18,
        80,
        35
    )

    bmi = st.slider(
        "BMI",
        15.0,
        55.0,
        27.5
    )

    children = st.selectbox(
        "Number of Children",
        [0, 1, 2, 3, 4, 5]
    )

with col2:

    gender = st.selectbox(
        "Gender",
        ["male", "female"]
    )

    discount_eligibility = st.selectbox(
        "Discount Eligibility",
        ["yes", "no"]
    )

    region = st.selectbox(
        "Region",
        [
            "northeast",
            "northwest",
            "southeast",
            "southwest"
        ]
    )

# =====================================
# BMI CATEGORY
# =====================================

if bmi < 18.5:
    bmi_category = "Underweight"
elif bmi < 25:
    bmi_category = "Normal Weight"
elif bmi < 30:
    bmi_category = "Overweight"
else:
    bmi_category = "Obese"

st.info(f"BMI Category: **{bmi_category}**")

# =====================================
# PREDICTION BUTTON
# =====================================

if st.button(
    "Predict Premium",
    use_container_width=True
):

    customer_data = pd.DataFrame([
        {
            "age": age,
            "bmi": bmi,
            "children": children,
            "gender": gender,
            "discount_eligibility": discount_eligibility,
            "region": region,
            "age_squared": age ** 2,
            "bmi_squared": bmi ** 2,
            "age_bmi": age * bmi
        }
    ])

    prediction = float(
        model.predict(customer_data)[0]
    )

    lower_bound = max(
        prediction - error_margin,
        0
    )

    upper_bound = prediction + error_margin

    # =====================================
    # RESULTS
    # =====================================

    st.header("Prediction Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Predicted Premium",
            f"£{prediction:,.2f}"
        )

    with col2:
        st.metric(
            "Lower Estimate",
            f"£{lower_bound:,.2f}"
        )

    with col3:
        st.metric(
            "Upper Estimate",
            f"£{upper_bound:,.2f}"
        )

    # =====================================
    # RISK PROFILE
    # =====================================

    st.subheader("Risk Assessment")

    risk_score = 0

    if age > 50:
        risk_score += 1

    if bmi >= 30:
        risk_score += 1

    if children >= 3:
        risk_score += 1

    if risk_score == 0:
        st.success("🟢 Low Risk Profile")

    elif risk_score == 1:
        st.warning("🟡 Moderate Risk Profile")

    else:
        st.error("🔴 High Risk Profile")

    # =====================================
    # EXPOSURE BAR
    # =====================================

    st.subheader("Premium Scale")

    scale = min(
        float(prediction / 1500),
        1.0
    )

    st.progress(scale)

    # =====================================
    # INPUT RECAP
    # =====================================

    st.subheader("Customer Summary")

    st.dataframe(
        customer_data,
        use_container_width=True
    )

# =====================================
# FOOTER
# =====================================

st.divider()

st.caption(
    "Built using XGBoost Regression, Feature Engineering, and Hyperparameter Tuning."
)