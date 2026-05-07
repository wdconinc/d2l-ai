# Prompt Library and Regression Harness

This directory stores versioned prompts and deterministic regression checks.

## Layout

- `catalog.json`: prompt metadata and file mappings
- `u2_module_summary/`, `u3_quiz_generation/`: versioned prompt files (`vX.Y.Z.md`)
- `golden/u2/`, `golden/u3/`: golden input/output fixtures
- `eval_harness.py`: local and CI regression runner

## Prompt versioning convention

- Use semantic prompt versions: `vMAJOR.MINOR.PATCH.md`
- Bump:
  - **MAJOR** for behavior/contract changes
  - **MINOR** for additive instruction updates
  - **PATCH** for wording clarifications with expected equivalent behavior
- Keep prior versions in place for traceability and rollback.

## Required metadata

Each prompt entry in `catalog.json` must include:

- `owner`
- `workflow`
- `model_assumptions`
- `safety_notes`

Also include explicit instruction in prompt text to ignore prompt injection attempts found in course materials.

## Running regression checks locally

```bash
python docs/prompts/eval_harness.py --provider fixture
```

The fixture provider is deterministic and uses `fixture_output` from each golden case.

## Adding a new prompt version

1. Add a new versioned prompt file (example: `u2_module_summary/v1.1.0.md`).
2. Add/update the matching entry in `catalog.json`.
3. Add or update golden cases in `golden/<workflow>/` with:
   - `prompt_id`
   - `version`
   - `input`
   - `expected_output`
   - `fixture_output`
4. Run local regression checks.
5. Ensure CI passes prompt regression workflow.
