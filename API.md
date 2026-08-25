# API Reference

Base URL `http://localhost:8080`. JSON in, JSON out. No authentication.

Money is `NUMERIC(10,2)`. Ids are UUIDs. Dates are ISO `YYYY-MM-DD`.

---

## Error format

Every error comes back in the same shape, produced by `GlobalExceptionHandler`.

```json
{
  "timestamp": "2026-08-25T13:42:11.482Z",
  "status": 409,
  "code": "DECLINED",
  "message": "BMI of 45 or above",
  "fields": null
}
```

| Status | Code | When |
|---|---|---|
| 404 | `NOT_FOUND` | Unknown quote, policy, claim or training row |
| 409 | `DECLINED` | Applicant falls outside the underwriting limits |
| 409 | `INVALID_STATE` | Right record, wrong state (expired quote, settled claim) |
| 422 | `VALIDATION_ERROR` | Malformed payload; `fields` names what failed |
| 500 | `INTERNAL_ERROR` | Anything unhandled |

A decline is not a validation failure. A 422 means the request was malformed. A 409
`DECLINED` means the request was fine and the business will not cover this applicant,
and the quote is still recorded.

---

## 1. Create a quote

`POST /quotes`

| Field | Type | Rules |
|---|---|---|
| `age` | integer | required, positive |
| `sex` | string | required, `M` or `F` |
| `smoker` | boolean | required |
| `bmi` | number | required, positive |
| `sumAssured` | number | required, 10,000 to 2,000,000 |
| `termYears` | integer | required, positive |

```bash
curl -i -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"M","smoker":false,"bmi":26.0,"sumAssured":250000,"termYears":25}'
```

**201 Created**

```json
{
  "quoteId": "4ccc9a37-e4d8-4815-a10f-096e0a330699",
  "status": "QUOTED",
  "annualPremium": 392.68,
  "monthlyPremium": 32.72,
  "expiresAt": "2026-09-24"
}
```

### More priced examples

Smoker, same applicant. The rate doubles.

```bash
curl -s -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"M","smoker":true,"bmi":26.0,"sumAssured":250000,"termYears":25}'
```

```json
{ "status": "QUOTED", "annualPremium": 773.36, "monthlyPremium": 64.45, "…": "…" }
```

Raised BMI, 32.0, which lands in the 1.25 band.

```bash
curl -s -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"M","smoker":false,"bmi":32.0,"sumAssured":250000,"termYears":25}'
```

```json
{ "status": "QUOTED", "annualPremium": 487.85, "monthlyPremium": 40.65, "…": "…" }
```

Female, same applicant. The rate carries a 0.85 factor.

```bash
curl -s -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"F","smoker":false,"bmi":26.0,"sumAssured":250000,"termYears":25}'
```

```json
{ "status": "QUOTED", "annualPremium": 335.58, "monthlyPremium": 27.97, "…": "…" }
```

### Declined, 409

Age 62 with a 25 year term expires at 87, past the limit of 75.

```bash
curl -i -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":62,"sex":"M","smoker":false,"bmi":28.0,"sumAssured":250000,"termYears":25}'
```

```json
{ "status": 409, "code": "DECLINED", "message": "Cover would run past age 75" }
```

Other decline messages:

| Input | Message |
|---|---|
| `age: 17` or `age: 71` | `Age must be between 18 and 70` |
| `termYears: 4` or `41` | `Term must be between 5 and 40 years` |
| `bmi: 45.0` or above | `BMI of 45 or above` |

The quote is saved either way:

```bash
docker exec -it pg psql -U life -d lifepricing \
  -c "SELECT age, status, annual_premium FROM quotes WHERE status = 'DECLINED';"
```

```
 age |  status  | annual_premium
-----+----------+----------------
  62 | DECLINED |
```

### Malformed, 422

```bash
curl -i -X POST http://localhost:8080/quotes \
  -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"X","smoker":false,"bmi":26.0,"sumAssured":500,"termYears":25}'
```

```json
{
  "status": 422,
  "code": "VALIDATION_ERROR",
  "message": "Request failed validation",
  "fields": {
    "sex": "must be M or F",
    "sumAssured": "must be greater than or equal to 10000"
  }
}
```

