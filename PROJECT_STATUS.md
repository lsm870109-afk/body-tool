# PROJECT STATUS

## Current progress
- STEP 01 — File structure and analysis environment: completed.
- STEP 02 — OTools feasibility verification: completed.
- STEP 03 — Skeleton structure reconstruction: completed.
- STEP 04 — Formal before/after skeleton diff: completed.
- STEP 05 — ORD/ORL animation structure analysis (O.Tools dump scope): completed.
- STEP 06 — Animation and skeleton correlation: pending.

## STEP 05 confirmed findings
- An accessible `xmcpjump.txt` dump identifies source object `xmcpjump.o`.
- AnimationBank at 0x4D850: size 28, NumAnimations 779, Animations array at 0x4BFF8, AnimationNames at 0x4CC24.
- All 779 names pair with ANIM_COMPOUND records.
- 607 compounds have one channel; 172 have two channels; total 951 channel payload records.
- Payload type counts: ANIM_DELTAF3 313; ANIM_DELTAQFAST 315; ANIM_DELTAF1 151; ANIM_RAWEVENT 105; ANIM_CSISEVENT 67.
- There are 105 `_ball` tracks, all one-channel ANIM_DELTAF3; frame counts 3–92.
- There are 105 `_velocity` tracks, all one-channel; 59 ANIM_DELTAF3 and 46 ANIM_DELTAF1.
- OTools source defines the ANIM_COMPOUND header and channel-offset array, but does not decode these payloads into per-frame values in this dump path.
- `xmcpdnk.txt` is listed in the repo but could not be read by the current GitHub file reader (empty response); its detailed data remains unverified in this step.
- Raw .ord/.orl container parsing and runtime channel semantics remain unverified.

## STEP 05 outputs
- STEP05_ORD_ORL_ANALYSIS.md

## STEP 06 scope
Correlate the decoded animation channels with the edited skeleton, prioritizing ball tracks, HandBallSnap (37/44), and the reported dunk/shot alignment problems. First obtain or implement a reliable decoder for DELTAF3, DELTAF1, and DELTAQFAST, and restore access to the detailed xmcpdnk dump.

## Safety
No original game files, animation files, skeleton binaries, or EXE files were modified.
Awaiting user approval before STEP 06.
