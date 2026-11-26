# STEP 03 — Skeleton Structure Reconstruction

## Scope
Analyzed the two repository files directly; no source binary was modified.

- Before: `base_lodB_skeleton(수정전).o` (11,280 bytes; blob `7e9208263d59801676c09bda62243e667b11d152`)
- After: `base_lodB_skeleton(수정후).o` (11,280 bytes; blob `665d9d5362f7baf4799f04a8d15e694c9886d8e8`)

## Confirmed ELF layout
- ELF32, little-endian, MIPS, relocatable object.
- `.data`: file offset `0x40`, size `0x2010`.
- `__Skeleton:::Hips` symbol: section-relative value `0x400`.
- Skeleton header begins at file offset `0x440`; its 32-bit words are `0x02800007, 0, 64, 0`. The third word confirms 64 bones.
- BoneState array begins at `.data + 0x410` = file offset `0x450`.
- 64 BoneState records, stride `0x70` (112 bytes), ending at file offset `0x2050`, exactly at the end of `.data`.
- Bone names are supplied by `__Bone:::Hips.<BoneName>` symbols. Symbol values advance in `0x10` steps; dividing by `0x10` yields the zero-based bone index.
- No ELF relocation section (SHT_REL/SHT_RELA) is present in these two files. The parent links are direct integer bone IDs in each BoneState.

## Verified BoneState layout
Cross-checked against OTools `export.cpp` struct declaration and actual 112-byte records:
- `+0x00`: Vector3 scale
- `+0x0C`: int32 parent bone ID
- `+0x10`: Vector4 rotation quaternion
- `+0x20`: Vector4 translation (CSV records xyz; w retained for later validation)
- `+0x30`: 4x4 inverse-base-transform matrix (16 float32 values)

The earlier tentative offsets `parent +0x1C / quaternion +0x20 / translation +0x30` are incorrect for this struct. The validated offsets above are used in both CSVs.

## Reconstructed hierarchy
- Bone count: 64.
- Root: bone ID 1, Hips (parent = -1).
- Bone IDs in the CSV are 1-based to match the user's numbering. The symbol-derived index is zero-based.
- Relevant chain: Hips (1) -> LowerSpine (28) -> MiddleSpine (29) -> UpperSpine (30).
- Left hand chain: ... -> LHand (36) -> LHandBallSnap (37).
- Right hand chain: ... -> RHand (43) -> RHandBallSnap (44).

## Structural comparison (not the formal STEP 04 report)
A preliminary byte-level field comparison was performed to validate extraction:
- Parent IDs changed: 0 bones.
- Scale changed: 0 bones.
- Rotation quaternion changed: 0 bones.
- Translation xyz changed: 44 bones.
- Inverse-base-transform matrix changed: 63 bones.
- At least one of these fields changed: 63 bones.
- Hips (1) is unchanged.
- LowerSpine (28), MiddleSpine (29), and UpperSpine (30) have changed translation and inverse-base-transform values.
- Both hand-ball snap bones (37 and 44) have changed translation and inverse-base-transform values.

This preliminary comparison is included as a validation check for STEP 03. Full interpretation of local/world transforms and the cause/effect of edits belongs to STEP 04.

## Output files
- `skeleton_before.csv`
- `skeleton_after.csv`

Each CSV contains all 64 bones, parent ID/name, scale, quaternion, translation xyz, and the 16 inverse-base-transform values.

## Limitations / pending validation
- Translation w component is not included in the CSV; it is retained in the source binary and should be validated before assigning semantics.
- Matrix storage convention (row-major vs column-major), coordinate handedness, and exact local-to-world composition order have not yet been proven.
- The no-relocation finding applies to these two skeleton objects only; it does not generalize to all EA files.
- No glTF export/import was attempted in this step.
- No game executable, animation, or original skeleton data was modified.
