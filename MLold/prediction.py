import pandas as pd
import joblib

model = joblib.load("premium_model.pkl")

customer = pd.DataFrame([
    {
        "age": 35,
        "gender": "male",
        "bmi": 28.4,
        "children": 2,
        "discount_eligibility": "yes",
        "region": "northwest"
    }
])

prediction = model.predict(customer)

print(
    f"Predicted Premium: £{prediction.2f}"
)