-- ============================================================================
-- Base rates for rate version 2026-08.
--
-- rate = the cost per GBP 1 of cover per year, before the BMI multiplier and
-- before the expense loading. 212 rows: ages 18 to 70, both sexes, smoker and
-- non-smoker.
--
-- WHERE THESE NUMBERS COME FROM
--
--   rate = 0.00106590 * exp(0.09 * (age - 35))
--          * 0.85 if female
--          * 2.0  if smoker
--
--   0.00106590  solved backwards so a 35 year old male non-smoker on 250,000
--               of cover pays 392.68 a year, which is the worked example in
--               the README
--   0.09        a Gompertz growth constant. Mortality roughly doubles every
--               8 years in adulthood, and exp(0.09 * 8) is about 2.05
--   0.85 / 2.0  plausible round differentials for sex and smoking
--
-- These are ILLUSTRATIVE. They were not fitted to mortality data, and they did
-- not come from the training CSV. Replace them with a published table (UK ONS
-- national life tables, or the US 2017 CSO) before anyone treats a premium here
-- as real. Doing so needs no code change: the API only ever reads this table.
-- ============================================================================

DELETE FROM base_rates WHERE rate_version = '2026-08';

INSERT INTO base_rates (rate_version, age, sex, smoker, rate)
SELECT '2026-08',
       a.age,
       s.sex,
       sm.smoker,
       ROUND((0.00106590
           * exp(0.09 * (a.age - 35))
           * CASE WHEN s.sex = 'F' THEN 0.85 ELSE 1.0 END
           * CASE WHEN sm.smoker  THEN 2.0  ELSE 1.0 END)::numeric, 8)
FROM   generate_series(18, 70)  AS a(age),
       (VALUES ('M'), ('F'))    AS s(sex),
       (VALUES (true), (false)) AS sm(smoker);

-- 53 ages x 2 sexes x 2 smoker flags = 212
SELECT COUNT(*) AS rows_seeded FROM base_rates WHERE rate_version = '2026-08';

-- The anchor. This must read 0.00106590, or the README example will not tie out.
SELECT rate AS anchor_rate_35m_nonsmoker
FROM   base_rates
WHERE  rate_version = '2026-08' AND age = 35 AND sex = 'M' AND smoker = false;