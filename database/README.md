# Email Database Documentation

## Overview

This directory contains the unified email analytics database that powers daily and weekly dashboard generation. The database stores email event data, SLA metrics, response times, and agent performance tracking.

## Database Files

### Active Files
- **`email_database.db`** - Primary SQLite database (7.7 MB)
  - Fast querying with SQL support
  - Used by dashboard generators with `--use-sqlite` flag
  - Contains all data including deduplication keys in `processed_keys` table
  - Schema version: 2.0.0

- **`email_database.json`** - JSON database (1.2 MB)
  - Default format for backward compatibility
  - Human-readable structure
  - Used by legacy scripts and validation tools
  - Does NOT include deduplication keys (now in SQLite)

### Archived Files
Old backups, exports, and deprecated files have been moved to `archive/` subdirectory:
- `email_database_backup_20250823_025925.json` - Old database backup (Aug 2025)
- `email_database_backup_manual.json` - Manual backup
- `email_database_export.json` - Export file
- `email_database_pre_reconciliation_20251023_235115.json` - Pre-reconciliation backup
- `processed_keys_legacy_20251026.json` - Legacy deduplication keys (2.9 MB, migrated to SQLite)

## Data Coverage

### Historical Data (Daily Totals Only)
**Date Range:** May 18, 2025 → August 12, 2025 (82 days)

**Available Fields:**
- `inbox_total` - Total emails received
- `sent_total` - Total emails sent/replied
- `completed_count` - Total emails completed/closed
- Flags: `has_email_data=1`, `has_sla_data=0`

**Note:** Historical data does NOT include hourly breakdowns or SLA metrics. This data is sourced from DailySummary.csv and is suitable for daily-level forecasting but should not be used for hourly analysis.

### Full Data (Daily + Hourly)
**Date Range:** August 13, 2025 → October 25, 2025 (73 days)

**Available Fields:**
- All daily summary metrics (totals, rates, response times)
- 24-hour granular data (emails received/replied/completed per hour)
- SLA compliance tracking (unread counts, thresholds)
- Agent performance metrics (per-agent hourly activity)
- Flags: `has_email_data=1`, `has_sla_data=1`

**Note:** Full data includes complete hourly breakdowns and is suitable for all types of analysis including hourly forecasting, capacity planning, and detailed performance analytics.

## Database Schema

### Schema Version
**Current Version:** 2.0.0  
**Last Updated:** 2025-10-25

### Table: `metadata`
Stores database-level metadata and version information.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key (always 1) |
| `schema_version` | TEXT | Schema version (e.g., "2.0.0") |
| `last_updated` | TEXT | ISO timestamp of last update |
| `total_days_processed` | INTEGER | Total days in database |
| `earliest_date` | TEXT | Earliest date in dataset |
| `latest_date` | TEXT | Latest date in dataset |
| `data_sources` | TEXT | JSON array of data sources |

### Table: `days`
Stores daily-level summary metrics for each date.

| Column | Type | Description |
|--------|------|-------------|
| `date` | TEXT | Date in YYYY-MM-DD format (PRIMARY KEY) |
| `has_email_data` | INTEGER | Boolean flag (1=has email data, 0=no data) |
| `has_sla_data` | INTEGER | Boolean flag (1=has SLA/hourly data, 0=daily only) |
| `total_emails` | INTEGER | Total emails processed |
| `replied_count` | INTEGER | Number of emails replied to |
| `completed_count` | INTEGER | Number of emails completed/closed |
| `deleted_count` | INTEGER | Number of emails deleted |
| `worked_count` | INTEGER | Total emails worked (replied + completed) |
| `pending_count` | INTEGER | End-of-day pending/unread count |
| `inbox_total` | INTEGER | Total inbox emails received |
| `sent_total` | INTEGER | Total sent emails |
| `reply_rate_percent` | REAL | Percentage of emails replied to |
| `avg_response_time_minutes` | REAL | Average response time in business minutes |
| `median_response_time_minutes` | REAL | Median response time in business minutes |
| `sla_compliance_rate` | REAL | SLA compliance percentage (0-100) |
| `avg_unread_count` | REAL | Average hourly unread count |
| `category_inbox` | INTEGER | Category count: Inbox events |
| `category_replied` | INTEGER | Category count: Replied events |
| `category_completed` | INTEGER | Category count: Completed events |
| `category_deleted` | INTEGER | Category count: Deleted events |
| `category_worked` | INTEGER | Category count: Worked events |

