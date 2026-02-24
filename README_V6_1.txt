AA STRUCTURAL READING PIPELINE — V6.1 FULL FIXED

What changed vs V5.6 FULL FIXED
- Deterministic anti-duplication conflict resolver for Arcana assignment:
  If the same Arcano is ranked #1 in multiple selected houses, the Arcano is assigned
  to the house where it is most decisive:
    decisivity = score(#1) - score(#2)
  Tie-breaks: higher score(#1), then lower house number.
- No change to scoring, clusters, house selection (v3.3), or orientation rules.
- Optional audit field: 'audit_conflict' is added only on rows where this resolver forced an assignment.

How to run (same as before)
- Use calc/aa_structural_reading_v5.py::compute(path) on a JSON_CU3 .txt file.

Tools
- tools/diff_v56_vs_v61.py: compare V5.6 vs V6.1 on a JSON batch.
