-- ============================================================================
-- Life Insurance Pricing, PostgreSQL schema
-- Run this first, then seed_base_rates.sql, then load the CSV.
-- ============================================================================

DROP TABLE IF EXISTS claims        CASCADE;
DROP TABLE IF EXISTS policies      CASCADE;
DROP TABLE IF EXISTS quotes        CASCADE;
DROP TABLE IF EXISTS base_rates    CASCADE;
DROP TABLE IF EXISTS training_data CASCADE;

-- gen_random_uuid() is built in from PostgreSQL 13; pgcrypto covers older versions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- PRICING INPUTS
-- ============================================================================

CREATE TABLE base_rates (
                            rate_version  VARCHAR(50)   NOT NULL,
                            age           SMALLINT      NOT NULL,
                            sex           CHAR(1)       NOT NULL,
                            smoker        BOOLEAN       NOT NULL,
                            rate          NUMERIC(10,8) NOT NULL,
                            CONSTRAINT pk_base_rates      PRIMARY KEY (rate_version, age, sex, smoker),
                            CONSTRAINT chk_base_rates_sex CHECK (sex IN ('M','F'))
);

-- ============================================================================
-- BUSINESS TABLES
-- ============================================================================

CREATE TABLE quotes (
                        id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
                        age              SMALLINT      NOT NULL,
                        sex              CHAR(1)       NOT NULL,
                        smoker           BOOLEAN       NOT NULL,
                        bmi              NUMERIC(5,2)  NOT NULL,
                        sum_assured      NUMERIC(12,2) NOT NULL,
                        term_years       SMALLINT      NOT NULL,
                        rate_version     VARCHAR(50)   NOT NULL,
                        annual_premium   NUMERIC(10,2),          -- null on a declined quote
                        monthly_premium  NUMERIC(10,2),
                        status           VARCHAR(20)   NOT NULL,
                        expires_at       DATE          NOT NULL,
                        created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
                        CONSTRAINT chk_quotes_sex    CHECK (sex IN ('M','F')),
                        CONSTRAINT chk_quotes_status CHECK (status IN ('QUOTED','DECLINED','ACCEPTED','EXPIRED'))
);

CREATE TABLE policies (
                          id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
                          quote_id        UUID          NOT NULL UNIQUE,
                          policy_number   VARCHAR(50)   NOT NULL UNIQUE,
                          start_date      DATE          NOT NULL,
                          end_date        DATE          NOT NULL,
                          annual_premium  NUMERIC(10,2) NOT NULL,
                          status          VARCHAR(20)   NOT NULL,
                          CONSTRAINT fk_policies_quote   FOREIGN KEY (quote_id) REFERENCES quotes(id),
                          CONSTRAINT chk_policies_status CHECK (status IN ('ACTIVE','CLAIMED','EXPIRED','CANCELLED'))
);

CREATE TABLE claims (
                        id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
                        policy_id   UUID          NOT NULL,
                        event_date  DATE          NOT NULL,
                        amount      NUMERIC(12,2) NOT NULL,
                        status      VARCHAR(20)   NOT NULL,
                        created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
                        CONSTRAINT fk_claims_policy  FOREIGN KEY (policy_id) REFERENCES policies(id),
                        CONSTRAINT chk_claims_status CHECK (status IN ('OPEN','PAID','REJECTED'))
);

-- ============================================================================
-- TRAINING DATA
-- medical_insurance_processed.csv, all 17 columns, in file order so \copy lines up.
-- 1337 rows. Sizes below come from the actual data:
--   age 18-64, bmi 16.0-53.1, children 0-5, expenses 1121.87-63770.43
--   gender/region/bmi_category/age_group are low-cardinality text
-- ============================================================================

CREATE TABLE training_data (
                               id                        BIGSERIAL     PRIMARY KEY,
                               age                       SMALLINT,
                               gender                    VARCHAR(10),
                               bmi                       NUMERIC(5,2),
                               children                  SMALLINT,
                               discount_eligibility      VARCHAR(3),
                               region                    VARCHAR(20),
                               expenses                  NUMERIC(12,2),
                               premium                   NUMERIC(12,4),
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

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_base_rates_version         ON base_rates(rate_version);
CREATE INDEX idx_base_rates_age_sex         ON base_rates(age, sex);

CREATE INDEX idx_quotes_status              ON quotes(status);
CREATE INDEX idx_quotes_created_at          ON quotes(created_at);
CREATE INDEX idx_quotes_expires_at          ON quotes(expires_at);
CREATE INDEX idx_quotes_rate_version        ON quotes(rate_version);
CREATE INDEX idx_quotes_age_sex_smoker      ON quotes(age, sex, smoker);

CREATE INDEX idx_policies_status            ON policies(status);
CREATE INDEX idx_policies_start_date        ON policies(start_date);
CREATE INDEX idx_policies_end_date          ON policies(end_date);

CREATE INDEX idx_claims_policy_id           ON claims(policy_id);
CREATE INDEX idx_claims_status              ON claims(status);
CREATE INDEX idx_claims_event_date          ON claims(event_date);
CREATE INDEX idx_claims_created_at          ON claims(created_at);

CREATE INDEX idx_training_data_age          ON training_data(age);
CREATE INDEX idx_training_data_gender       ON training_data(gender);
CREATE INDEX idx_training_data_region       ON training_data(region);
CREATE INDEX idx_training_data_bmi_category ON training_data(bmi_category);
CREATE INDEX idx_training_data_age_group    ON training_data(age_group);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE base_rates    IS 'Base mortality rates by age, sex and smoker status';
COMMENT ON TABLE quotes        IS 'Every quote, declines included';
COMMENT ON TABLE policies      IS 'Policies created from accepted quotes';
COMMENT ON TABLE claims        IS 'Claims filed against policies';
COMMENT ON TABLE training_data IS 'medical_insurance_processed.csv, loaded in full, 1337 rows';

COMMENT ON COLUMN base_rates.rate        IS 'Rate per GBP 1 of cover per year';
COMMENT ON COLUMN training_data.expenses IS 'Claims cost. The modelling target.';
COMMENT ON COLUMN training_data.premium  IS 'Synthetic: expenses / 25, 50 or 100. Not real market pricing.';