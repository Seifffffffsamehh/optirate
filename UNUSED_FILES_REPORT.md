# Unused Files Report

This report presents a dependency analysis of the OptiRate repository. It identifies files that are not imported, executed, or referenced by the main application flow (defined by `app.py` and the `FRONTEND` SPA architecture).

> [!IMPORTANT]
> **CRITICAL RULE**: Do NOT move or delete any of these files during this phase to preserve historic scripts, test tools, and legacy references.

---

## 1. Scratch / Development Utility Scripts

The following files are standalone Python scripts used during local development, database seeding, or interactive troubleshooting. They are not referenced or imported by any active application route, service, or background scheduler job.

### `analyze_cbe.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/analyze_cbe.py`
* **Import/Reference Analysis**: Not imported anywhere in `app.py`, `services/`, `routes/`, or `models/`.
* **Why it appears unused**: Standalone utility script used to inspect Arabic text patterns in the CBE page source.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `analyze_cbe2.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/analyze_cbe2.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Continuation of cell parsing tests for CBE table data.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `analyze_cbe_main.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/analyze_cbe_main.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Early playground code to locate scrapable HTML elements.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `analyze_cbe_main2.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/analyze_cbe_main2.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Simple BeautifulSoup extraction template.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `check_counts.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/check_counts.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: A script to query the database and count rows in the exchange history tables.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `check_db.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/check_db.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Script to query all users and verify database connection configurations.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `check_ids.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/check_ids.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Debugging script showing user IDs and email addresses stored in SQLite.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `dump_cbe.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/dump_cbe.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Fetches CBE HTML and writes it to a file.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `import_cbe_usd.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/import_cbe_usd.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Standalone utility script designed to manually seed historical USD rates from a text file into SQLite.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `migrate_db.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/migrate_db.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Schema migration script used to add the `plan` and `subscription_expires` columns to the database.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `migrate_plan.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/migrate_plan.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Helper script mapping user role updates to plans.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `refine_history.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/refine_history.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Data cleaning utility to remove or refine duplicate historical rows.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `refine_history2.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/refine_history2.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: A continuation of the database cleaning utilities.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `scratch_test.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/scratch_test.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Generic script for checking server responses.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `scratch_test_cbe.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/scratch_test_cbe.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Temporary script to verify the CbeProvider output.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `scratch_test_silver.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/scratch_test_silver.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Development script testing silver price extraction from DahabMasr / E-Dahab.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `seed_history.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/seed_history.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Mock data generation script to fill `exchange_history` for model testing.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `test.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Generic execution sandbox file.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

---

## 2. Test Verification Scripts

These scripts are used to verify API correctness, predict outputs, scraper functions, and overall logic integrity. They are useful for local QA checks but are not required for the production web app to function.

### `test_all_endpoints.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_all_endpoints.py`
* **Import/Reference Analysis**: Not imported anywhere.
* **Why it appears unused**: Script firing mock HTTP calls to check authentication, public rates, and predictions.
* **Confidence Level**: HIGH
* **Status**: Active File (Used for Verification)

### `test_all_predict.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_all_predict.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Standalone forecasting script calling prediction models directly.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_cbe_provider_final.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_cbe_provider_final.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Verifies scraping results specifically for CBE.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_currencies.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_currencies.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Test target for currency list lengths.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_get_history.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_get_history.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Test script for validating DB historical arrays.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_headers.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_headers.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Checks if WAF blocks headers from Python HTTP calls.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_import.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_import.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Short script verifying imports.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_predict.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_predict.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Checks Prophet fitting limits and linear fallbacks.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_recommend.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_recommend.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Direct verification script for target recommend JSON responses.
* **Confidence Level**: HIGH
* **Status**: Needs Review

### `test_scraper.py`
* **File Path**: `c:/Users/seifs/Desktop/optirate/test_scraper.py`
* **Import/Reference Analysis**: Not imported.
* **Why it appears unused**: Main testing script validating parser resilience for CBE.
* **Confidence Level**: HIGH
* **Status**: Active File (Used for Verification)

---

## 3. Scraping & Data Dumps

These files are temporary outputs of web scraping, dump files, or legacy logs.

### `cbe_dump.html`
* **File Path**: `c:/Users/seifs/Desktop/optirate/cbe_dump.html`
* **Import/Reference Analysis**: Not referenced by code.
* **Why it appears unused**: Captured HTML of the CBE page for offline parsing analysis.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `cbe_dump.txt`
* **File Path**: `c:/Users/seifs/Desktop/optirate/cbe_dump.txt`
* **Import/Reference Analysis**: Not referenced by code.
* **Why it appears unused**: Captured text dump of the CBE rates page.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `cbe_main.html`
* **File Path**: `c:/Users/seifs/Desktop/optirate/cbe_main.html`
* **Import/Reference Analysis**: Not referenced.
* **Why it appears unused**: Legacy cache of crawled HTML.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `dahabmasr.html`
* **File Path**: `c:/Users/seifs/Desktop/optirate/dahabmasr.html`
* **Import/Reference Analysis**: Not referenced.
* **Why it appears unused**: Raw HTML from gold/silver pricing site used to debug parsers.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `debug_currencies.txt`
* **File Path**: `c:/Users/seifs/Desktop/optirate/debug_currencies.txt`
* **Import/Reference Analysis**: Not referenced by code.
* **Why it appears unused**: Generated print log of current rates.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `raw1.txt`
* **File Path**: `c:/Users/seifs/Desktop/optirate/raw1.txt`
* **Import/Reference Analysis**: Not referenced by code.
* **Why it appears unused**: Stale terminal output logs.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

### `scratch_out.txt`
* **File Path**: `c:/Users/seifs/Desktop/optirate/scratch_out.txt`
* **Import/Reference Analysis**: Not referenced.
* **Why it appears unused**: Scraper output dump.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive

---

## 4. Unused Frontend Files

These files are present in the frontend directory but are not requested, rendered, or linked in any index page.

### `payment-modal.html`
* **File Path**: `c:/Users/seifs/Desktop/optirate/FRONTEND/payment-modal.html`
* **Import/Reference Analysis**: Not referenced by any HTML file (`index.html`, `dashboard.html`, `auth.html`, etc.) or JS module in the project.
* **Why it appears unused**: The payment upgrade modal is rendered dynamically using JavaScript in `payment.js` or is hardcoded inline within the pages (`dashboard.html`, `bank-rates.html`). This separate file is not loaded.
* **Confidence Level**: HIGH
* **Status**: Safe to Archive
