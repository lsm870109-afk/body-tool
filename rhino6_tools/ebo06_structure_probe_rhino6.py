# -*- coding: utf-8 -*-
"""
NBA Live 06 EBO read-only structure probe
Rhino 6 / IronPython 2.7 compatible.
Select a base EBO and a character/morph EBO. This script NEVER writes files.
All offsets are reported as observations, not assumed format definitions.
"""
import rhinoscriptsyntax as rs
import struct
import os

def u16(data, off):
    if off < 0 or off + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, off)[0]

def u32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, off)[0]

def f32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, off)[0]

def hx(value):
    if value is None:
        return "None"
    return "0x%08X (%d)" % (value, value)

def hexdump(data, start, count):
    end = min(len(data), start + count)
    pos = start
    while pos < end:
        chunk = data[pos:min(pos + 16, end)]
        hs = " ".join(["%02X" % ord(c) for c in chunk])
        asc = "".join([c if 32 <= ord(c) < 127 else "." for c in chunk])
        print("%08X  %-47s  %s" % (pos, hs, asc))
        pos += 16

def read_file(path):
    f = open(path, "rb")
    try:
        return f.read()
    finally:
        f.close()

def header_report(label, path, data):
    size = len(data)
    print("")
    print("=" * 72)
    print("FILE: %s" % label)
    print("PATH: %s" % path)
    print("SIZE: %d bytes (%s)" % (size, hx(size)))
    print("MAGIC: %s" % repr(data[:4]))
    if data[:4] != "EBO\x00":
        print("WARNING: first four bytes are not EBO\\0")
    print("")
    print("-- HEADER BYTES 0x00..0xBF --")
    hexdump(data, 0, 0xC0)
    print("")
    print("-- LITTLE-ENDIAN HEADER WORDS --")
    for off in range(0, min(0x80, size - 3), 4):
        print("0x%04X : %s" % (off, hx(u32(data, off))))
    print("")
    print("-- SELECTED 16-BIT FIELDS --")
    for off in range(0x20, min(0x50, size - 1), 2):
        print("0x%04X : 0x%04X (%d)" % (off, u16(data, off), u16(data, off)))
    print("")
    print("-- ALIGNED WORDS THAT LOOK LIKE FILE OFFSETS --")
    found = []
    for off in range(4, min(0x100, size - 3), 4):
        val = u32(data, off)
        if val is not None and 0x40 <= val < size:
            found.append((off, val))
    if found:
        for off, val in found:
            print("field 0x%04X -> %s" % (off, hx(val)))
    else:
        print("(none in first 0x100 bytes)")
    print("")
    print("-- CANDIDATE 573 x XYZ FLOAT BLOCK --")
    candidate = 0x1BC
    byte_count = 573 * 3 * 4
    if candidate + byte_count <= size:
        vals = struct.unpack_from("<%df" % (573 * 3), data, candidate)
        finite = True
        for v in vals:
            if v != v or abs(v) > 1.0e20:
                finite = False
                break
        print("offset=%s length=%d (%s)" % (hx(candidate), byte_count, hx(byte_count)))
        print("finite/plausible-float-test=%s" % finite)
        if finite:
            xs = vals[0::3]
            ys = vals[1::3]
            zs = vals[2::3]
            print("X %.7f .. %.7f" % (min(xs), max(xs)))
            print("Y %.7f .. %.7f" % (min(ys), max(ys)))
            print("Z %.7f .. %.7f" % (min(zs), max(zs)))
            print("NOTE: presence and finite values do NOT prove this is a vertex stream.")
    else:
        print("not enough bytes for 573 XYZ values at 0x1BC")
    print("")
    print("-- FLOAT TRIPLES AT SELECTED OFFSETS (DIAGNOSTIC ONLY) --")
    for off in (0x40, 0x60, 0x80, 0xA0, 0xC0, 0x100, 0x180, 0x1BC):
        if off + 12 <= size:
            a, b, c = struct.unpack_from("<3f", data, off)
            print("0x%04X : (% .6g, % .6g, % .6g)" % (off, a, b, c))

def compare_files(a_label, a_path, a, b_label, b_path, b):
    print("")
    print("=" * 72)
    print("PAIR COMPARISON")
    print("%s : %d bytes" % (a_label, len(a)))
    print("%s : %d bytes" % (b_label, len(b)))
    print("")
    common = min(len(a), len(b))
    first = None
    diff_count = 0
    for i in range(common):
        if a[i] != b[i]:
            diff_count += 1
            if first is None:
                first = i
    print("Common byte span: %d" % common)
    print("Different byte positions in common span: %d" % diff_count)
    if first is None:
        print("First difference: none")
    else:
        print("First difference: 0x%X" % first)
        lo = max(0, first - 16)
        print("-- BASE AROUND FIRST DIFFERENCE --")
        hexdump(a, lo, 64)
        print("-- FILE B AROUND FIRST DIFFERENCE --")
        hexdump(b, lo, 64)
    print("")
    print("-- SAME-OFFSET HEADER WORD COMPARISON (0x00..0x7F) --")
    for off in range(0, min(0x80, common - 3), 4):
        av = u32(a, off)
        bv = u32(b, off)
        if av != bv:
            print("0x%04X : A=%s  B=%s" % (off, hx(av), hx(bv)))
    print("")
    print("-- IDENTICAL RUNS IN FIRST 0x300 BYTES --")
    run_start = None
    runs = []
    for i in range(min(0x300, common)):
        same = a[i] == b[i]
        if same and run_start is None:
            run_start = i
        if (not same or i == min(0x300, common) - 1) and run_start is not None:
            end = i if not same else i + 1
            if end - run_start >= 4:
                runs.append((run_start, end - run_start))
            run_start = None
    for off, length in runs:
        print("0x%04X length %d" % (off, length))
    print("NOTE: binary similarity alone does not identify semantic chunks.")

def main():
    print("NBA Live 06 EBO STRUCTURE PROBE - READ ONLY")
    base_path = rs.OpenFileName("Select NBA Live 06 base EBO", "EBO files (*.ebo)|*.ebo||")
    if not base_path:
        print("Cancelled.")
        return
    morph_path = rs.OpenFileName("Select NBA Live 06 character/morph EBO", "EBO files (*.ebo)|*.ebo||")
    if not morph_path:
        print("Cancelled.")
        return
    try:
        base = read_file(base_path)
        morph = read_file(morph_path)
    except Exception as e:
        print("READ ERROR: %s" % str(e))
        return
    header_report("BASE EBO", base_path, base)
    header_report("CHARACTER / MORPH EBO", morph_path, morph)
    compare_files("BASE", base_path, base, "CHARACTER/MORPH", morph_path, morph)
    print("")
    print("=" * 72)
    print("READ-ONLY inspection finished. No source file was changed.")
    print("Copy the complete Rhino command history (F2) for analysis.")

if __name__ == "__main__":
    main()
