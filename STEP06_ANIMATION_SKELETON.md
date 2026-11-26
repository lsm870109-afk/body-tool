# STEP 06 — Animation and Skeleton Correlation

## Scope
This step correlates the accessible `xmcpjump.txt` dump (source object `xmcpjump.o`) with the modified NBA Live 06 skeleton reconstructed in STEP03/STEP04. It does not modify game assets or executables.

## 1. Evidence inspected
- `xmcpjump.txt` was fetched successfully from the project repository (687,511 characters).
- OTools source `OTools/dump.cpp` at commit `1442a59c43fc825915ac9f6ebadf4f54852a80bc` was inspected.
- STEP03/STEP04 skeleton tables and reports were used for bone IDs and before/after changes.
- `xmcpdnk.txt` exists in the repository and has blob SHA `0dd422672a5e23f67fbd5fae990d33ce60a6bbde`, but GitHub file retrieval returned an empty body, including a line-range request. Its contents could not be inspected in this step.

## 2. Confirmed jump-bank track mappings
The AnimationNames and Animations arrays use matching indices. For selected tracks:

| Track name | Name index | Compound offset | Channels | Frames | Payload type |
|---|---:|---:|---:|---:|---|
| BLKHITFALL1_ball | 0 | 0x421C | 1 | 92 | ANIM_DELTAF3 |
| BLKHITFALL1_velocity | 6 | 0x62D8 | 1 | 92 | ANIM_DELTAF3 |
| BLKLAYBHNDSTUFF1_ball | 56 | 0xB64C | 1 | 20 | ANIM_DELTAF3 |
| BLKLAYBHNDSTUFF1_velocity | 62 | 0xC124 | 1 | 20 | ANIM_DELTAF1 |

These are direct observations from the dump's name table, offset array, compound headers and channel records.

## 3. What can be correlated with the skeleton
STEP03/STEP04 established the relevant skeleton IDs:
- LHand = 36; LHandBallSnap = 37
- RHand = 43; RHandBallSnap = 44
- LowerSpine = 28; MiddleSpine = 29; UpperSpine = 30

The jump dump exposes named `_ball` and `_velocity` tracks as separate animation-bank entries. The selected examples show that the ball and velocity tracks can have the same compound frame count while using different payload types (for example, 20-frame layup-stuff tracks use DELTAF3 for `_ball` and DELTAF1 for `_velocity`).

However, the dump does not expose a verified mapping from these named tracks to bone IDs 37/44, nor does it establish whether ball coordinates are world-space, player-root-relative, hand-relative, or transformed by a runtime attachment rule. The strings `_ball` and `_velocity` alone are not sufficient to decide this.

## 4. Decoder / runtime limitations
- OTools `WriteAnimation` identifies animation types and compound headers, but for the selected DELTAF3/DELTAF1 records the dump writer emits the payload as `Unknown [size]` raw bytes rather than decoded per-frame values.
- The inspected OTools README explicitly lists animation support as not implemented. This agrees with the source-level limitation observed here. See: https://github.com/FIFAM-Mods/otools
- No validated decoder for this EA animation payload family was found in the inspected OTools source or the project files.
- The available `xmcpjump.o` dump is not a dunk animation bank: its name table contains blocking/layup-stuff examples, but no DUNK/DNK/JUMP/SHOT-named entries. Therefore it cannot directly explain the user's specific dunk-to-rim failure.
- `xmcpdnk.txt` could not be read by the available GitHub file retrieval path, so dunk-specific track names and frame data remain unavailable.

## 5. Conclusions
### Confirmed
1. The animation bank contains independently named `_ball` and `_velocity` tracks.
2. These tracks are separate from the reconstructed skeleton table in the dump structure; no explicit bone-ID binding to HandBallSnap 37/44 was established.
3. The accessible jump dump gives compound offsets, channel counts, frame counts and payload type identifiers for selected ball/velocity tracks.
4. The skeleton edit changed the hand-ball-snap translations (STEP04), while the animation bank contains separate ball tracks. This makes a mismatch between edited hand attachment geometry and independently animated ball motion a testable hypothesis, not a proven cause.

### Not established
- Decoded ball position values or trajectory.
- Coordinate system, units, handedness, transform order or reference frame for the ball tracks.
- Runtime binding of ball tracks to hand/snap bones.
- Whether animation, skeleton, ball attachment logic or EXE physics causes the reported offset.
- Dunk-specific animation behavior.

## 6. Next required evidence
To complete the correlation without guessing:
1. Obtain a readable `xmcpdnk.txt` dump (or the original `xmcpdnk.o` / relevant animation asset) through a path that preserves its contents.
2. Obtain the DELTAF3/DELTAF1 payload specification or a decoder validated against multiple known tracks.
3. Decode the ball path and compare it with the animated hand/snap world transform using the game's actual transform convention.
4. Only after that, determine whether the correction belongs in animation data, skeleton/attachment alignment, or game runtime logic.

## Safety of changes
No original .o/.ord/.orl file, game executable, skeleton binary or animation payload was modified.
