---
name: spec-driven-development
description: 'Use for specification-first Python work, acceptance criteria definition, test planning, and keeping implementation aligned with docs/specification.md.'
argument-hint: 'Describe the feature or refactor to specify before coding'
user-invocable: true
---

# Spec-Driven Development

## When to Use
- Defining a new feature before implementation
- Turning requirements into acceptance checks
- Updating tests after a spec change

## Procedure
1. Read `docs/specification.md`.
2. Add or refine acceptance criteria for the requested behavior.
3. Add or update focused tests before implementation when practical.
4. Implement the smallest change that satisfies the updated spec.
5. Run the narrowest validation command and record the result.