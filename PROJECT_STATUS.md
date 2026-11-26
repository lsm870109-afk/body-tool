# PROJECT STATUS

## Current progress
- STEP 01 — File structure and analysis environment: completed (prior analysis).
- STEP 02 — OTools feasibility verification: completed (prior analysis).
- STEP 03 — Skeleton structure reconstruction: completed for the two supplied LOD-B skeleton objects.
- STEP 04 — Before/after skeleton comparison: not started as a separate formal stage.

## Confirmed facts
- Both LOD-B files are ELF32 little-endian MIPS relocatable objects, 11,280 bytes each.
- `.data` starts at file offset 0x40 and has size 0x2010.
- Skeleton symbol is at .data + 0x400; header reports 64 bones.
- BoneState array begins at .data + 0x410; 64 records, 112 bytes each.
- Bone names map to zero-based indices through symbol value / 0x10.
- Parent IDs are stored in BoneState at +0x0C.
- OTools export.cpp struct layout: scale +0x00, parent +0x0C, quaternion +0x10, translation +0x20, inverse base transform +0x30.
- No SHT_REL/SHT_RELA relocation sections in these two objects.
- Parent hierarchy reconstructed with Hips as root.
- User's 1-based IDs: LowerSpine 28, MiddleSpine 29, UpperSpine 30.

## Preliminary comparison observations
- Parent IDs, scales, and quaternions: unchanged across files.
- Translation xyz changed in 44 bones.
- Inverse-base-transform changed in 63 bones.
- Hips unchanged; spine chain and both hand-ball snap bones have changed translation/matrix values.
- Formal interpretation and world-space comparison are reserved for STEP 04.

## Inputs
- `base_lodB_skeleton(수정전).o` (GitHub blob 7e9208263d59801676c09bda62243e667b11d152)
- `base_lodB_skeleton(수정후).o` (GitHub blob 665d9d5362f7baf4799f04a8d15e694c9886d8e8)

## Outputs
- `STEP03_SKELETON_ANALYSIS.md`
- `skeleton_before.csv`
- `skeleton_after.csv`

## Commands / methods
- Retrieved both files from the repository's main branch using GitHub Contents API.
- Parsed ELF section headers and symbol table.
- Cross-checked BoneState struct offsets against OTools export.cpp.
- Parsed all 64 BoneState records and compared field arrays.

## Errors / limitations
- Initial parsing attempt used incorrect tentative BoneState field offsets; corrected after cross-checking the OTools struct declaration.
- Matrix convention, coordinate system, and translation w semantics remain unverified.
- No original binary files were edited.

## Next exact task
- Begin STEP 04 only after user approval: formal before/after skeleton diff, local/world transform evaluation, and inverse-base-transform interpretation.

## Approval
- STEP 03 result reported to user; awaiting approval to proceed to STEP 04.
- No STEP 04 work authorized yet.
