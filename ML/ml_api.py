from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ==========================================================
# FILE LOCATIONS
# ==========================================================

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


# ==========================================================
# GLOBAL MODEL CONTAINER
# ==========================================================

models = {}


# ==========================================================
# API DATA CONTRACTS
# ==========================================================

class CustomerDetails(BaseModel):
    age: int = Field(
        ge=18,
        le=100,
    )

    bmi: float = Field(
        ge=10.0,
        le=70.0,
    )

    children: int = Field(
        ge=0,
        le=20,
    )

    gender: Literal[
        "male",
        "female",
    ]

    discount_eligibility: Literal[
        "yes",
        "no",
    ]

    region: Literal[
        "northeast",
        "northwest",
        "southeast",
        "southwest",
    ]


class TreatmentContributionRequest(
    CustomerDetails
):
    treatment_cost: float = Field(
        gt=0,
        le=1_000_000,
    )


class PolicyIllustrationRequest(
    CustomerDetails
):
    expected_treatments_per_year: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
    )

    administration_rate: float = Field(
        default=10.0,
        ge=0,
        le=30,
    )

    uncertainty_rate: float = Field(
        default=10.0,
        ge=0,
        le=30,
    )

    margin_rate: float = Field(
        default=5.0,
        ge=0,
        le=20,
    )


# ==========================================================
# HELPERS
# ==========================================================

def build_customer_record(
    request: CustomerDetails,
    expenses=None,
):
    record = {
        "age": request.age,
        "bmi": request.bmi,
        "children": request.children,
        "gender": request.gender,
        "discount_eligibility": (
            request.discount_eligibility
        ),
        "region": request.region,
        "age_squared": request.age ** 2,
        "bmi_squared": request.bmi ** 2,
        "age_bmi": request.age * request.bmi,
    }

    if expenses is not None:
        record["expenses"] = float(expenses)

    return pd.DataFrame([record])


def predict_customer_contribution(
    customer_record,
    treatment_cost,
):
    raw_prediction = models[
        "contribution"
    ].predict(customer_record)[0]

    contribution = max(
        float(raw_prediction),
        0.0,
    )

    contribution = min(
        contribution,
        float(treatment_cost),
    )

    return contribution


# ==========================================================
# STARTUP
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    required_files = [
        CONTRIBUTION_MODEL_PATH,
        EXPENSE_MODEL_PATH,
        MODEL_METRICS_PATH,
    ]

    missing_files = [
        path.name
        for path in required_files
        if not path.exists()
    ]

    if missing_files:
        raise RuntimeError(
            "Missing trained model files: "
            + ", ".join(missing_files)
            + ". Run python training.py first."
        )

    models["contribution"] = joblib.load(
        CONTRIBUTION_MODEL_PATH
    )

    models["expense"] = joblib.load(
        EXPENSE_MODEL_PATH
    )

    models["metrics"] = joblib.load(
        MODEL_METRICS_PATH
    )

    print("ML models loaded successfully.")

    yield

    models.clear()


# ==========================================================
# APPLICATION
# ==========================================================

app = FastAPI(
    title="Insurance ML API",
    description=(
        "Proof-of-concept API for treatment "
        "contribution and policy illustrations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# ENDPOINTS
# ==========================================================

@app.get("/")
def root():
    return {
        "service": "Insurance ML API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "contribution_model_loaded": (
            "contribution" in models
        ),
        "expense_model_loaded": (
            "expense" in models
        ),
    }


@app.get("/model-metrics")
def model_metrics():
    return models["metrics"]


@app.post("/predict/treatment-contribution")
def treatment_contribution(
    request: TreatmentContributionRequest,
):
    try:
        customer_record = build_customer_record(
            request,
            expenses=request.treatment_cost,
        )

        customer_contribution = (
            predict_customer_contribution(
                customer_record,
                request.treatment_cost,
            )
        )

        insurer_contribution = max(
            request.treatment_cost
            - customer_contribution,
            0,
        )

        contribution_percentage = (
            customer_contribution
            / request.treatment_cost
            * 100
        )

        typical_error = float(
            models["metrics"][
                "contribution_model"
            ]["typical_error"]
        )

        lower_estimate = max(
            customer_contribution
            - typical_error,
            0,
        )

        upper_estimate = min(
            customer_contribution
            + typical_error,
            request.treatment_cost,
        )

        return {
            "hospital_treatment_cost": round(
                request.treatment_cost,
                2,
            ),
            "customer_contribution": round(
                customer_contribution,
                2,
            ),
            "insurer_contribution": round(
                insurer_contribution,
                2,
            ),
            "customer_contribution_percentage": round(
                contribution_percentage,
                2,
            ),
            "typical_lower_estimate": round(
                lower_estimate,
                2,
            ),
            "typical_upper_estimate": round(
                upper_estimate,
                2,
            ),
            "currency": "GBP",
            "proof_of_concept": True,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Treatment contribution prediction "
                f"failed: {error}"
            ),
        ) from error


