-- Dynamic Date Column Scanner
-- The legacy ERP schema has tables with 900+ columns, many of which are date
-- fields named inconsistently (TranDate, GateDate, CreatedOn, EntryDate, etc.).
-- This script dynamically discovers every date/datetime column in a given table
-- and counts how many rows have a non-null value in a target month.
--
-- Used during forensics to find which tables are actually receiving data
-- without manually inspecting all 1,394 tables and their date columns.
--
-- Usage: set @TargetTable and @TargetMonth, then execute.

DECLARE @TargetTable  NVARCHAR(128) = 'STOCKTRAN';   -- table to scan
DECLARE @TargetMonth  NVARCHAR(7)   = '2026-08';     -- YYYY-MM

DECLARE @sql          NVARCHAR(MAX) = '';
DECLARE @colName      NVARCHAR(128);

-- Build a UNION query across every date/datetime column in the target table
DECLARE col_cursor CURSOR FOR
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME   = @TargetTable
      AND DATA_TYPE IN ('date', 'datetime', 'datetime2', 'smalldatetime')
    ORDER BY ORDINAL_POSITION;

OPEN col_cursor;
FETCH NEXT FROM col_cursor INTO @colName;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF @sql <> '' SET @sql = @sql + ' UNION ALL ';

    SET @sql = @sql + '
        SELECT
            ''' + @colName + '''          AS date_column,
            COUNT(*)                      AS rows_in_month,
            MIN(' + QUOTENAME(@colName) + ') AS earliest,
            MAX(' + QUOTENAME(@colName) + ') AS latest
        FROM ' + QUOTENAME(@TargetTable) + '
        WHERE FORMAT(' + QUOTENAME(@colName) + ', ''yyyy-MM'') = ''' + @TargetMonth + '''';

    FETCH NEXT FROM col_cursor INTO @colName;
END;

CLOSE col_cursor;
DEALLOCATE col_cursor;

-- Wrap in an ORDER BY so the most active columns surface first
SET @sql = 'SELECT * FROM (' + @sql + ') AS t ORDER BY rows_in_month DESC';

EXEC sp_executesql @sql;

-- Sample output for STOCKTRAN in August 2026:
-- date_column  | rows_in_month | earliest             | latest
-- -------------|---------------|----------------------|---------------------
-- TranDate     | 14,823        | 2026-08-01 00:00:00  | 2026-08-31 23:59:59
-- CreatedOn    | 14,823        | 2026-08-01 08:03:11  | 2026-08-31 22:41:07
-- ModifiedOn   | 2,441         | 2026-08-03 09:12:44  | 2026-08-30 18:22:19
-- PostingDate  | 0             | NULL                 | NULL
-- ...
--
-- Interpretation:
-- TranDate is the active date column. PostingDate and other candidates are
-- unused. This lets us confidently filter by TranDate when auditing activity.


-- ── Bonus: scan ALL tables for any activity in the target month ──────────────
-- Run this to find which of the 1,394 tables have ANY date column with rows
-- in the target month. Useful for a full-schema activity map.

DECLARE @allTablesSql NVARCHAR(MAX) = '';
DECLARE @tbl          NVARCHAR(128);
DECLARE @col          NVARCHAR(128);

DECLARE all_cursor CURSOR FOR
    SELECT c.TABLE_NAME, c.COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS c
    JOIN INFORMATION_SCHEMA.TABLES t
        ON c.TABLE_NAME = t.TABLE_NAME
    WHERE c.DATA_TYPE IN ('date', 'datetime', 'datetime2', 'smalldatetime')
      AND t.TABLE_TYPE = 'BASE TABLE'
    ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;

OPEN all_cursor;
FETCH NEXT FROM all_cursor INTO @tbl, @col;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF @allTablesSql <> '' SET @allTablesSql = @allTablesSql + ' UNION ALL ';

    SET @allTablesSql = @allTablesSql + '
        SELECT
            ''' + @tbl + '''  AS table_name,
            ''' + @col + '''  AS date_column,
            COUNT(*)          AS rows_in_month
        FROM ' + QUOTENAME(@tbl) + '
        WHERE TRY_CONVERT(NVARCHAR(7), ' + QUOTENAME(@col) + ', 120) = ''' + @TargetMonth + '''';

    FETCH NEXT FROM all_cursor INTO @tbl, @col;
END;

CLOSE all_cursor;
DEALLOCATE all_cursor;

SET @allTablesSql = '
    SELECT table_name, date_column, rows_in_month
    FROM (' + @allTablesSql + ') AS all_t
    WHERE rows_in_month > 0
    ORDER BY rows_in_month DESC';

EXEC sp_executesql @allTablesSql;

-- This produces the full activity map: which tables are alive in a given month.
-- Finding from August 2026 forensics:
-- Only 3 tables had non-zero rows: UPDATESTATUS, STOCKTRAN, GatePass.
-- All BOM and issuance tables: 0 rows.
