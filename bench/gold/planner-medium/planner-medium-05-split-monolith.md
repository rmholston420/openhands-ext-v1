# planner-medium-05-split-monolith

## Task summary
Plan the extraction of an in-repo `email_service` module (currently 800 lines in `src/services/email.py`) into a separate installable Python package `company-email-service`, keeping the existing repo's imports working via the new package as a dependency.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Create a new git repository company-email-service with the standard Python package layout (pyproject.toml, src/company_email_service/, tests/, README).", "deps": []},
    {"id": "s2", "desc": "Move src/services/email.py to the new repo as src/company_email_service/__init__.py or a submodule; move associated tests.", "deps": ["s1"]},
    {"id": "s3", "desc": "Publish the new package to the internal PyPI (or use editable install for local dev) with a specific version tag like 0.1.0.", "deps": ["s2"]},
    {"id": "s4", "desc": "In the original repo, add company-email-service to pyproject.toml/requirements as a pinned dependency; delete src/services/email.py.", "deps": ["s3"]},
    {"id": "s5", "desc": "Update all import statements from 'from services.email import ...' to 'from company_email_service import ...' across the codebase.", "deps": ["s4"]},
    {"id": "s6", "desc": "Run the full test suite in the original repo to confirm imports resolve and behavior is unchanged; run tests in the new repo to confirm package correctness.", "deps": ["s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps: new repo scaffold → move code → publish → depend → update imports → test. DAG dependencies correct (publish before depend; depend before import updates). |
| 70-89 | Correct sequence but combines publish with depend (missing the explicit publish gate — package must exist on the index before it can be depended on). |
| 40-69 | Covers moves and imports but no explicit publish step (assumes editable install; not portable). |
| 10-39 | Deletes original file before ensuring package is available — leaves repo in broken state. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's handling of a cross-repo dependency-graph task. Key discriminator: does the plan sequence "publish new package" before "add as dependency"? Getting this backwards is a common junior mistake.
