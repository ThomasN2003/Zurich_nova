import streamlit as st
import pandas as pd
import joblib

# ===================================
# LOAD MODEL
# ===================================

model = joblib.load("premium_model.pkl")
error_margin = joblib.load("error_margin.pkl")

# ===================================
# PAGE CONFIG
# ===================================

st.set_page_config(
    page_title="Insurance Premium Predictor",
    page_icon="💰",
    layout="wide"
)

# ===================================
# STYLING
# ===================================

st.markdown("""
<style>

.stApp {
    background-color: #f8fafc;
}

.main-title {
    font-size: 42px;
    font-weight: bold;
    color: #0f172a;
}

.sub-title {
    font-size: 20px;
    color: #475569;
}

.result-box {
    background-color: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
}

</style>
""", unsafe_allow_html=True)

# ===================================
# HEADER
# ===================================

st.markdown(
    "<div class='main-title'>💰 Insurance Premium Predictor</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='sub-title'>Predict customer insurance premiums using a machine learning model</div>",
    unsafe_allow_html=True
)

st.write("")
st.write("")

# ===================================
# SIDEBAR INPUTS
# ===================================

st.sidebar.header("Customer Information")

age = st.sidebar.slider(
    "Age",
    min_value=18,
    max_value=80,
    value=35
)

bmi = st.sidebar.slider(
    "BMI",
    min_value=15.0,
    max_value=55.0,
    value=27.5
)

children = st.sidebar.slider(
    "Number of Children",
    min_value=0,
    max_value=5,
    value=0
)

gender = st.sidebar.selectbox(
    "Gender",
    ["male", "female"]
)

discount_eligibility = st.sidebar.selectbox(
    "Discount Eligibility",
    ["yes", "no"]
)

region = st.sidebar.selectbox(
    "Region",
    [
        "northeast",
        "northwest",
        "southeast",
        "southwest"
    ]
)

# ===================================
# BMI CATEGORY
# ===================================

if bmi < 18.5:
    bmi_category = "Underweight"
elif bmi < 25:
    bmi_category = "Normal Weight"
elif bmi < 30:
    bmi_category = "Overweight"
else:
    bmi_category = "Obese"

# ===================================
# CUSTOMER SUMMARY
# ===================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Age",
        age
    )

with col2:
    st.metric(
        "BMI Category",
        bmi_category
    )

with col3:
    st.metric(
        "Children",
        children
    )

st.divider()

# ===================================
# PREDICTION
# ===================================

if st.button(
    "🔮 Predict Premium",
    use_container_width=True
):

    customer_data = pd.DataFrame([{
        "age": age,
        "bmi": bmi,
        "children": children,
        "gender": gender,
        "discount_eligibility": discount_eligibility,
        "region": region,
        "age_squared": age ** 2,
        "bmi_squared": bmi ** 2,
        "age_bmi": age * bmi
    }])

    prediction = model.predict(customer_data)[0]

    lower_bound = max(
        prediction - error_margin,
        0
    )

    upper_bound = (
        prediction + error_margin
    )

    st.success("Prediction Complete ✅")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Predicted Premium")

        st.metric(
            label="Monthly Premium",
            value=f"£{prediction:,.2f}"
        )

    with col2:

        st.markdown("### Expected Range")

        st.metric(
            label="Confidence Range",
            value=f"£{lower_bound:,.2f} - £{upper_bound:,.2f}"
        )

    st.divider()

    # ===================================
    # RISK LEVEL
    # ===================================

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
        st.error("🔴 Higher Risk Profile")

    # ===================================
    # PREMIUM VISUAL
    # ===================================

    st.subheader("Premium Indicator")

    progress_value = min(
        prediction / 1000,
        1.0
    )

    st.progress(progress_value)

    st.caption(
        "Premium position relative to expected pricing range."
    )

    # ===================================
    # CUSTOMER DETAILS
    # ===================================

    st.subheader("Prediction Inputs")

    st.dataframe(
        customer_data,
        use_container_width=True
    )

# ===================================
# FOOTER
# ===================================

st.divider()

st.caption(
    "Machine Learning Model: XGBoost Regression with feature engineering and hyperparameter tuning."
)