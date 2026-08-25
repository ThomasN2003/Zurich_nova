import pandas as pd
import streamlit as st
import joblib

model = joblib.load("premium_model.pkl")

st.title("Insurance Premium Predictor")

age = st.number_input("Age", 18, 100, 30)
bmi = st.number_input("BMI", 10.0, 60.0, 25.0)
children = st.number_input("Children", 0, 10, 0)

gender = st.selectbox(
    "Gender",
    ["male", "female"]
)

discount = st.selectbox(
    "Discount Eligibility",
    ["yes", "no"]
)

region = st.selectbox(
    "Region",
    [
        "northwest",
        "northeast",
        "southwest",
        "southeast"
    ]
)

if st.button("Predict Premium"):
    row = pd.DataFrame([{
        "age": age,
        "gender": gender,
        "bmi": bmi,
        "children": children,
        "discount_eligibility": discount,
        "region": region
    }])

    pred = model.predict(row)[0]

    st.success(
        f"Predicted Premium = £{pred:.2f}"
    )