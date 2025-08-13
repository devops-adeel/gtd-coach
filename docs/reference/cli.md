# CLI Reference

## Main Commands

### gtd_coach
```bash
python -m gtd_coach [options]
```

Options:
- `--config PATH` - Custom config file location
- `--skip-timing` - Skip Timing app integration
- `--debug` - Enable debug logging
- `--version` - Show version

### Scripts

#### start-coach.sh
Full system startup including LM Studio.
```bash
./scripts/start-coach.sh
```

#### docker-run.sh
Docker execution wrapper.
```bash
./scripts/deployment/docker-run.sh [command]
```

Commands:
- `(none)` - Run weekly review
- `build` - Build Docker image
- `shell` - Open container shell
- `test` - Run test suite
- `timing` - Test Timing integration
- `summary` - Generate weekly summary

#### timer.sh
Standalone timer with audio alerts.
```bash
./scripts/timer.sh MINUTES MESSAGE
```

Example:
```bash
./scripts/timer.sh 5 "Time's up!"
```

## Data Management

### Export Data
```bash
python -m gtd_coach.export --format json --output export.json
```

### Generate Summary
```bash
python generate_summary.py [--week YYYY-MM-DD]
```

### Clean Old Data
```bash
python scripts/clean_old_data.py --days 90
```

## Testing Commands

### Run All Tests
```bash
pytest
```

### Coverage Report
```bash
pytest --cov=gtd_coach --cov-report=html
```

### Integration Tests
```bash
pytest tests/integration/ --real-apis
```

## Development Commands

### Format Code
```bash
black gtd_coach/ tests/
```

### Lint
```bash
ruff check gtd_coach/
```

### Type Check
```bash
mypy gtd_coach/
```

## Docker Commands

### Build Image
```bash
docker compose build
```

### Run Review
```bash
docker compose up gtd-coach
```

### Execute Command
```bash
docker compose run gtd-coach python script.py
```

### View Logs
```bash
docker compose logs -f gtd-coach
```