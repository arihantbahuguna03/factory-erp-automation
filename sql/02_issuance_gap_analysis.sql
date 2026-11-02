-- Raw Material Issuance Gap Analysis
-- Confirms that 500–700 daily floor issuance entries are being written on
-- paper and never entered into the ERP. Both issuance tables should have
-- zero rows — or rows only from purchase-receiving, not floor issuance.
--
-- Cross-checks against STOCKTRAN and GatePass to confirm stock IS moving
-- (just not through the issuance path).

-- 1. Issuance tables — expected: 0 rows
SELECT 'DEPARTMENTRAWISSUEMASTER' AS table_name, COUNT(*) AS row_count
FROM DEPARTMENTRAWISSUEMASTER
UNION ALL
SELECT 'DEPARTMENTRAWISSUETRAN', COUNT(*)
FROM DEPARTMENTRAWISSUETRAN;

-- 2. Confirm stock IS moving (purchase-receiving and gate-out paths are active)
SELECT
    'STOCKTRAN'  AS table_name,
    COUNT(*)     AS row_count,
    MIN(TranDate) AS earliest,
    MAX(TranDate) AS latest
FROM STOCKTRAN
UNION ALL
SELECT
    'GatePass',
    COUNT(*),
    MIN(GateDate),
    MAX(GateDate)
FROM GatePass;

-- 3. Break down STOCKTRAN by transaction type to confirm issuance type is absent
SELECT
    TranType,
    COUNT(*)     AS entries,
    MIN(TranDate) AS from_date,
    MAX(TranDate) AS to_date
FROM STOCKTRAN
GROUP BY TranType
ORDER BY entries DESC;

-- Expected findings:
-- • DEPARTMENTRAWISSUEMASTER   → 0 rows
-- • DEPARTMENTRAWISSUETRAN     → 0 rows
-- • STOCKTRAN                  → many rows, but TranType for floor issuance absent
-- • GatePass                   → active (gate-out is happening)
--
-- Interpretation:
-- Inventory is moving in (purchase-receiving) and out (gate-out) but the
-- middle step — issuing raw material to departments against an order — is
-- completely missing from the system. The ERP's stock figure is therefore
-- always wrong: it shows what was received, not what was actually consumed.
-- Dead stock accumulates silently because the system never records consumption.
