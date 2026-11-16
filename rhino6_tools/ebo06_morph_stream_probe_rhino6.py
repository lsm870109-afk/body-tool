# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe - READ ONLY
# Rhino 6 / IronPython 2.7
#
# Purpose:
#   Inspect the metadata immediately before the known 573 * Float3 candidate
#   in a character EBO. This script does NOT modify the source file.
#
# Command: EBO06_MORPH_STREAM_PROBE
#
# IMPORTANT:
#   0x1BC is a confirmed finite 573*3 float candidate for the supplied
#   damilicB.ebo sample only. Its exact semantic meaning is not assumed here.

import struct
import os
import rhinoscriptsyntax as rs

def u16(data, off):
    if off < 0 or off + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, off)[0]

def u32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, off)[0]

def i32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, off)[0]

def f32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, off)[0]

def hx(v):
    if v is None:
        return "----"
    return "0x%08X" % (v & 0xFFFFFFFF)

def printable_ascii(raw):
    out = []
    for b in bytearray(raw):
        if 32 <= b <= 126:
            out.append(chr(b))
        else:
            out.append(".")
    return "".join(out)

def dump_words(data, start, end, title):
    print("")
    print("-- %s (4-byte words) --" % title)
    off = start
    while off + 4 <= min(end, len(data)):
        iv = u32(data, off)
        fv = f32(data, off)
        print("0x%04X  u32=%10u  i32=%11d  f32=% .9g  hex=%s" %
              (off, iv, i32(data, off), fv, hx(iv)))
        off += 4

def dump_bytes(data, start, length, title):
    end = min(len(data), start + length)
    print("")
    print("-- %s start=0x%X length=0x%X --" %
          (title, start, max(0, end-start)))
    off = start
    while off < end:
        chunk = data[off:min(off+16, end)]
        hexpart = " ".join(["%02X" % b for b in bytearray(chunk)])
        print("%08X  %-47s  %s" %
              (off, hexpart, printable_ascii(chunk)))
        off += 16

def scan_strings(data, start, end, min_len):
    found = []
    i = start
    end = min(end, len(data))
    while i < end:
        if 32 <= data[i] <= 126:
            j = i
            while j < end and 32 <= data[j] <= 126:
                j += 1
            if j - i >= min_len:
                found.append((i, data[i:j]))
            i = j + 1
        else:
            i += 1
    return found

def inspect(path):
    f = open(path, "rb")
    try:
        data = f.read()
    finally:
        f.close()

    size = len(data)
    print("")
    print("=" * 76)
    print("NBA LIVE 06 MORPH STREAM PROBE - READ ONLY")
    print("FILE: %s" % path)
    print("SIZE: %d bytes / 0x%X" % (size, size))

    if size < 0x40 or data[:4] != "EBO\x00":
        print("ERROR: Not a recognized EBO header.")
        return

    print("MAGIC=%r VERSION=%d SIZE_FIELD=%d" %
          (data[:4], u32(data, 4), u32(data, 8)))

    print("")
    print("-- HEADER --")
    for off in (0x10, 0x14, 0x18, 0x1C, 0x20):
        v = u32(data, off)
        state = "IN FILE" if v is not None and v < size else "OUTSIDE"
        print("field 0x%02X -> 0x%X (%d) %s" % (off, v, v, state))

    # Descriptor and morph metadata from the supplied character sample.
    dump_bytes(data, 0x60, 0x160, "DESCRIPTOR / MORPH METADATA AREA")
    dump_words(data, 0xE0, 0x1BC, "METADATA WORD INTERPRETATION")

    # The sample's candidate coordinate array starts at 0x1BC.
    candidate_start = 0x1BC
    candidate_count = 573
    candidate_bytes = candidate_count * 3 * 4
    candidate_end = candidate_start + candidate_bytes
    print("")
    print("-- 573 x Float3 CANDIDATE --")
    print("start=0x%X bytes=%d (0x%X) end=0x%X file_size=0x%X" %
          (candidate_start, candidate_bytes, candidate_bytes,
           candidate_end, size))
    if candidate_end <= size:
        finite_count = 0
        mins = [None, None, None]
        maxs = [None, None, None]
        for n in range(candidate_count):
            for c in range(3):
                v = f32(data, candidate_start + (n*3+c)*4)
                if v == v and abs(v) < 1.0e20:
                    finite_count += 1
                    if mins[c] is None or v < mins[c]:
                        mins[c] = v
                    if maxs[c] is None or v > maxs[c]:
                        maxs[c] = v
        print("finite components=%d / %d" %
              (finite_count, candidate_count*3))
        for c, label in enumerate(("X", "Y", "Z")):
            print("%s range: % .9g .. % .9g" %
                  (label, mins[c], maxs[c]))
        print("first 12 Float3 records:")
        for n in range(12):
            off = candidate_start + n*12
            a = f32(data, off)
            b = f32(data, off+4)
            c = f32(data, off+8)
            print("  #%03d @0x%04X  % .9g  % .9g  % .9g" %
                  (n, off, a, b, c))
        print("last 4 Float3 records:")
        for n in range(candidate_count-4, candidate_count):
            off = candidate_start + n*12
            a = f32(data, off)
            b = f32(data, off+4)
            c = f32(data, off+8)
            print("  #%03d @0x%04X  % .9g  % .9g  % .9g" %
                  (n, off, a, b, c))
    else:
        print("Candidate range exceeds file; sample layout does not apply.")

    # Show the tail where this sample stores the Morph type/name strings.
    strings = scan_strings(data, max(0, size-0x500), size, 3)
    print("")
    print("-- PRINTABLE STRINGS IN FINAL 0x500 BYTES --")
    for off, raw in strings:
        try:
            s = raw.decode("ascii")
        except:
            s = repr(raw)
        print("0x%04X  %s" % (off, s))

    # Inspect the region between candidate data and tail metadata.
    if candidate_end < size:
        dump_bytes(data, candidate_end, min(0x100, size-candidate_end),
                   "BYTES IMMEDIATELY AFTER 573 x Float3 CANDIDATE")

    print("")
    print("READ ONLY complete. No file was changed.")
    print("=" * 76)

def main():
    path = rs.OpenFileName("Select NBA Live 06 character EBO",
                           "EBO files (*.ebo)|*.ebo||")
    if not path:
        print("Cancelled.")
        return
    try:
        inspect(path)
    except Exception as e:
        print("PROBE ERROR: %s" % str(e))
        raise

if __name__ == "__main__":
    main()
