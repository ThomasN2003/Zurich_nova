### Requirements

- JDK 17
- Maven installed
- Postgres

### Running the app

1. ```mvn clean install```
2. ```mvn spring-boot:run```


# Life Insurance Pricing

Term life only. Applicant details in, premium out. Spring Boot, PostgreSQL, plain
HTML frontend served from the same app.

## 1. Pricing logic

The premium comes from a rate table plus a BMI loading.

```
base_rate  = rate per £1 of cover for (age, sex, smoker)   -- base_rates table
multiplier = BMI loading:  under 30      = 1.0
                           30 to 34.9    = 1.25
                           35 and over   = 1.6

annual  = sum_assured * base_rate * multiplier / (1 - loading) + fixed_fee
monthly = annual / 12
```

`loading` is 0.30 and covers expenses and profit. `fixed_fee` is £12 a year.

### Worked example

A 35 year old male non-smoker, BMI 26, wants £250,000 of cover over 25 years.

```
base_rate  = 0.00106590        from base_rates, age 35, M, non-smoker
multiplier = 1.0               BMI 26 is under 30

annual  = 250000 * 0.00106590 * 1.0 / (1 - 0.30) + 12.00
        = 266.475 / 0.70 + 12.00
        = 380.68 + 12.00
        = 392.68

monthly = 392.68 / 12 = 32.72
```

Two variations on the same applicant:

| Change | Rate or multiplier | Annual |
|---|---|---|
| Smoker | rate doubles to 0.00213180 | £773.36 |
| BMI 32 | multiplier becomes 1.25 | £487.85 |
| BMI 38 | multiplier becomes 1.6 | £621.09 |

### Where the rates come from

`base_rates` holds 212 rows covering ages 18 to 70 by sex and smoker status, seeded
from a Gompertz curve anchored so the worked example above reconciles. **These rates
are illustrative, not actuarial.** Swapping in a published mortality table is a change
to one seed script and nothing else, because the API only ever reads the table.

Every quote stores the `rate_version` it was priced on, so a premium can be reproduced
after the table changes.

### Declines

Decline if age is outside 18 to 70, term outside 5 to 40, BMI is 45 or above, or age
plus term would take cover past 75. A declined quote is still stored, with status
`DECLINED` and no premium, and the API returns 409.

Term is stored and sets the policy end date but does **not** affect the premium. A
5 year and a 40 year term price the same. Known simplification.

## 2. Functional requirements

| ID | Requirement | Where |
|---|---|---|
| FR-1 | Create a quote from age, sex, smoker, BMI, sum assured and term. Return annual and monthly premium. | `QuoteController`, `PricingServiceImpl` |
| FR-2 | Reject malformed input with 422 naming the field. Decline outside the underwriting limits with 409. | `QuoteRequest`, `GlobalExceptionHandler` |
| FR-3 | Store every quote, declines included, with its inputs and rate version so it can be reproduced. | `QuoteServiceImpl.create` |
| FR-4 | Turn a quote into a policy. A quote expires after 30 days and can only be accepted once. | `QuoteServiceImpl.accept` |
| FR-5 | Record a claim against an active policy, then settle it PAID or REJECTED. Paying takes the policy off risk. | `ClaimServiceImpl` |
| FR-6 | Report loss ratio: paid claims over premium written, grouped by smoker status and age band. | `ClaimRepository.lossRatio` |
| FR-7 | Browse the training data behind the rate calibration. | `TrainingDataController` |

Validation and declines are different things. A malformed payload (missing field, sex
that is not M or F) is a 422. An applicant the business will not cover is a 409, and
that quote is still recorded.

## 3. API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/quotes` | Create a quote |
| GET | `/quotes/{id}` | Fetch a quote |
| POST | `/quotes/{id}/accept` | Create a policy from the quote |
| POST | `/policies/{id}/claims` | Record a claim |
| PATCH | `/claims/{id}` | Set status to PAID or REJECTED |
| GET | `/reports/loss-ratio` | Loss ratio by smoker and age band |
| GET | `/training-data/{id}` | One training row |
| GET | `/training-data?limit=20` | Browse training rows, capped at 200 |
| GET | `/training-data/count` | How many training rows are loaded |

`POST /quotes` request:

```json
{ "age": 35, "sex": "M", "smoker": false, "bmi": 26.0, "sumAssured": 250000, "termYears": 25 }
```

Response, 201:

```json
{ "quoteId": "…", "status": "QUOTED", "annualPremium": 392.68, "monthlyPremium": 32.72, "expiresAt": "2026-09-24" }
```

Declined, 409:

```json
{ "timestamp": "…", "status": 409, "code": "DECLINED", "message": "BMI of 45 or above" }
```

## 4. Database schema

