# PROJECT STATUS

## Current progress
- STEP 01 — File structure and analysis environment: completed.
- STEP 02 — OTools feasibility verification: completed.
- STEP 03 — Skeleton structure reconstruction: completed.
- STEP 04 — Formal before/after skeleton diff: completed.
- STEP 05 — ORD/ORL structure analysis: not started as the next official stage.

## STEP 04 confirmed findings
- Compared all 64 bones from skeleton_before.csv and skeleton_after.csv.
- Parent IDs changed: 0.
- Scale changed: 0.
- Quaternion changed: 0.
- Local translation xyz changed: 44 bones.
- Inverse-base-transform entries 12–14 changed: 63 bones.
- Inverse-base-transform entries 0–11 and 15 unchanged.
- Hips (1) unchanged.
- LowerSpine (28), MiddleSpine (29), UpperSpine (30) local translation changes are recorded in STEP04_SKELETON_DIFF.md.
- LHandBallSnap (37) and RHandBallSnap (44) both have local translation changes.
- Descendant inverse-matrix translation terms changed even where local translation did not, consistent with inherited parent-space movement.

## STEP 04 interpretation limits
- Matrix storage convention and multiplication order not independently proven.
- Coordinate axes/handedness not established; do not call X/Y/Z a particular world direction.
- No conclusion yet about animation data, in-game jump height, ball attachment runtime behavior, or EXE physics.
- No source binary was modified.

## Outputs
- STEP03_SKELETON_ANALYSIS.md
- skeleton_before.csv
- skeleton_after.csv
- STEP04_SKELETON_DIFF.md
- skeleton_diff.csv
- PROJECT_STATUS.md

## Next exact task
- STEP 05 — ORD/ORL structure analysis, beginning with the relevant animation files and channel payload structure. Correlate skeleton bone changes with animation data only after parsing the ORD/ORL representation.

## Approval
- STEP 04 report saved and presented.
- Awaiting user approval before STEP 05.
