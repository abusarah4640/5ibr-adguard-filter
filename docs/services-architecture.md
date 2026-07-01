# Services Architecture

Phase 3 separates user interaction from business logic.

```text
fivebr.py
    ↓
CLI command modules
    ↓
scripts/services/
    ↓
scripts/database.py
    ↓
database/domains.csv
```

## Services

- `integrity_service.py`: validates domains, categories, filters, status and confidence.
- `database_service.py`: shared add/update/integrity operations with metadata support.
- `review_service.py`: Pending → Approved/Rejected workflow.
- `report_service.py`: reusable report counters for vendors, categories and statuses.

This makes future REST API or Web UI development possible without rewriting the core logic.