Five tables. `base_rates` drives pricing, `quotes` → `policies` → `claims` is the
business flow, `training_data` is read-only reference data.

```sql
CREATE TABLE base_rates (
  rate_version  VARCHAR(50)   NOT NULL,
  age           SMALLINT      NOT NULL,
  sex           CHAR(1)       NOT NULL,
  smoker        BOOLEAN       NOT NULL,
  rate          NUMERIC(10,8) NOT NULL,   -- per £1 of cover per year
  CONSTRAINT pk_base_rates      PRIMARY KEY (rate_version, age, sex, smoker),
  CONSTRAINT chk_base_rates_sex CHECK (sex IN ('M','F'))
);

CREATE TABLE quotes (
  id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  age              SMALLINT      NOT NULL,
  sex              CHAR(1)       NOT NULL,
  smoker           BOOLEAN       NOT NULL,
  bmi              NUMERIC(5,2)  NOT NULL,
  sum_assured      NUMERIC(12,2) NOT NULL,
  term_years       SMALLINT      NOT NULL,
  rate_version     VARCHAR(50)   NOT NULL,
  annual_premium   NUMERIC(10,2),          -- null when DECLINED
  monthly_premium  NUMERIC(10,2),
  status           VARCHAR(20)   NOT NULL,
  expires_at       DATE          NOT NULL,
  created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT chk_quotes_sex    CHECK (sex IN ('M','F')),
  CONSTRAINT chk_quotes_status CHECK (status IN ('QUOTED','DECLINED','ACCEPTED','EXPIRED'))
);

CREATE TABLE policies (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  quote_id        UUID          NOT NULL UNIQUE REFERENCES quotes(id),
  policy_number   VARCHAR(50)   NOT NULL UNIQUE,
  start_date      DATE          NOT NULL,
  end_date        DATE          NOT NULL,
  annual_premium  NUMERIC(10,2) NOT NULL,
  status          VARCHAR(20)   NOT NULL,
  CONSTRAINT chk_policies_status CHECK (status IN ('ACTIVE','CLAIMED','EXPIRED','CANCELLED'))
);

CREATE TABLE claims (
  id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id   UUID          NOT NULL REFERENCES policies(id),
  event_date  DATE          NOT NULL,
  amount      NUMERIC(12,2) NOT NULL,
  status      VARCHAR(20)   NOT NULL,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT chk_claims_status CHECK (status IN ('OPEN','PAID','REJECTED'))
);

-- medical_insurance_processed.csv, all 17 columns, 1337 rows
CREATE TABLE training_data (
  id                        BIGSERIAL     PRIMARY KEY,
  age                       SMALLINT,
  gender                    VARCHAR(10),
  bmi                       NUMERIC(5,2),
  children                  SMALLINT,
  discount_eligibility      VARCHAR(3),
  region                    VARCHAR(20),
  expenses                  NUMERIC(12,2),   -- claims cost
  premium                   NUMERIC(12,4),   -- synthetic: expenses / 25, 50 or 100
  discount_eligibility_flag SMALLINT,
  gender_flag               SMALLINT,
  bmi_category              VARCHAR(20),
  age_group                 VARCHAR(20),
  large_family              SMALLINT,
  age_bmi_interaction       NUMERIC(10,2),
  expense_per_child         NUMERIC(12,2),
  premium_expense_ratio     NUMERIC(10,4),
  high_cost_customer        SMALLINT
);
```

Full DDL with indexes is in `src/main/resources/postgres_schema.sql`.

### Status flows

```
quote:   QUOTED ──accept──► ACCEPTED
         QUOTED ──expiry──► EXPIRED
         DECLINED (terminal)

policy:  ACTIVE ──claim paid──► CLAIMED

claim:   OPEN ──► PAID
         OPEN ──► REJECTED
```

## 5. Running it

```bash
mvn clean test
mvn spring-boot:run
```

Then `http://localhost:8080` for the quote-to-claim page, or:

```bash
curl -X POST http://localhost:8080/quotes -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"M","smoker":false,"bmi":26.0,"sumAssured":250000,"termYears":25}'
```

## 6. Tests

```bash
mvn test
```

Unit tests with repositories mocked, so no database is needed.

- `PricingServiceImplTest` — the formula against the worked example, BMI band
  boundaries, the underwriting limits.
- `QuoteServiceImplTest` — persistence, declines still being stored, accept, expiry,
  double accept.
- `ClaimServiceImplTest` — registration and status transitions.

Not covered: the `/reports/loss-ratio` native query, which needs a live database.

## 7. Known limitations

- Rates are illustrative, not from a published mortality table.
- Term does not affect the premium.
- `children` and `region` sit in the training data but play no part in pricing.
- No authentication.