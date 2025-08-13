# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in GTD Coach, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email the maintainer directly with details
3. Allow reasonable time for a fix before public disclosure

## API Key Management

### ⚠️ CRITICAL: Never Hardcode API Keys

This repository has strict policies against hardcoding API keys or secrets:

1. **All API keys MUST be stored in environment variables**
2. **Never commit `.env` files** (only `.env.example`)
3. **Use the provided `scripts/setup_env.py` to configure your environment**

### Required API Keys

- **Timing API Key**: Get from https://web.timingapp.com (requires Timing Connect subscription)
- **Todoist API Key**: Get from https://todoist.com/app/settings/integrations
- **Langfuse Keys** (optional): Get from https://cloud.langfuse.com
- **Neo4j Credentials** (optional): For Graphiti memory integration

### Setting Up API Keys Safely

```bash
# Method 1: Environment Variables
export TIMING_API_KEY="your-key-here"
export TODOIST_API_KEY="your-key-here"

# Method 2: Use .env file (never commit this!)
cp config/.env.example .env
# Edit .env with your keys

# Method 3: Use the setup script
python3 scripts/setup_env.py
```

## Security Measures

### 1. Pre-commit Hooks

We use multiple layers of pre-commit hooks to prevent accidental secret exposure:

```bash
# Install pre-commit hooks
brew install pre-commit
pre-commit install
```

The hooks will:
- Scan for secrets using `detect-secrets` and `gitleaks`
- Check for hardcoded API keys
- Prevent committing `.env` files
- Detect private keys

### 2. GitHub Actions Security Scanning

Every push and PR triggers:
- **Gitleaks**: Comprehensive secret scanning
- **TruffleHog**: Verified credential detection
- **Bandit**: Python security analysis
- **Safety**: Dependency vulnerability checks
- **CodeQL**: Advanced security analysis
- Custom API key pattern detection

### 3. Git History Protection

If you accidentally commit a secret:

1. **Immediately revoke the exposed key**
2. **Clean Git history**:
   ```bash
   # Install git-filter-repo
   brew install git-filter-repo
   
   # Create patterns file with the exposed secret
   echo "YOUR_EXPOSED_SECRET" > sensitive-patterns.txt
   
   # Clean history
   git filter-repo --replace-text sensitive-patterns.txt --force
   
   # Remove patterns file
   rm sensitive-patterns.txt
   ```
3. **Force push to remote** (coordinate with team)
4. **Contact GitHub support** for server-side cleanup

### 4. Development Best Practices

- **Always use environment variables** for sensitive data
- **Review diffs carefully** before committing
- **Use `.env.example`** to document required variables
- **Run tests** with mocked APIs when possible
- **Rotate keys regularly**
- **Use minimal permission scopes** for API keys

## Security Checklist for Contributors

Before submitting a PR:

- [ ] No hardcoded API keys or secrets
- [ ] No `.env` files included
- [ ] Pre-commit hooks pass
- [ ] Sensitive data uses environment variables
- [ ] Test files use mocked credentials
- [ ] Documentation doesn't contain real keys

## Incident Response

If a secret is exposed:

1. **Revoke immediately** - Disable the exposed credential
2. **Assess impact** - Check logs for unauthorized usage
3. **Clean repository** - Remove from history using git-filter-repo
4. **Rotate credentials** - Generate new keys
5. **Update systems** - Deploy new credentials
6. **Document incident** - Record what happened and lessons learned

## Security Tools Configuration

### detect-secrets

Baseline: `.secrets.baseline`
Update baseline: `detect-secrets scan --update .secrets.baseline`

### Gitleaks

Config: Automatic via GitHub Actions
Local scan: `gitleaks detect --source . -v`

### Bandit

Skip rules: B101 (assert), B601 (shell)
Run locally: `bandit -r gtd_coach/`

## Dependency Management

- Regular dependency updates via Dependabot
- Security advisories monitored via GitHub Security
- Use `safety check` to scan for vulnerabilities

## Contact

For security concerns, contact the repository maintainer directly rather than creating public issues.

---

*Last updated: 2025-08-13*
*Security incident addressed: Timing API key exposure (resolved)*