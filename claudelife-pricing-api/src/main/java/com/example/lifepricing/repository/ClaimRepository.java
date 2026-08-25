package com.example.lifepricing.repository;

import com.example.lifepricing.model.Claim;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.UUID;

public interface ClaimRepository extends JpaRepository<Claim, UUID> {

    /** FR-6: loss ratio by smoker status and age band. PostgreSQL flavour. */
    @Query(value = """
            SELECT CASE WHEN q.smoker THEN 'SMOKER' ELSE 'NON_SMOKER' END AS segment,
                   CASE WHEN q.age < 30 THEN '18-29'
                        WHEN q.age < 45 THEN '30-44'
                        WHEN q.age < 60 THEN '45-59'
                        ELSE '60+' END                                    AS age_band,
                   SUM(p.annual_premium)                                  AS premium,
                   COALESCE(SUM(c.paid), 0)                               AS paid_claims
            FROM policies p
            JOIN quotes q ON q.id = p.quote_id
            LEFT JOIN (SELECT policy_id, SUM(amount) AS paid
                       FROM claims WHERE status = 'PAID'
                       GROUP BY policy_id) c ON c.policy_id = p.id
            GROUP BY 1, 2
            ORDER BY 1, 2
            """, nativeQuery = true)
    List<Object[]> lossRatio();
}
