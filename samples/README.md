# samples/

Small committed export samples — enough rows to illustrate each quirk without requiring a live database.

| File | Format | Quirk illustrated |
|------|--------|-------------------|
| `parts_v1_sample.csv` | CSV UTF-8 | 2019-era column names (`partNo`, `partName`, `cat`, `measure`) |
| `parts_v2_sample.csv` | CSV UTF-8 | Schema drift — `uom` moved before `cat`; extra null `legacy_ref` column |
| `suppliers_legacy_sample.csv` | CSV (Windows-1252 in full export) | Near-duplicate supplier names; inactive supplier still referenced |
| `change_orders_sample.xlsx` | XLSX | Row 1 is a merged section header; notes can contain embedded newlines |

The full exports (all rows) are generated at runtime and available from the running API.
