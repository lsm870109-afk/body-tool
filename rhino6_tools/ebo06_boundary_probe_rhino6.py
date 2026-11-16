# -*- coding: utf-8 -*-
"""
NBA Live 06 EBO boundary/table probe
Rhino 6 / IronPython 2.7 compatible. READ ONLY.
Select base_lodB.ebo and damilicB.ebo.
Dumps descriptor-like area and regions referenced by header offsets.
Does not assume these are confirmed chunks.
"""
import rhinoscriptsyntax as rs
import struct

def u32(d, o):
    if o < 0 or o + 4 > len(d): return None
    return struct.unpack_from("<I", d, o)[0]

def u16(d, o):
    if o < 0 or o + 2 > len(d): return None
    return struct.unpack_from("<H", d, o)[0]

def dump(d, start, length, title):
    print("")
    print("-- %s start=0x%X length=0x%X --" % (title, start, length))
    if start < 0 or start >= len(d):
        print("OUT OF RANGE")
        return
    end = min(len(d), start + length)
    p = start
    while p < end:
        b = d[p:min(p+16, end)]
        h = " ".join(["%02X" % ord(x) for x in b])
        a = "".join([x if 32 <= ord(x) < 127 else "." for x in b])
        print("%08X  %-47s  %s" % (p, h, a))
        p += 16

def analyze(path, label):
    f = open(path, "rb")
    try: d = f.read()
    finally: f.close()
    n = len(d)
    print("")
    print("=" * 76)
    print("%s : %s (%d bytes / 0x%X)" % (label, path, n, n))
    print("magic=%r version=%s size_field=%s" %
          (d[:4], u32(d,4), u32(d,8)))
    print("Header offsets:")
    refs = []
    for off in (0x10,0x14,0x18,0x1C,0x20):
        v = u32(d,off)
        print("  field 0x%02X -> 0x%X (%d) %s" %
              (off,v,v,"IN FILE" if v < n else "OUTSIDE"))
        if v is not None and 0x60 <= v < n:
            refs.append((off,v))
    dump(d, 0x60, min(0x2A0, n-0x60), "DESCRIPTOR AREA 0x60..")
    # Print likely 16-byte records without assigning semantic meaning.
    print("")
    print("-- 16-BYTE RECORD VIEW (RAW DWORDS), 0x60..0x1FF --")
    for off in range(0x60, min(0x200, n-15), 16):
        vals = [u32(d,off+i) for i in (0,4,8,12)]
        print("0x%04X : %08X %08X %08X %08X" %
              (off, vals[0], vals[1], vals[2], vals[3]))
    # Header-referenced regions and nearby boundaries.
    seen = set()
    for field, v in refs:
        base = max(0, v-0x30)
        key = base
        if key not in seen:
            seen.add(key)
            dump(d, base, 0x90, "AROUND HEADER POINTER field=0x%X value=0x%X" % (field,v))
    # Last 0x300 bytes are important because header pointers cluster near EOF.
    dump(d, max(0,n-0x300), min(0x300,n), "FINAL 0x300 BYTES")
    # 0x1BC candidate is shown as bytes and floats, but not classified.
    if 0x1BC+6876 <= n:
        vals = struct.unpack_from("<%df" % 1719, d, 0x1BC)
        good = all([(x == x and abs(x) < 1.0e10) for x in vals])
        print("")
        print("0x1BC / 6876-byte candidate: finite=%s" % good)
        if good:
            xyz = [vals[0::3], vals[1::3], vals[2::3]]
            print("candidate XYZ ranges:")
            for axis, arr in zip(("X","Y","Z"),xyz):
                print("  %s: %.7g .. %.7g" % (axis,min(arr),max(arr)))
    return d

def main():
    print("NBA LIVE 06 EBO BOUNDARY PROBE - READ ONLY")
    p1 = rs.OpenFileName("Select base_lodB.ebo", "EBO files (*.ebo)|*.ebo||")
    if not p1: return
    p2 = rs.OpenFileName("Select damilicB.ebo", "EBO files (*.ebo)|*.ebo||")
    if not p2: return
    try:
        analyze(p1, "BASE EBO")
        analyze(p2, "CHARACTER EBO")
    except Exception as e:
        print("ERROR: %s" % str(e))
    print("")
    print("=" * 76)
    print("READ ONLY complete. No file was changed. Copy Rhino command history with F2.")

if __name__ == "__main__":
    main()
