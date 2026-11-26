# STEP 05 — ORD/ORL Animation Structure Analysis (O.Tools Dump Scope)

## Scope and evidence
This step examines the animation object dump available in the repository:
- Input dump: `xmcpjump.txt` (header identifies source object as `xmcpjump.o`).
- OTools structure definitions: `OTools/dump.cpp` at commit `1442a59c43fc825915ac9f6ebadf4f54852a80bc`.
- The raw game `.ord` / `.orl` containers were not directly parsed in this step. Findings below describe the decoded object dump, not a complete archive/container specification.
- `xmcpdnk.txt` exists in the repository listing, but the GitHub file reader returned an empty body for this 1.9 MB file. Its detailed contents are therefore not included in the fresh counts below.

## 1. AnimationBank structure
The `xmcpjump` dump contains:
- AnimationBank address: `0x4D850`
- Size: 28 bytes
- NumAnimations: 779
- unknown1: 80
- unknown2: 532
- Animations array offset: `0x4BFF8`
- AnimationNames array offset: `0x4CC24`
- Stat: 0

The two arrays each contain 779 entries:
- `Animations`: offsets to named animation compound records.
- `AnimationNames`: name-offset entries, e.g. `BLKHITFALL1_ball`.

The array indices pair the animation name with its compound record. The compound's channel offsets then point to the lower-level payload records.

## 2. Animation compound record
The OTools `WriteAnimation` implementation identifies type 15 as `ANIM_COMPOUND` and reads:
1. Type: uint16
2. CheckSum: uint16
3. AttributeBlock: offset
4. NumChannels: uint16
5. NumFrames: uint16
6. ChannelOffset array: one offset per channel

In the dump:
- 779 / 779 named AnimationBank entries resolve to `ANIM_COMPOUND`.
- 607 compounds contain one channel.
- 172 compounds contain two channels.
- Total lower-level channel payload records referenced: 951.

This establishes a two-level representation: named compound animation entry -> one or more typed channel payload records.

## 3. Channel payload types observed
Across the 951 channel records referenced by the 779 compounds:

| Payload type | Count |
|---|---:|
| ANIM_DELTAF3 | 313 |
| ANIM_DELTAQFAST | 315 |
| ANIM_DELTAF1 | 151 |
| ANIM_RAWEVENT | 105 |
| ANIM_CSISEVENT | 67 |
| Total | 951 |

The dump labels these records by type, but most payload bodies are emitted as raw `Unknown [size]` byte blocks. OTools' `WriteAnimation` code does not decode the DELTAF3, DELTAF1, DELTAQFAST, RAWEVENT, or CSISevent payload contents into per-frame numeric samples in this dump path.

## 4. Ball and velocity tracks — confirmed structural finding
The name table contains:
- 105 entries ending in `_ball`.
- 105 entries ending in `_velocity`.

For all 105 `_ball` entries:
- The compound has one channel.
- Its payload type is `ANIM_DELTAF3`.
- Frame count range: 3–92 (average 20.1).

For the 105 `_velocity` entries:
- Each compound has one channel.
- 59 payloads are `ANIM_DELTAF3`.
- 46 payloads are `ANIM_DELTAF1`.
- Frame count range: 3–92 (average 20.1).

Examples include:
- `BLKHITFALL1_ball` — 92 frames, ANIM_DELTAF3.
- `BLKHITFALL1_velocity` — 92 frames, ANIM_DELTAF3.
- `BLKLAYBHNDSTUFF1_ball` — 20 frames, ANIM_DELTAF3.
- `BLKLAYBHNDSTUFF1_velocity` — 20 frames, ANIM_DELTAF1.

This proves that this bank stores separately named ball and velocity tracks, rather than representing every ball-related value only as part of the player's named limb channels. It does not yet establish whether the ball track is world-space, player-relative, hand-relative, or how the runtime blends it with the player skeleton.

## 5. Other named channels
The name table also contains 105 each of `_e`, `_facing`, `_l`, and `_t`, plus 149 `_r` entries.
Observed payload associations:
- `_facing`: ANIM_DELTAF1.
- `_l`: ANIM_DELTAQFAST.
- `_t`: ANIM_DELTAQFAST.
- `_e`: event payloads; 67 compounds have both RAWEVENT and CSISevent, while 38 have RAWEVENT only.
- `_r`: a mixture of ANIM_DELTAF3 and two-channel compounds containing ANIM_DELTAQFAST plus ANIM_DELTAF3.

The suffix meanings are not inferred here. In particular, `_l`, `_r`, and `_t` must not be assigned left/right/translation meanings without validating the game-specific channel schema.

## 6. What is and is not decoded
Confirmed:
- AnimationBank metadata and both 779-entry tables.
- The compound record field layout, based on OTools source.
- Compound channel counts, frame counts, channel offsets, and payload type labels.
- Existence and type of separately named `_ball` and `_velocity` tracks.

Not decoded:
- Numeric per-frame XYZ samples inside DELTAF3.
- Numeric per-frame scalar samples inside DELTAF1.
- Quaternion reconstruction inside DELTAQFAST.
- The event payload semantics.
- Coordinate space, units, interpolation rules, and timing semantics.
- How the runtime binds a named track to a specific skeleton bone or ball object.
- Raw `.ord` / `.orl` container layout and runtime loading behavior.

## 7. Relevance to the reported symptoms
The separately stored `_ball` tracks make the animation data a plausible independent source of ball position. Therefore, a modified skeleton and an unchanged ball trajectory could become misaligned during a dunk or shot. This is a testable hypothesis, not yet a proven cause.

The `_velocity` tracks also exist separately, but the dump does not yet tell us whether they are root/player motion, ball velocity, or another named channel. Do not assume they are the physics engine's final velocity.

No evidence in this step establishes that the game EXE physics engine must be changed.

## 8. Next step
STEP 06 should correlate:
1. The relevant compound names and channel payloads (especially ball and movement-related tracks).
2. The modified skeleton's hand and HandBallSnap positions.
3. The actual runtime animation and ball attachment behavior.

Before changing data, STEP 06 needs a decoder or a reliable reference implementation for DELTAF3 / DELTAF1 / DELTAQFAST, plus the missing detailed `xmcpdnk` dump or an equivalent accessible extraction.

## Safety
- No animation, skeleton, ORL/ORD, or EXE file was modified.
- This report records structural analysis only.
