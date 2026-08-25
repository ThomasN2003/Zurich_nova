# Life Insurance Pricing, simple version

Term life only. Applicant details in, premium out. REST + JSON, PostgreSQL.

## 1. Dataset

Kaggle "Health Insurance Dataset" (imtkaggleteam): https://www.kaggle.com/datasets/imtkaggleteam/health-insurance-dataset

One CSV with age, gender, bmi, children, region, `expenses` (claims cost) and `premium`. Check the column headers after download.

Use it two ways:
1. Fit `expenses ~ age + gender + bmi` to get the BMI multipliers below.
2. Loss ratio = sum(expenses) / sum(premium). Use that to set the loading.

## 2. Pricing formula

```
base_rate = rate per £1 of cover for (age, sex, smoker)   -- from base_rates table
multiplier = BMI multiplier (e.g. under 30 = 1.0, 30 to 34.9 = 1.25, 35+ = 1.6)
annual_premium = sum_assured * base_rate * multiplier / (1 - loading) + fixed_fee
monthly_premium = annual_premium / 12
```

Loading covers expenses and profit (e.g. 0.30). Fixed fee e.g. £12.
Decline if age is outside 18 to 70, term outside 5 to 40, or BMI 45 or above.

## 3. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | Create a quote from age, sex, smoker, BMI, sum assured and term. Return annual and monthly premium. |
| FR-2 | Reject invalid input with a 422 and the field that failed. Decline outside the limits above. |
| FR-3 | Store every quote with its inputs and the rate version used, so it can be reproduced. |
| FR-4 | Turn a quote into a policy. Quote expires after 30 days. |
| FR-5 | Record a claim against a policy with an amount and status (OPEN, PAID, REJECTED). |
| FR-6 | Report loss ratio: paid claims / annual premium, grouped by smoker status and age band. |

## 4. API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/quotes` | Create a quote |
| GET | `/quotes/{id}` | Fetch a quote |
| POST | `/quotes/{id}/accept` | Create a policy from the quote |
| POST | `/policies/{id}/claims` | Record a claim |
| PATCH | `/claims/{id}` | Set status to PAID or REJECTED |
| GET | `/reports/loss-ratio` | Loss ratio by smoker and age band |

Example `POST /quotes`:

```json
{ "age": 35, "sex": "M", "smoker": false, "bmi": 26.0, "sumAssured": 250000, "termYears": 25 }
```

Response:

```json
{ "quoteId": "…", "status": "QUOTED", "annualPremium": 392.68, "monthlyPremium": 32.72, "expiresAt": "2026-09-24" }
```

## 5. Database schema

```sql
CREATE TABLE base_rates (
  rate_version  TEXT NOT NULL,           -- e.g. '2026-08'
  age           SMALLINT NOT NULL,
  sex           CHAR(1) NOT NULL CHECK (sex IN ('M','F')),
  smoker        BOOLEAN NOT NULL,
  rate          NUMERIC(10,8) NOT NULL,  -- per £1 of cover per year
  PRIMARY KEY (rate_version, age, sex, smoker)
);

CREATE TABLE quotes (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  age              SMALLINT NOT NULL,
  sex              CHAR(1) NOT NULL CHECK (sex IN ('M','F')),
  smoker           BOOLEAN NOT NULL,
  bmi              NUMERIC(5,2) NOT NULL,
  sum_assured      NUMERIC(12,2) NOT NULL,
  term_years       SMALLINT NOT NULL,
  rate_version     TEXT NOT NULL,
  annual_premium   NUMERIC(10,2),
  monthly_premium  NUMERIC(10,2),
  status           TEXT NOT NULL CHECK (status IN ('QUOTED','DECLINED','ACCEPTED','EXPIRED')),
  expires_at       DATE NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE policies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quote_id        UUID NOT NULL UNIQUE REFERENCES quotes(id),
  policy_number   TEXT NOT NULL UNIQUE,
  start_date      DATE NOT NULL,
  end_date        DATE NOT NULL,
  annual_premium  NUMERIC(10,2) NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('ACTIVE','CLAIMED','EXPIRED','CANCELLED'))
);

CREATE TABLE claims (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id   UUID NOT NULL REFERENCES policies(id),
  event_date  DATE NOT NULL,
  amount      NUMERIC(12,2) NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('OPEN','PAID','REJECTED')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE training_data (             -- the Kaggle CSV, loaded as is
  id        BIGSERIAL PRIMARY KEY,
  age       SMALLINT,
  gender    TEXT,
  bmi       NUMERIC(5,2),
  children  SMALLINT,
  region    TEXT,
  expenses  NUMERIC(12,2),
  premium   NUMERIC(12,2)
);
```

## 6. Build order

1. Run the schema, load the CSV into `training_data`, seed `base_rates` for one rate version.
2. Build `POST /quotes` with the formula in section 2.
3. Add accept, claims and the loss ratio report.
