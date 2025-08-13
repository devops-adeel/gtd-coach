# Documentation Maintenance

## Documentation Standards

### Single Source of Truth
Each piece of information must exist in exactly ONE location. All other references should link to that location.

### Diátaxis Framework
Organize content by user needs:
- **Tutorial**: Learning-oriented (first-time users)
- **How-to**: Task-oriented (specific goals)
- **Reference**: Information-oriented (lookup)
- **Explanation**: Understanding-oriented (concepts)

### Writing Guidelines
- Keep sections under 100 lines
- Use clear headings and subheadings
- Include code examples where relevant
- Link to related documentation
- Avoid duplication

## Quarterly Review Process

Add to CHANGELOG.md each quarter:
```markdown
## Documentation Review - Q1 2025
- [ ] Remove outdated content
- [ ] Update integration guides
- [ ] Verify all links work
- [ ] Archive historical docs
- [ ] Update examples
```

## Adding New Features

When adding features, update:
1. Relevant how-to guide
2. Configuration reference if new settings
3. API reference if new endpoints
4. CHANGELOG.md with feature description

## Deprecation Process

1. Mark deprecated in documentation
2. Add deprecation warning in code
3. Document migration path
4. Remove after 2 releases

## Documentation Testing

### Link Checking
```bash
# Install markdown-link-check
npm install -g markdown-link-check

# Check all markdown files
find docs -name "*.md" -exec markdown-link-check {} \;
```

### Spell Checking
```bash
# Using aspell
find docs -name "*.md" -exec aspell check {} \;
```

## Documentation Metrics

Track in quarterly reviews:
- Total line count
- Number of files
- Broken links found
- User feedback items

Target: < 2,500 lines of active documentation