**Data Quality Notes:**
- Historical dates (pre-Aug 13, 2025): Only `inbox_total`, `sent_total`, and `completed_count` are populated
- Full data dates (Aug 13+): All fields are populated including response times and SLA metrics
- `has_sla_data=0` indicates daily totals only (no hourly breakdown available)

### Table: `hourly_data`
Stores hour-by-hour metrics for each date (24 rows per day, hours 0-23).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `date` | TEXT | Date in YYYY-MM-DD format (FOREIGN KEY → days.date) |
| `hour` | INTEGER | Hour of day (0-23) |
| `emails_received` | INTEGER | Emails received during this hour |
| `emails_replied` | INTEGER | Emails replied to during this hour |
| `emails_completed` | INTEGER | Emails completed during this hour |
| `emails_deleted` | INTEGER | Emails deleted during this hour |
| `emails_worked` | INTEGER | Total worked (replied + completed) |
| `avg_response_time` | REAL | Average response time for hour (business minutes) |
| `unread_count` | INTEGER | Unread email count at end of hour |
| `sla_met` | INTEGER | Boolean flag (1=SLA met, 0=breached) |
| `active_agent_count` | INTEGER | Number of agents active during hour |
| `active_agents` | TEXT | JSON array of active agent names |
| `agent_replies` | TEXT | JSON object of per-agent reply counts |

**Constraints:**
- `UNIQUE(date, hour)` - Only one entry per date/hour combination
- `hour` must be between 0-23

**Data Availability:**
- Historical dates (pre-Aug 13, 2025): **NO hourly data** (table has 0 rows for these dates)
- Full data dates (Aug 13+): Complete 24-hour data available

### Table: `agent_metrics`
Stores agent performance metrics aggregated by date.

| Column | Type | Description |
|--------|------|-------------|
| `date` | TEXT | Date in YYYY-MM-DD format (PRIMARY KEY, FOREIGN KEY → days.date) |
| `agent_counts` | TEXT | JSON object: agent name → total reply count |
| `agent_group_counts` | TEXT | JSON object: agent group metrics |
| `responses_with_agent` | INTEGER | Number of responses with agent signature |
| `total_replied_responses` | INTEGER | Total replied responses |
| `unmatched_replied_responses` | INTEGER | Replies without agent signature |
| `hourly_agent_summary` | TEXT | JSON array: per-hour agent activity |

**JSON Field Examples:**
```json
// agent_counts
{"Nathan": 45, "Shay": 38, "Kamil": 29}

// hourly_agent_summary
[
  {"hour": 7, "agents": ["Nathan", "Shay"], "replies": {"Nathan": 3, "Shay": 2}},
  {"hour": 8, "agents": ["Nathan", "Shay", "Kamil"], "replies": {"Nathan": 5, "Shay": 4, "Kamil": 3}}
]
```

### Table: `aggregates`
Stores global aggregated metrics across all dates.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key (always 1) |
| `global_hourly_worked` | TEXT | JSON array: 24-hour global workload summary |

**JSON Field Example:**
```json
// global_hourly_worked
[
  {"hour": 0, "total_worked": 15, "avg_per_day": 0.5},
  {"hour": 7, "total_worked": 1250, "avg_per_day": 17.1},
  {"hour": 14, "total_worked": 2180, "avg_per_day": 29.7}
]
```

### Table: `events` (Reserved)
Placeholder table for future event-level granularity. Currently not populated.

### Table: `processed_keys`
Stores deduplication keys to prevent duplicate email entries across ingestion runs.

| Column | Type | Description |
|--------|------|-------------|
| `date` | TEXT | Date in YYYY-MM-DD format (part of PRIMARY KEY) |
| `event_type` | TEXT | Event type: Inbox, Replied, Completed, Deleted (part of PRIMARY KEY) |
| `dedup_key` | TEXT | Unique deduplication key derived from message ID (part of PRIMARY KEY) |

