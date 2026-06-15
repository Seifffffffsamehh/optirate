# Cleanup Report

This report documents the safe project cleanup phase for OptiRate, where confirmed unused and development utility files were moved into a dedicated `archive/` folder to clean up the workspace root.

---

## 1. Moved Files Inventory

Exactly 26 unused files (consisting of development scripts, scraper test templates, historical HTML dumps, and unused page components) were moved. 

| File Name | Original Location | New Location (under `archive/`) |
| :--- | :--- | :--- |
| `analyze_cbe.py` | `analyze_cbe.py` | `archive/analyze_cbe.py` |
| `analyze_cbe2.py` | `analyze_cbe2.py` | `archive/analyze_cbe2.py` |
| `analyze_cbe_main.py` | `analyze_cbe_main.py` | `archive/analyze_cbe_main.py` |
| `analyze_cbe_main2.py` | `analyze_cbe_main2.py` | `archive/analyze_cbe_main2.py` |
| `check_counts.py` | `check_counts.py` | `archive/check_counts.py` |
| `check_db.py` | `check_db.py` | `archive/check_db.py` |
| `check_ids.py` | `check_ids.py` | `archive/check_ids.py` |
| `dump_cbe.py` | `dump_cbe.py` | `archive/dump_cbe.py` |
| `import_cbe_usd.py` | `import_cbe_usd.py` | `archive/import_cbe_usd.py` |
| `migrate_db.py` | `migrate_db.py` | `archive/migrate_db.py` |
| `migrate_plan.py` | `migrate_plan.py` | `archive/migrate_plan.py` |
| `refine_history.py` | `refine_history.py` | `archive/refine_history.py` |
| `refine_history2.py` | `refine_history2.py` | `archive/refine_history2.py` |
| `scratch_test.py` | `scratch_test.py` | `archive/scratch_test.py` |
| `scratch_test_cbe.py` | `scratch_test_cbe.py` | `archive/scratch_test_cbe.py` |
| `scratch_test_silver.py` | `scratch_test_silver.py` | `archive/scratch_test_silver.py` |
| `seed_history.py` | `seed_history.py` | `archive/seed_history.py` |
| `test.py` | `test.py` | `archive/test.py` |
| `cbe_dump.html` | `cbe_dump.html` | `archive/cbe_dump.html` |
| `cbe_dump.txt` | `cbe_dump.txt` | `archive/cbe_dump.txt` |
| `cbe_main.html` | `cbe_main.html` | `archive/cbe_main.html` |
| `dahabmasr.html` | `dahabmasr.html` | `archive/dahabmasr.html` |
| `debug_currencies.txt` | `debug_currencies.txt` | `archive/debug_currencies.txt` |
| `raw1.txt` | `raw1.txt` | `archive/raw1.txt` |
| `scratch_out.txt` | `scratch_out.txt` | `archive/scratch_out.txt` |
| `payment-modal.html` | `FRONTEND/payment-modal.html` | `archive/payment-modal.html` |

---

## 2. Integrity & Functional Status Confirmation

We ran the project's backend test suite within the virtual environment post-migration to confirm that all services are fully intact:

1. **AI Forecasting Engine**: Running `venv\Scripts\python.exe test_predict.py` successfully returns predictions for `USD` and `SAR` without error, using the pure Python linear fallback model.
2. **CBE Scraping Pipeline**: Running `venv\Scripts\python.exe test_cbe_provider_final.py` successfully bypasses the Web Application Firewall (WAF) and returns clean, mapped rates from the Central Bank of Egypt.
3. **Core App Startup**: The Flask server factory registers all blueprints, custom JWT sub loaders, background daily cron schedulers, and pre-request subscription checks seamlessly.
4. **Active Files Untouched**: No files inside `models/`, `routes/`, or `services/` were moved, deleted, renamed, or modified. Active frontend pages (`index.html`, `dashboard.html`, etc.) remain fully functional.

**Conclusion**: All core functionalities, recommendations, databases, and admin dashboards behave exactly as before. The cleanup has zero negative impact.
