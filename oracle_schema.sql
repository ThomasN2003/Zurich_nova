-- ============================================================================
-- Oracle Database Schema Conversion from PostgreSQL
-- ============================================================================

-- Drop existing objects if they exist (for clean re-runs)
BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE claims CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE policies CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE quotes CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE base_rates CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE training_data CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP SEQUENCE training_data_seq';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================================
-- SEQUENCES
-- ============================================================================

-- Sequence for training_data table (replaces BIGSERIAL)
CREATE SEQUENCE training_data_seq
  START WITH 1
  INCREMENT BY 1
  NOCACHE
  NOCYCLE;

-- ============================================================================
-- TABLES
-- ============================================================================

-- BASE_RATES table
CREATE TABLE base_rates (
  rate_version  VARCHAR2(50) NOT NULL,
  age           NUMBER(5) NOT NULL,
  sex           CHAR(1) NOT NULL,
  smoker        NUMBER(1) NOT NULL,  -- 0=false, 1=true (Oracle has no BOOLEAN)
  rate          NUMBER(10,8) NOT NULL,
  CONSTRAINT pk_base_rates PRIMARY KEY (rate_version, age, sex, smoker),
  CONSTRAINT chk_base_rates_sex CHECK (sex IN ('M','F')),
  CONSTRAINT chk_base_rates_smoker CHECK (smoker IN (0,1))
);

-- QUOTES table
CREATE TABLE quotes (
  id               RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
  age              NUMBER(5) NOT NULL,
  sex              CHAR(1) NOT NULL,
  smoker           NUMBER(1) NOT NULL,
  bmi              NUMBER(5,2) NOT NULL,
  sum_assured      NUMBER(12,2) NOT NULL,
  term_years       NUMBER(5) NOT NULL,
  rate_version     VARCHAR2(50) NOT NULL,
  annual_premium   NUMBER(10,2),
  monthly_premium  NUMBER(10,2),
  status           VARCHAR2(20) NOT NULL,
  expires_at       DATE NOT NULL,
  created_at       TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT chk_quotes_sex CHECK (sex IN ('M','F')),
  CONSTRAINT chk_quotes_smoker CHECK (smoker IN (0,1)),
  CONSTRAINT chk_quotes_status CHECK (status IN ('QUOTED','DECLINED','ACCEPTED','EXPIRED'))
);

-- POLICIES table
CREATE TABLE policies (
  id              RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
  quote_id        RAW(16) NOT NULL UNIQUE,
  policy_number   VARCHAR2(50) NOT NULL UNIQUE,
  start_date      DATE NOT NULL,
  end_date        DATE NOT NULL,
  annual_premium  NUMBER(10,2) NOT NULL,
  status          VARCHAR2(20) NOT NULL,
  CONSTRAINT fk_policies_quote FOREIGN KEY (quote_id) REFERENCES quotes(id),
  CONSTRAINT chk_policies_status CHECK (status IN ('ACTIVE','CLAIMED','EXPIRED','CANCELLED'))
);

-- CLAIMS table
CREATE TABLE claims (
  id          RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
  policy_id   RAW(16) NOT NULL,
  event_date  DATE NOT NULL,
  amount      NUMBER(12,2) NOT NULL,
  status      VARCHAR2(20) NOT NULL,
  created_at  TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT fk_claims_policy FOREIGN KEY (policy_id) REFERENCES policies(id),
  CONSTRAINT chk_claims_status CHECK (status IN ('OPEN','PAID','REJECTED'))
);

-- TRAINING_DATA table
CREATE TABLE training_data (
  id        NUMBER(19) PRIMARY KEY,
  age       NUMBER(5),
  gender    VARCHAR2(10),
  bmi       NUMBER(5,2),
  children  NUMBER(5),
  region    VARCHAR2(50),
  expenses  NUMBER(12,2),
  premium   NUMBER(12,2)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Indexes on base_rates
CREATE INDEX idx_base_rates_version ON base_rates(rate_version);
CREATE INDEX idx_base_rates_age_sex ON base_rates(age, sex);

-- Indexes on quotes
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_created_at ON quotes(created_at);
CREATE INDEX idx_quotes_expires_at ON quotes(expires_at);
CREATE INDEX idx_quotes_rate_version ON quotes(rate_version);
CREATE INDEX idx_quotes_age_sex_smoker ON quotes(age, sex, smoker);

-- Indexes on policies
CREATE INDEX idx_policies_quote_id ON policies(quote_id);
CREATE INDEX idx_policies_policy_number ON policies(policy_number);
CREATE INDEX idx_policies_status ON policies(status);
CREATE INDEX idx_policies_start_date ON policies(start_date);
CREATE INDEX idx_policies_end_date ON policies(end_date);

-- Indexes on claims
CREATE INDEX idx_claims_policy_id ON claims(policy_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_event_date ON claims(event_date);
CREATE INDEX idx_claims_created_at ON claims(created_at);

-- Indexes on training_data
CREATE INDEX idx_training_data_age ON training_data(age);
CREATE INDEX idx_training_data_gender ON training_data(gender);
CREATE INDEX idx_training_data_region ON training_data(region);

-- ============================================================================
-- TRIGGERS FOR AUTO-INCREMENT
-- ============================================================================

-- Trigger for training_data to auto-populate ID from sequence
CREATE OR REPLACE TRIGGER trg_training_data_id
BEFORE INSERT ON training_data
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
  SELECT training_data_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE base_rates IS 'Base insurance rates by age, sex, and smoker status';
COMMENT ON TABLE quotes IS 'Insurance quotes generated for customers';
COMMENT ON TABLE policies IS 'Active insurance policies';
COMMENT ON TABLE claims IS 'Claims filed against policies';
COMMENT ON TABLE training_data IS 'Kaggle CSV training data for ML models';

COMMENT ON COLUMN base_rates.rate IS 'Rate per £1 of cover per year';
COMMENT ON COLUMN quotes.smoker IS '0=non-smoker, 1=smoker';
COMMENT ON COLUMN base_rates.smoker IS '0=non-smoker, 1=smoker';