**Constraints:**
- `PRIMARY KEY (date, event_type, dedup_key)` - Ensures uniqueness across all three columns

**Purpose:**
- Prevents duplicate entries when re-ingesting overlapping CSV exports
- Tracks ~30K deduplication keys across all processed dates
- Updated automatically during ingestion runs

**Migration Note:**
- Prior to Oct 26, 2025, deduplication keys were stored in separate `processed_keys.json` file (2.9 MB)
- Keys migrated to SQLite table for better integration and performance
- Legacy JSON file archived as `archive/processed_keys_legacy_20251026.json`

## Usage Examples

### Query Daily Totals
```python
import sqlite3
conn = sqlite3.connect('database/email_database.db')
cur = conn.cursor()

# Get all dates with full data
cur.execute('''
    SELECT date, inbox_total, sent_total, completed_count, 
           avg_response_time_minutes, sla_compliance_rate
    FROM days 
    WHERE has_sla_data = 1
    ORDER BY date
''')
```

### Query Hourly Data
```python
# Get hourly breakdown for specific date
cur.execute('''
    SELECT hour, emails_received, emails_worked, unread_count, sla_met
    FROM hourly_data
    WHERE date = '2025-10-15'
    ORDER BY hour
''')
```

### Filter by Data Type
```python
# Get only dates suitable for hourly forecasting
cur.execute('''
    SELECT date FROM days 
    WHERE has_sla_data = 1  -- Full hourly data available
    ORDER BY date
''')

# Get all dates for daily-level analysis
cur.execute('''
    SELECT date, inbox_total, sent_total, completed_count 
    FROM days 
    WHERE has_email_data = 1  -- Includes both historical and full data
    ORDER BY date
''')
```

## Data Quality Flags

### `has_email_data`
- **1** = Date has email data (at minimum: inbox_total, sent_total, completed_count)
- **0** = Date has no data

### `has_sla_data`
- **1** = Date has complete hourly SLA data (24 hours of unread counts, response times)
- **0** = Date has daily totals only, no hourly breakdown

### Recommended Usage by Data Type

| Analysis Type | Required Flag | Date Range | Notes |
|--------------|---------------|------------|-------|
| Daily forecasting | `has_email_data=1` | May 18+ (156 days) | Use all dates |
| Hourly forecasting | `has_sla_data=1` | Aug 13+ (73 days) | Filter for complete data |
| Capacity planning | `has_sla_data=1` | Aug 13+ | Requires agent metrics |
| Weekly KPIs | `has_email_data=1` | May 18+ | Daily aggregation only |

## Maintenance

### Backup Strategy
- Automatic backups created during ingestion runs
- Old backups moved to `archive/` directory
- Retention: Keep last 2-3 backups, archive older versions

### Database Updates
```bash
# Update database with new CSV data
./update_database.sh

# Update with SQLite support
./update_database.sh --sqlite

# Direct ingestion
python3 scripts/daily/ingest_and_update.py --use-sqlite
```

### Schema Migration
If schema updates are needed:
```bash
# Backup first
cp email_database.db email_database_backup_$(date +%Y%m%d_%H%M%S).db

# Run migration script (if available)
python3 scripts/migrations/migrate_to_sqlite.py
```

## Related Documentation
- **Architecture:** `documentation/architecture.md`
- **Ingestion System:** `scripts/daily/README_INGESTION.md`
- **Dashboard Generation:** `templates/daily_report.html`
- **SQLite Migration:** `documentation/sqlite_migration.md`

## Troubleshooting

### Missing Hourly Data
**Symptom:** Dashboard shows zeros for hourly charts  
**Solution:** Check `has_sla_data` flag. Historical dates (pre-Aug 13) don't have hourly data by design.

### Date Not Found
**Symptom:** Query returns no results for a date  
**Solution:** Check date range. Database only contains May 18, 2025 onwards. Use `SELECT MIN(date), MAX(date) FROM days` to confirm coverage.

### Inconsistent Totals
**Symptom:** Daily totals don't match hourly sums  
**Solution:** Run reconciliation check in ingestion script. Full data dates should always have matching totals.

---

**Last Updated:** 2025-10-26  
**Database Version:** 2.0.0  
**Total Records:** 156 days (82 historical + 74 full)
