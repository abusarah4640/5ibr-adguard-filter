# 5ibr 1.9.0 Final Release

Release date: 2026-07-15

## Overview

5ibr 1.9.0 is the first final release built on the completed production lifecycle and runtime resource architecture.

The release separates installed application code from mutable project state, supports installation from a Python Wheel, and provides safe initialization, lifecycle diagnostics, runtime-isolated CLI commands, and a runtime-isolated Web UI.

This release was promoted only after staged RC validation, isolated package installation, full automated regression testing, live service validation, restart-survival checks, runtime-path verification, package-safety verification, and final release-contract closure.

## Final status

```text
Version                       : 1.9.0
Automated tests               : 422 passed
Intelligence status           : HEALTHY
Production status             : PRODUCTION_ACTIVE
Production HTTP               : 200
RC3 validation HTTP           : 200
Audit integrity               : AUDIT_INTEGRITY_PASS
Blocking reasons              : 0
Runtime isolation             : PASS
Web runtime isolation         : PASS
Audit-service isolation       : PASS
Backup-service isolation      : PASS
Suggestions-service isolation : PASS
Mutable-service isolation     : PASS
Production verification       : PASS
````

## Runtime architecture

The installed package contains immutable application code and safe seed resources.

Mutable state is stored under the active runtime root:

```text
FIVEBR_HOME=/path/to/fivebr-project
```

Runtime directories include:

```text
config/
database/
filters/
releases/
reports/
data/
```

The runtime architecture allows installed application code to remain separate from mutable project state.

For example:

```text
Installed application code:
  /opt/5ibr-rc3/venv/

Active runtime state:
  /opt/5ibr-rc3/runtime/
```

The active runtime root is selected through:

```text
FIVEBR_HOME=/opt/5ibr-rc3/runtime
```

This architecture prevents installed package code from depending on mutable files inside the Python installation directory and allows isolated project initialization, validation, building, diagnostics, and Web UI execution.

## Safe project initialization

A new isolated project can be initialized with:

```bash
fivebr init /path/to/fivebr-project
```

The initialized runtime contains safe seed resources required for first startup.

The final seed contract includes:

```text
config/analyzer.json
config/categories.json
config/database.json
config/releases.json
config/signatures.json
config/vendors.json

database/domains.csv

filters/ads.txt
filters/adult.txt
filters/gaming.txt
filters/mobile.txt
filters/privacy.txt
filters/smart-tv.txt
filters/social.txt
filters/telemetry.txt
filters/whitelist.txt
```

A newly initialized project was verified with:

```text
Decision      : PROJECT_INITIALIZED
Valid         : True
Database rows : 0
Checks passed : 27
Checks failed : 0
Issues        : 0
```

## Runtime-isolated CLI validation

The release was validated from an isolated Wheel installation with an independent runtime root.

The following runtime commands were verified successfully:

```text
fivebr version
fivebr init
fivebr project-status
fivebr stats
fivebr doctor
fivebr validate
fivebr report
fivebr build
fivebr knowledge-check
fivebr intelligence-check
fivebr intelligence-diagnostics
fivebr intelligence-report
fivebr rule-check
```

The initialized runtime successfully generated release artifacts:

```text
all.txt
family.txt
gaming.txt
home.txt
privacy.txt
strict-family.txt
```

## Web runtime isolation

The Web UI now resolves mutable paths from the active runtime root instead of assuming that mutable data exists inside the source checkout or installed package directory.

Runtime-isolated Web resources include:

```text
releases/
reports/
data/uploads/
data/audit/
data/backups/
reports/suggestions.csv
reports/suggestions-rejected.csv
reports/suggestion-decisions.csv
```

The following Web routes were validated successfully from an isolated runtime:

```text
/
 /domains
/reports/suggestions
/analyze
/analyze-log
/analysis
/review-queue
/releases
/audit
/intelligence
```

All tested routes returned HTTP 200 during live RC validation.

## Mutable-service isolation

The following mutable Web services were migrated to the central runtime path architecture:

```text
Audit service
Backup service
Suggestions service
Review decisions
Rejected suggestions
Runtime reports
Runtime uploads
Release downloads
```

Runtime-path regression tests verify that mutable services write only to the active `FIVEBR_HOME` runtime.

Compatibility was also preserved for existing tests and controlled monkeypatch-based test isolation.

## Version architecture

Version resolution is centralized and consistent across:

```text
VERSION
pyproject.toml
fivebr version
Installed package metadata
Web UI
Intelligence report
```

The final release contract verified:

```text
Source VERSION    : 1.9.0
Package metadata  : 1.9.0
Source CLI        : 1.9.0
Installed RC3 CLI : 1.9.0rc3
```

The RC3 validation environment remained unchanged while the source tree was promoted to the final `1.9.0` version.

## Intelligence status

The final intelligence report completed successfully:

```text
Knowledge Base
--------------
Entries            : 6
Status             : OK

