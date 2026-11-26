# STEP 04 — Formal Skeleton Before/After Diff

## Scope and inputs
This step compares the two STEP 03 extraction tables only. It does not modify either original binary.

- Before CSV: `skeleton_before.csv`
- After CSV: `skeleton_after.csv`
- Each table contains 64 bones.
- Comparison tolerance: absolute float difference greater than 1e-7.

## Executive result
The edit is not a uniform scale or rotation change:
- Bone count: 64 -> 64.
- Parent IDs changed: 0.
- Scale components changed: 0.
- Quaternion components changed: 0.
- Local translation xyz changed: 44 bones.
- Inverse-base-transform translation components (matrix entries 12–14) changed: 63 bones.
- Inverse-base-transform entries 0–11 and 15: unchanged in all 64 bones.
- Hips (bone 1) is unchanged.

This pattern indicates positional edits while preserving the stored local bone rotations, scales, and hierarchy. The inverse-base-transform changes extend beyond bones whose own local translation changed, consistent with ancestor movement being reflected in descendant bind-space transforms. The exact matrix convention and composition order remain unverified.

## Main edited spine chain
| Bone | Parent | Before translation (x,y,z) | After translation (x,y,z) | Delta (x,y,z) |
|---|---|---|---|---|
| LowerSpine (28) | Hips | (0.000000, 0.000000, 0.000000) | (-1.847966, 0.047765, 0.038508) | (-1.847966, 0.047765, 0.038508) |
| MiddleSpine (29) | LowerSpine | (0.543470, 0.000000, 0.000000) | (0.998707, 0.000617, -0.031557) | (0.455237, 0.000617, -0.031557) |
| UpperSpine (30) | MiddleSpine | (0.530838, 0.000000, 0.000000) | (0.930698, -0.035945, -0.018797) | (0.399860, -0.035945, -0.018797) |

The LowerSpine local X translation changes by about -1.848 units. MiddleSpine and UpperSpine local X translations increase by about +0.455 and +0.400 units respectively. This is not equivalent to simply lowering the spine along the vertical axis. Coordinate-axis meaning is not yet established, so these values must not be described as world-height changes.

## Arm and ball-snap observations
- LHand (36): translation delta (-0.255777, -0.054215, -0.014106).
- LHandBallSnap (37): translation delta (-0.045068, -0.006922, approximately 0).
- RHand (43): translation delta (-0.255777, -0.054216, +0.014104).
- RHandBallSnap (44): translation delta (-0.045068, -0.006922, approximately 0).

Both hand-ball snap nodes have been moved in their local translations. This is a concrete structural difference relevant to the reported ball-to-hand offset, but this diff alone cannot prove it causes the in-game ball attachment problem.

## What the inverse matrices tell us
For 63 bones, only matrix entries 12, 13, and 14 changed. The other 13 entries are unchanged. This is consistent with a translation-only change in the inverse bind/base transform, while its 3x3 linear portion remains the same. Some descendants (including Head and facial bones) have changed inverse-matrix translation despite unchanged local translation, which is consistent with inherited parent-space changes.

Do not yet label entries 12–14 as a specific row or column, or infer world coordinates: row-major/column-major layout, handedness, and multiplication order have not been independently validated.

## Interpretation and limits
1. The binary edit preserved skeleton topology, local scale, and local rotation.
2. The modified local translations affect more than the two spine nodes; 44 bones have local translation changes, including legs, arms, and spine.
3. Both hand-ball snap nodes moved relative to their parents in their stored local translation values.
4. The inverse-base-transform translation terms were updated broadly, likely to keep inverse bind/base transforms coherent with the changed hierarchy. This is a strong structural interpretation, not a fully proven runtime behavior.
5. This analysis does not establish jump height, animation retargeting, ball attachment runtime behavior, or whether the game EXE physics must be changed. Those require STEP 05–07 evidence.

## Output
- `STEP04_SKELETON_DIFF.md`: this report.
- `skeleton_diff.csv`: per-bone before/after local translations and inverse-matrix translation terms for every changed bone.
- `PROJECT_STATUS.md`: updated to mark STEP 04 complete and STEP 05 pending.

## Validation notes
- Inputs and CSV extraction were re-fetched from GitHub main during this step.
- CSV rows were matched by bone ID and name.
- Float differences use a 1e-7 threshold.
- No binary was edited or replaced.