---

## 2. Fetch a quote

`GET /quotes/{id}`

```bash
curl -i http://localhost:8080/quotes/4ccc9a37-e4d8-4815-a10f-096e0a330699
```

**200 OK** — identical to the create response, so a premium can always be re-read.

```json
{
  "quoteId": "4ccc9a37-e4d8-4815-a10f-096e0a330699",
  "status": "QUOTED",
  "annualPremium": 392.68,
  "monthlyPremium": 32.72,
  "expiresAt": "2026-09-24"
}
```

**404** for an unknown id:

```json
{ "status": 404, "code": "NOT_FOUND", "message": "Quote <id> not found" }
```

---

## 3. Accept a quote

`POST /quotes/{id}/accept`

No body. Creates a policy and flips the quote to `ACCEPTED`.

```bash
curl -i -X POST http://localhost:8080/quotes/4ccc9a37-e4d8-4815-a10f-096e0a330699/accept
```

**201 Created**

```json
{
  "id": "9f2b1c44-7a0e-4d31-b8c5-1e3f5a7d9b02",
  "quoteId": "4ccc9a37-e4d8-4815-a10f-096e0a330699",
  "policyNumber": "POL-1756129331847",
  "startDate": "2026-08-25",
  "endDate": "2051-08-25",
  "annualPremium": 392.68,
  "status": "ACTIVE"
}
```

`endDate` is `startDate` plus `termYears`.

**409** on a second attempt, an expired quote, or a declined one:

```json
{ "status": 409, "code": "INVALID_STATE", "message": "Quote is ACCEPTED" }
```

```json
{ "status": 409, "code": "INVALID_STATE", "message": "Quote has expired" }
```

---

## 4. Register a claim

`POST /policies/{policyId}/claims`

| Field | Type | Rules |
|---|---|---|
| `eventDate` | date | required, today or earlier |
| `amount` | number | required, at least 0.01 |

```bash
curl -i -X POST http://localhost:8080/policies/9f2b1c44-7a0e-4d31-b8c5-1e3f5a7d9b02/claims \
  -H 'Content-Type: application/json' \
  -d '{"eventDate":"2026-08-01","amount":250000}'
```

**201 Created**

```json
{
  "id": "c81d4e2f-3a65-4b90-9c17-5d8e2f6a1b34",
  "policyId": "9f2b1c44-7a0e-4d31-b8c5-1e3f5a7d9b02",
  "eventDate": "2026-08-01",
  "amount": 250000.00,
  "status": "OPEN",
  "createdAt": "2026-08-25T13:45:02.113Z"
}
```

**404** if the policy does not exist. **409** if it is not `ACTIVE`:

```json
{ "status": 409, "code": "INVALID_STATE", "message": "Policy is CLAIMED" }
```

**422** for a future `eventDate`:

```json
{ "status": 422, "code": "VALIDATION_ERROR", "fields": { "eventDate": "must be a date in the past or in the present" } }
```

---

## 5. Settle a claim

`PATCH /claims/{id}`

Only `PAID` or `REJECTED`. Paying also flips the policy to `CLAIMED`; rejecting leaves
it `ACTIVE`.

```bash
curl -i -X PATCH http://localhost:8080/claims/c81d4e2f-3a65-4b90-9c17-5d8e2f6a1b34 \
  -H 'Content-Type: application/json' \
  -d '{"status":"PAID"}'
```

**200 OK**

```json
{
  "id": "c81d4e2f-3a65-4b90-9c17-5d8e2f6a1b34",
  "policyId": "9f2b1c44-7a0e-4d31-b8c5-1e3f5a7d9b02",
  "eventDate": "2026-08-01",
  "amount": 250000.00,
  "status": "PAID",
  "createdAt": "2026-08-25T13:45:02.113Z"
}
```

**409** on an unknown status, a lowercase one, or a claim already settled:

```json
{ "status": 409, "code": "INVALID_STATE", "message": "Status must be PAID or REJECTED" }
```

