# Data QA Report

_Database_: `/home/cynic/workspace/champion_prophet/database/email_database.db`

## Coverage

- Earliest date: **2025-05-18**
- Latest date: **2025-10-25**
- Total days in scope: **156**
- Days with email data: **155**
- Days with SLA/hourly data: **74**

## Daily Table Null Counts

| Column | Null Rows |
| --- | --- |
| `avg_response_time_minutes` | 86 |
| `avg_unread_count` | 82 |
| `category_completed` | 82 |
| `category_deleted` | 82 |
| `category_inbox` | 82 |
| `category_replied` | 82 |
| `category_worked` | 82 |
| `completed_count` | 0 |
| `date` | 0 |
| `deleted_count` | 82 |
| `has_email_data` | 0 |
| `has_sla_data` | 0 |
| `inbox_total` | 0 |
| `median_response_time_minutes` | 86 |
| `pending_count` | 82 |
| `replied_count` | 82 |
| `reply_rate_percent` | 82 |
| `sent_total` | 0 |
| `sla_compliance_rate` | 82 |
| `total_emails` | 82 |
| `worked_count` | 82 |

## Duplicate Date Checks

No duplicate dates detected in `days` table.

## Hourly Coverage

- Expected hourly rows (24 × SLA days): **1776**
- Actual hourly rows: **1776**
- Rows with null hourly metrics: **0**
- All SLA days contain full 24 hourly rows.