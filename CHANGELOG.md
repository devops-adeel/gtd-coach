# Changelog

All notable changes to GTD Coach will be documented in this file.

## [2.0.0] - 2024-08-10

### 🚨 BREAKING CHANGES - Major Reorganization

This version introduces a complete restructuring of the codebase for better maintainability and developer experience.

#### Migration Required

The project has been reorganized from a flat structure to a proper Python package structure. If you have existing scripts or configurations, you'll need to update them.

### Changed

#### File Structure
- **Moved to package structure**: All Python code now under `gtd_coach/` package
- **Organized by feature**: Pattern detection in `patterns/`, integrations in `integrations/`
- **Centralized configuration**: All config files in `config/` directory
- **Consolidated documentation**: Reduced from 18+ files to 3 main docs

#### Import Changes
All imports have changed. Update your code:

**Before:**
```python
from gtd_review import GTDCoach
from adhd_patterns import ADHDPatternDetector
from graphiti_integration import GraphitiMemory
```

**After:**
```python
from gtd_coach.coach import GTDCoach
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector
from gtd_coach.integrations.graphiti import GraphitiMemory
```

#### Running the Application

**Before:**
```bash
python gtd-review.py
./start-coach.sh
```

**After:**
```bash
python -m gtd_coach
./scripts/start-coach.sh
```

#### Docker Changes
- Dockerfile moved to `config/docker/Dockerfile`
- docker-compose.yml moved to `config/docker/docker-compose.yml`
- Updated to use new package structure

### File Mapping

| Old Location | New Location |
|-------------|--------------|
| `gtd-review.py` | `gtd_coach/coach.py` |
| `adhd_patterns.py` | `gtd_coach/patterns/adhd_metrics.py` |
| `pattern_detector.py` | `gtd_coach/patterns/detector.py` |
| `memory_enhancer.py` | `gtd_coach/patterns/memory_enhancer.py` |
| `graphiti_integration.py` | `gtd_coach/integrations/graphiti.py` |
| `langfuse_tracker.py` | `gtd_coach/integrations/langfuse.py` |
| `timing_integration.py` | `gtd_coach/integrations/timing.py` |
| `generate_summary.py` | `scripts/generate_summary.py` |
| `start-coach.sh` | `scripts/start-coach.sh` |
| `docker-run.sh` | `scripts/docker-run.sh` |
| `.env.example` | `config/.env.example` |
| `Dockerfile` | `config/docker/Dockerfile` |
| `docker-compose.yml` | `config/docker/docker-compose.yml` |

### Documentation Changes

| Old Files | New Location |
|-----------|--------------|
| `USAGE_GUIDE.md`, `QUICK_REFERENCE.md`, etc. | `docs/USER_GUIDE.md` |
| `SETUP_COMPLETE.md`, `DOCKER_DEPLOYMENT.md`, etc. | `docs/DEVELOPER.md` |
| `TIMING_SETUP.md`, `LANGFUSE_INTEGRATION.md`, etc. | `docs/CONFIGURATION.md` |
| Integration-specific docs | `docs/integrations/` |

### Improved

- **Better organization**: Clear separation of concerns with feature-based structure
- **Easier navigation**: Intuitive package layout following Python best practices
- **Cleaner imports**: Proper namespace packaging
- **Documentation discovery**: Consolidated from 18+ files to 3 main guides
- **Test organization**: Tests mirror source structure in `tests/` directory
- **Professional structure**: Follows modern Python packaging standards

### How to Migrate

1. **Backup your data**:
   ```bash
   cp -r data/ data_backup/
   cp .env .env.backup
   ```

2. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

3. **Update your .env file location** (if customized):
   ```bash
   cp .env.backup .env
   ```

4. **Update any custom scripts** to use new imports

5. **Test the new structure**:
   ```bash
   python test_structure.py
   python -m gtd_coach --help
   ```

6. **Clean up old files** (optional, after confirming everything works):
   ```bash
   # Remove old Python files that were moved
   rm gtd-review.py adhd_patterns.py  # etc.
   ```

### Notes

- All functionality remains the same - this is purely a structural reorganization
- Data files in `data/`, `logs/`, and `summaries/` are unaffected
- Configuration in `.env` files continues to work as before
- The reorganization makes the codebase more maintainable and professional

---

## [1.x.x] - Previous Versions

### [1.5.0] - 2024-08-09
- Added Langfuse integration for LLM observability
- Implemented prompt management system
- Added A/B testing for coaching tones

### [1.4.0] - 2024-08-08
- Integrated Timing app for real project tracking
- Added focus score calculations
- Implemented context switch detection

### [1.3.0] - 2024-08-07
- Added Graphiti memory integration
- Implemented pattern detection across sessions
- Added memory enhancement features

### [1.2.0] - 2024-08-05
- Improved ADHD pattern detection
- Added comprehensive logging
- Enhanced timer system with audio alerts

### [1.1.0] - 2024-08-03
- Initial Docker support
- Added configuration management
- Implemented phase-based coaching system

### [1.0.0] - 2024-08-01
- Initial release
- Basic GTD review functionality
- LM Studio integration
- 30-minute time-boxed sessions