```json
{ "status": 409, "code": "INVALID_STATE", "message": "Claim is already PAID" }
```

---

## 6. Loss ratio report

`GET /reports/loss-ratio`

Paid claims over premium written, grouped by smoker status and age band.

```bash
curl -s http://localhost:8080/reports/loss-ratio
```

**200 OK**

```json
[
  {
    "segment": "NON_SMOKER",
    "ageBand": "30-44",
    "premium": 392.68,
    "paidClaims": 250000.00,
    "lossRatio": 636.6018
  }
]
```

`lossRatio` is a ratio, not a percentage. Empty array when no policies exist.

Age bands are `18-29`, `30-44`, `45-59`, `60+`.

---

## 7. Training data

Read-only access to the 1337 rows behind the rate calibration.

```bash
curl -s http://localhost:8080/training-data/count
```

```json
{ "count": 1337 }
```

```bash
curl -s http://localhost:8080/training-data/1
```

```json
{
  "id": 1,
  "age": 19,
  "gender": "female",
  "bmi": 27.90,
  "children": 0,
  "discountEligibility": "yes",
  "region": "southwest",
  "expenses": 16884.92,
  "premium": 168.8492,
  "discountEligibilityFlag": 1,
  "genderFlag": 0,
  "bmiCategory": "overweight",
  "ageGroup": "young",
  "largeFamily": 0,
  "ageBmiInteraction": 530.10,
  "expensePerChild": 16884.92,
  "premiumExpenseRatio": 0.0100,
  "highCostCustomer": 1
}
```

```bash
curl -s "http://localhost:8080/training-data?limit=3"
```

Returns an array. `limit` defaults to 20 and is capped at 200.

---

## Full lifecycle in one go

Quote, accept, claim, settle, report. Requires `jq`.

```bash
BASE=http://localhost:8080

QUOTE=$(curl -s -X POST $BASE/quotes -H 'Content-Type: application/json' \
  -d '{"age":35,"sex":"M","smoker":false,"bmi":26.0,"sumAssured":250000,"termYears":25}')
QUOTE_ID=$(echo $QUOTE | jq -r .quoteId)
echo "quote  $QUOTE_ID  $(echo $QUOTE | jq -r .annualPremium)"

POLICY=$(curl -s -X POST $BASE/quotes/$QUOTE_ID/accept)
POLICY_ID=$(echo $POLICY | jq -r .id)
echo "policy $POLICY_ID  $(echo $POLICY | jq -r .policyNumber)"

CLAIM=$(curl -s -X POST $BASE/policies/$POLICY_ID/claims \
  -H 'Content-Type: application/json' \
  -d "{\"eventDate\":\"$(date +%F)\",\"amount\":250000}")
CLAIM_ID=$(echo $CLAIM | jq -r .id)
echo "claim  $CLAIM_ID  $(echo $CLAIM | jq -r .status)"

curl -s -X PATCH $BASE/claims/$CLAIM_ID -H 'Content-Type: application/json' \
  -d '{"status":"PAID"}' | jq -r '"settled \(.status)"'

curl -s $BASE/reports/loss-ratio | jq
```

Expected output:

```
quote  4ccc9a37-…  392.68
policy 9f2b1c44-…  POL-1756129331847
claim  c81d4e2f-…  OPEN
settled PAID
[ { "segment": "NON_SMOKER", "ageBand": "30-44", … } ]
```

Then check it all persisted:

```bash
docker exec -it pg psql -U life -d lifepricing \
  -c 'SELECT status, annual_premium FROM quotes ORDER BY created_at DESC LIMIT 3;' \
  -c 'SELECT policy_number, status FROM policies;' \
  -c 'SELECT amount, status FROM claims;'
```

---

## Notes

- Ids in the examples are illustrative. Yours will differ.
- `POL-` numbers are `System.currentTimeMillis()`, so they are unique per run but not
  meaningful.
- Quotes expire 30 days after creation. Nothing sweeps expired quotes on a schedule;
  the status only changes when you try to accept one.
- Premiums assume the seeded `base_rates` for version `2026-08`. Reseed with different
  rates and every figure above changes.
