-- BOM Module Gap Analysis
-- Confirms that the Bill of Materials module in the legacy ERP is entirely
-- unused. Run this before proposing the BOM automation module so you have
-- a baseline row count to show the client and reference post-go-live.
--
-- All 8 BOM-related tables checked. Expected finding: zero rows across all.

SELECT 'PROCESSCONSUMPTIONMASTER'    AS table_name, COUNT(*) AS row_count FROM PROCESSCONSUMPTIONMASTER
UNION ALL
SELECT 'PROCESSCONSUMPTIONDETAIL',                  COUNT(*) FROM PROCESSCONSUMPTIONDETAIL
UNION ALL
SELECT 'ORDER_CONSUMPTION_DETAIL',                  COUNT(*) FROM ORDER_CONSUMPTION_DETAIL
UNION ALL
SELECT 'ARTICLEMASTER',                             COUNT(*) FROM ARTICLEMASTER
UNION ALL
SELECT 'ARTICLEDETAIL',                             COUNT(*) FROM ARTICLEDETAIL
UNION ALL
SELECT 'PROCESSCONSUMPTIONMASTER_TEMP',             COUNT(*) FROM PROCESSCONSUMPTIONMASTER_TEMP
UNION ALL
SELECT 'PROCESSCONSUMPTIONDETAIL_TEMP',             COUNT(*) FROM PROCESSCONSUMPTIONDETAIL_TEMP
UNION ALL
SELECT 'BOM_APPROVAL_LOG',                          COUNT(*) FROM BOM_APPROVAL_LOG
ORDER BY row_count DESC;

-- Expected output (zero rows across all BOM tables):
-- table_name                        | row_count
-- ----------------------------------|----------
-- PROCESSCONSUMPTIONMASTER          | 0
-- PROCESSCONSUMPTIONDETAIL          | 0
-- ORDER_CONSUMPTION_DETAIL          | 0
-- ... (all zeros)

-- Interpretation:
-- The BOM module has never been used. Every consumption figure in the ERP
-- is either absent or manually back-calculated. This is why actual vs.
-- planned consumption comparisons are impossible — there is no "planned"
-- figure in the system.
