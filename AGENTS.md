# TypeSafe Code Guard Rules
- **Semantic Code Search**: Always call `typesafe_find_code` with a behavioral description (what the code *does*, not literal keywords) before grepping or reading multiple files.
- **Diff Sanity Check**: Call `typesafe_audit_diff` before finishing edits to verify scope alignment and catch removed defensive checks or leftover debug statements.
- For query formulation examples and metric thresholds, activate the `typesafe-code-guard` skill.