@app.post("/predict/policy-illustration")
def policy_illustration(
    request: PolicyIllustrationRequest,
):
    try:
        customer_record = build_customer_record(
            request
        )

        predicted_treatment_cost = max(
            float(
                models["expense"].predict(
                    customer_record
                )[0]
            ),
            0.0,
        )

        contribution_record = (
            customer_record.copy()
        )

        contribution_record["expenses"] = (
            predicted_treatment_cost
        )

        estimated_customer_contribution = (
            predict_customer_contribution(
                contribution_record,
                predicted_treatment_cost,
            )
        )

        insurer_cost_per_treatment = max(
            predicted_treatment_cost
            - estimated_customer_contribution,
            0,
        )

        annual_expected_claim_cost = (
            insurer_cost_per_treatment
            * request.expected_treatments_per_year
        )

        administration_amount = (
            annual_expected_claim_cost
            * request.administration_rate
            / 100
        )

        uncertainty_amount = (
            annual_expected_claim_cost
            * request.uncertainty_rate
            / 100
        )

        margin_amount = (
            annual_expected_claim_cost
            * request.margin_rate
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

        typical_expense_error = float(
            models["metrics"][
                "expense_model"
            ]["typical_error"]
        )

        lower_treatment_estimate = max(
            predicted_treatment_cost
            - typical_expense_error,
            0,
        )

        upper_treatment_estimate = (
            predicted_treatment_cost
            + typical_expense_error
        )

        return {
            "quote_eligible": True,
            "eligibility_message": (
                "Eligible to receive an indicative "
                "illustration, subject to underwriting "
                "and policy terms."
            ),
            "expected_treatment_cost": round(
                predicted_treatment_cost,
                2,
            ),
            "typical_treatment_cost_range": {
                "lower": round(
                    lower_treatment_estimate,
                    2,
                ),
                "upper": round(
                    upper_treatment_estimate,
                    2,
                ),
            },
            "estimated_customer_contribution": round(
                estimated_customer_contribution,
                2,
            ),
            "insurer_cost_per_treatment": round(
                insurer_cost_per_treatment,
                2,
            ),
            "expected_treatments_per_year": (
                request.expected_treatments_per_year
            ),
            "annual_expected_claim_cost": round(
                annual_expected_claim_cost,
                2,
            ),
            "pricing_breakdown": {
                "administration_rate": (
                    request.administration_rate
                ),
                "administration_amount": round(
                    administration_amount,
                    2,
                ),
                "uncertainty_rate": (
                    request.uncertainty_rate
                ),
                "uncertainty_amount": round(
                    uncertainty_amount,
                    2,
                ),
                "margin_rate": (
                    request.margin_rate
                ),
                "margin_amount": round(
                    margin_amount,
                    2,
                ),
            },
            "indicative_annual_policy_price": round(
                annual_policy_price,
                2,
            ),
            "indicative_monthly_policy_price": round(
                monthly_policy_price,
                2,
            ),
            "currency": "GBP",
            "proof_of_concept": True,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Policy illustration failed: "
                f"{error}"
            ),
        ) from error