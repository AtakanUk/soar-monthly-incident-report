# SOAR Monthly Incident Report

[![CI](https://github.com/AtakanUk/soar-monthly-incident-report/actions/workflows/ci.yml/badge.svg)](https://github.com/AtakanUk/soar-monthly-incident-report/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Builds a monthly SOC metrics report from IBM QRadar SOAR and delivers it as HTML (mail body) and PDF (attachment).

The report answers the questions a SOC lead or customer usually asks at the end of the month:

- How many incidents were closed in the period, and with which actions?
- How long does it take to close an incident on average, and which ones were the fastest and slowest?
- Which incidents stayed open for more than *N* days?
- Which offenses were reported to the customer but never got a response?

An additional `workflows` command lists the workflows that are currently active (have at least one enabled rule), which is handy for periodic configuration reviews.

## How it works

1. Closed incidents are pulled from `/incidents/query_paged`, newest first. Paging stops as soon as an incident older than the reporting window is reached, so the full incident history is never downloaded.
2. Option labels of the multi-select "action" field are read from `/types/incident/fields/<field>` so the report shows labels instead of numeric IDs.
3. Incidents flagged as notified (`<notified field> = <value>`) are queried separately. The ones that still carry a value in the approval field are listed as awaiting a response.
4. Metrics are calculated in plain Python (`analytics.py`), rendered to HTML with inline styles so that mail clients keep the layout, and a pie chart of the action distribution is embedded as a base64 PNG.
5. The HTML is converted to PDF with wkhtmltopdf and both are optionally sent by SMTP.

Incidents whose name contains any of the configured exclusion patterns (e.g. noisy test rules or simulation tools) are left out of every metric.

```text
src/soar_monthly_incident_report/
├── cli.py              # argument parsing, orchestration
├── config.py           # environment-based settings
├── soar_client.py      # SOAR REST queries (paging, field values, workflows)
├── analytics.py        # metric calculations
├── charts.py           # matplotlib pie chart
├── html_renderers.py   # report HTML
├── pdf_writer.py       # wkhtmltopdf via pdfkit
└── emailer.py          # SMTP delivery
```

## Requirements

- Python 3.11+
- An IBM QRadar SOAR API key with read access to incidents, incident type fields and workflows
- [wkhtmltopdf](https://wkhtmltopdf.org/) for PDF output (not needed with `--no-pdf`)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env             # then fill in the values
```

## Configuration

All settings are read from environment variables; a `.env` file in the working directory is loaded automatically.

| Variable | Default | Description |
| --- | --- | --- |
| `SOAR_HOST` | – | SOAR hostname |
| `SOAR_PORT` | `443` | SOAR HTTPS port |
| `SOAR_ORG` | – | Organization name |
| `SOAR_API_KEY_ID` / `SOAR_API_KEY_SECRET` | – | API key credentials |
| `SOAR_CAFILE` | system CAs | CA bundle path, or `false` to disable verification (lab only) |
| `REPORT_LOOKBACK_DAYS` | `30` | Size of the reporting window |
| `REPORT_LONG_RUNNING_DAYS` | `2` | Threshold for the "open for more than N days" table |
| `REPORT_EXCLUDE_PATTERNS` | – | Comma-separated substrings; matching incident names are ignored |
| `REPORT_ACTION_FIELD` | `action_info` | Multi-select incident field that records the action taken |
| `REPORT_NOTIFIED_FIELD` / `REPORT_NOTIFIED_VALUE` | `second_info` / `Ok` | Field and value that mark an incident as notified to the customer |
| `REPORT_APPROVAL_FIELD` | `approval` | Field that stays populated until the customer responds |
| `REPORT_RECIPIENT_FIELD` | `mail_to_address` | Field holding the notification recipient |
| `WKHTMLTOPDF_PATH` | found on `PATH` | Explicit path to the wkhtmltopdf binary |
| `SMTP_HOST` / `SMTP_PORT` | – / `25` | Mail relay |
| `SMTP_STARTTLS` | `false` | Upgrade the connection with STARTTLS |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | – | Only needed if the relay requires authentication |
| `MAIL_FROM`, `MAIL_TO`, `MAIL_CC` | – | Sender and comma-separated recipients |
| `MAIL_SUBJECT` | `[IBM QRadar SOAR] Monthly Incident Report` | Mail subject |

The `REPORT_*_FIELD` settings refer to custom incident fields. Adjust them to the API names used in your organization.

## Usage

```bash
# HTML + PDF into ./reports
soar-monthly-report report

# HTML only, mailed to the configured recipients
soar-monthly-report report --no-pdf --send-mail

# Active workflow inventory
soar-monthly-report workflows --output active_workflows.txt
```

`python -m soar_monthly_incident_report ...` works the same way without installing the console script.

For a monthly schedule, a cron entry such as `0 8 1 * * cd /opt/soar-monthly-report && .venv/bin/soar-monthly-report report --send-mail` is enough.

## Tests

```bash
pip install pytest
pytest
```

The tests use a fake REST client and cover paging, metric calculations and HTML rendering; no SOAR instance is needed.

## License

[MIT](LICENSE)