Rule Engine
-----------
Vendor Groups      : 11
Category Groups    : 8
Filter Mappings    : 8
Status             : OK

Core Engines
------------
Decision Engine    : OK
Explain Engine     : OK

Database
--------
Known Domains      : 32
Approved           : 32
Pending            : 0

Overall
-------
Status             : HEALTHY
Version            : 1.9.0
```

## Automated verification

The complete automated test suite passed:

```text
422 passed in 3.00s
```

The final release validation includes regression coverage for:

```text
Runtime path resolution
Installed package version resolution
CLI version contract
Web runtime paths
Analyzer runtime configuration
Audit runtime isolation
Backup runtime isolation
Suggestions runtime isolation
Review-decision runtime isolation
Web review queue
One-click approval
Package seed resources
Wheel content contract
Release version contract
Release documentation contract
Release manifest contract
Installed version consumers
```

## Live RC validation

The final release was promoted after live validation of `1.9.0rc3` on a separate service and port.

The RC3 environment was isolated from the production service:

```text
RC3 installed code : /opt/5ibr-rc3/venv
RC3 runtime        : /opt/5ibr-rc3/runtime
RC3 port           : 8091

Production port    : 8089
```

Live acceptance status:

```text
RC3 service               : active
RC3 HTTP                  : 200
Production service        : active
Production HTTP           : 200
Restart survival          : PASS
Clean stability window    : PASS
Application regression    : NOT FOUND
```

The clean stability validation tested:

```text
Routes tested              : 10
Rounds                     : 3
Total requests             : 30
HTTP failures              : 0
All responses              : HTTP 200
Post-test wait             : 75 seconds
Worker timeouts            : 0
Tracebacks                 : 0
Service state after test   : active
```

## Gunicorn worker-timeout closure

During RC validation, one Gunicorn sync worker timeout was observed while the worker was waiting for HTTP request data.

The trace occurred at:

```text
gunicorn/http/unreader.py
self.sock.recv(self.mxchunk)
```

No HTTP URI had been read, and no application route was entered.

The timed-out worker was replaced automatically by Gunicorn. The service remained active, and port `8091` remained listening.

A subsequent clean stability test completed with:

```text
30 successful HTTP requests
0 HTTP failures
0 repeated worker timeouts
0 tracebacks
Service state: active
```

Final classification:

```text
CONNECTION_LEVEL_TIMEOUT
APPLICATION_REGRESSION_NOT_FOUND
STABILITY_GATE_PASS
```

## Restart-survival validation

The RC3 service was explicitly restarted after stability validation.

Post-restart checks confirmed:

```text
RC3 service state          : active
RC3 HTTP                   : 200
Post-restart error scan    : PASS
```

The post-restart journal scan found no:

```text
Traceback
Exception
FileNotFoundError
PermissionError
KeyError
Worker timeout
SIGKILL
HTTP 500
```

## Package safety

The release package does not embed:

```text
Production policies
Production database rows
Audit logs
Suggestion decisions
Evaluation reports
Runtime reports
Runtime backups
Runtime uploads
Mutable production state
```

Packaged seeds contain only safe initialization resources.

The package architecture ensures that a newly installed Wheel starts with safe seed resources rather than copying mutable production state.

## Production safety

The final release preparation preserved the running production environment.

During final version promotion:

```text
Production service        : active
Production HTTP           : 200
RC3 service               : active
RC3 HTTP                  : 200
```

The final version-contract decision was:

```text
FINAL_VERSION_CONTRACT_PASS
RC3_SERVICE_UNCHANGED
PRODUCTION_SERVICE_UNCHANGED
```

## Release artifacts

Final Wheel:

```text
fivebr-1.9.0-py3-none-any.whl
```

Final source distribution:

```text
fivebr-1.9.0.tar.gz
```

Checksums:

```text
SHA256SUMS.txt
```

The final checksums are generated only after the final package build and isolated acceptance test.

## Release decision

The final release is accepted only after successful completion of:

```text
Final version contract          : PASS
Full automated test suite       : PASS
Intelligence health             : HEALTHY
Runtime architecture            : PASS
Installed Wheel validation      : PASS
CLI runtime isolation           : PASS
Web runtime isolation           : PASS
Mutable-service isolation       : PASS
Package safety                  : PASS
Live RC validation              : PASS
Restart survival                : PASS
Clean stability window          : PASS
Application regression          : NOT FOUND
Production verification         : PASS
Blocking reasons                : 0
```

Final decision:

```text
5ibr 1.9.0
FINAL RELEASE READY
```
