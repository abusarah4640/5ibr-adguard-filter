# 5ibr AdGuard Filter

An open-source AdGuard Home filter project focused on privacy, security, telemetry blocking and gaming.

## Features

- Modular filter generation
- Automatic release generation
- Database-driven domain management
- CLI toolkit
- Validation system
- Statistics and reporting

## Installation

```bash
git clone https://github.com/abusarah4640/5ibr-adguard-filter.git
cd 5ibr-adguard-filter
python fivebr.py build
```

## Commands

```bash
python fivebr.py build
python fivebr.py validate
python fivebr.py report
python fivebr.py stats
python fivebr.py search <domain>
```

## Project Structure

```
config/
database/
docs/
filters/
releases/
scripts/
tests/
```

## Roadmap

### v0.2.0

- Database Manager
- CLI
- Search
- Stats
- Add
- Remove
- Update

### v0.3.0

- Analyzer
- Reports
- HTML Dashboard

### v1.0.0

- Stable Release

## License

GPL-3.0
