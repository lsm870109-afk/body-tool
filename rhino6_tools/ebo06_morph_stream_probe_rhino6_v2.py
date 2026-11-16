# -*- coding: utf-8 -*-
# NBA Live 06 Morph Stream Probe V2 - READ ONLY
# Rhino 6 / IronPython 2.7
#
# This is a fresh implementation. It does NOT use bytearray,
# FileStream.Read(), or struct.unpack_from().
# It does NOT modify the selected EBO file.

import struct
from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File

def read_bytes(path):
    # Returns a CLR System.Byte[].
    return File.ReadAllBytes(path)

def raw_string(data, offset, count):
    # Convert only the requested bytes to a Python 2 byte string.
    return ''.join(chr(int(data[offset + i])) for i in range(count))

def u16(data, off):
    if off < 0 or off + 2 > len(data):
        return None
    return struct.unpack("<H", raw_string(data, off, 2))[0]

def u32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack("<I", raw_string(data, off, 4))[0]

def i32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack("<i", raw_string(data, off, 4))[0]

def f32(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack("<f", raw_string(data, off, 4))[0]

def hx(v):
    if v is None:
        return "----"
    return "0x%08X" % (v & 0xFFFFFFFF)

def ascii_view(data, start, count):
    end = min(len(data), start + count)
    chars = []
    for i in range(start, end):
        b = int(data[i])
        chars.append(chr(b) if 32 <= b <= 126 else ".")
    return ''.join(chars)

def dump_bytes(data, start, count, title):
    end = min(len(data), start + count)
    print("")
    print("-- %s start=0x%X length=0x%X --" %
          (title, start, max(0, end-start)))
    off = start
    while off < end:
        n = min(16, end-off)
        vals = ["%02X" % int(data[off+j]) for j in range(n)]
        print("%08X  %-47s  %s" %
              (off, " ".join(vals), ascii_view(data, off, n)))
        off += n

def dump_words(data, start, end, title):
    print("")
    print("-- %s --" % title)
    off = start
    while off + 4 <= min(end, len(data)):
        iv = u32(data, off)
        fv = f32(data, off)
        print("0x%04X  u32=%10u  i32=%11d  f32=% .9g  hex=%s" %
              (off, iv, i32(data, off), fv, hx(iv)))
        off += 4

def find_strings(data, start, end, min_len):
    found = []
    i = start
    end = min(end, len(data))
    while i < end:
        if 32 <= int(data[i]) <= 126:
            j = i
            while j < end and 32 <= int(data[j]) <= 126:
                j += 1
            if j - i >= min_len:
                found.append((i, ascii_view(data, i, j-i)))
            i = j + 1
        else:
            i += 1
    return found

def inspect(path):
    data = read_bytes(path)
    size = len(data)

    print("")
    print("=" * 76)
    print("NBA LIVE 06 MORPH STREAM PROBE V2 - READ ONLY")
    print("FILE: %s" % str(path))
    print("SIZE: %d bytes / 0x%X" % (size, size))

    if size < 0x40:
        print("ERROR: File is too small for an EBO header.")
        return

    magic = raw_string(data, 0, 4)
    if tuple(int(data[i]) for i in range(4)) != (69, 66, 79, 0):
        print("ERROR: Not a recognized EBO header. First bytes: %s" %
              " ".join("%02X" % int(data[i]) for i in range(4)))
        return

    print("MAGIC bytes OK VERSION=%d SIZE_FIELD=%d" % (u32(data, 4), u32(data, 8)))
          (u32(data, 4), u32(data, 8)))

    print("")
    print("-- HEADER POINTERS --")
    for off in (0x10, 0x14, 0x18, 0x1C, 0x20):
        v = u32(data, off)
        state = "IN FILE" if v is not None and v < size else "OUTSIDE"
        print("field 0x%02X -> 0x%X (%d) %s" % (off, v, v, state))

    dump_bytes(data, 0x60, 0x160, "DESCRIPTOR / MORPH METADATA AREA")
    dump_words(data, 0xE0, 0x1BC, "METADATA WORD INTERPRETATION")

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
            print("  #%03d @0x%04X  % .9g  % .9g  % .9g" %
                  (n, off, f32(data, off), f32(data, off+4),
                   f32(data, off+8)))
        print("last 4 Float3 records:")
        for n in range(candidate_count-4, candidate_count):
            off = candidate_start + n*12
            print("  #%03d @0x%04X  % .9g  % .9g  % .9g" %
                  (n, off, f32(data, off), f32(data, off+4),
                   f32(data, off+8)))
    else:
        print("Candidate range exceeds file; sample layout does not apply.")

    print("")
    print("-- PRINTABLE STRINGS IN FINAL 0x500 BYTES --")
    for off, value in find_strings(data, max(0, size-0x500), size, 3):
        print("0x%04X  %s" % (off, value))

    if candidate_end < size:
        dump_bytes(data, candidate_end, min(0x100, size-candidate_end),
                   "BYTES AFTER 573 x Float3 CANDIDATE")

    print("")
    print("READ ONLY complete. No file was changed.")
    print("=" * 76)

def main():
    dlg = OpenFileDialog()
    dlg.Title = "Select NBA Live 06 character EBO"
    dlg.Filter = "EBO files (*.ebo)|*.ebo|All files (*.*)|*.*"
    dlg.Multiselect = False
    if dlg.ShowDialog() != DialogResult.OK:
        print("Cancelled.")
        return
    path = dlg.FileName
    try:
        inspect(path)
    except Exception as e:
        import traceback
        print("PROBE V2 ERROR TYPE: %s" % type(e).__name__)
        print("PROBE V2 ERROR: %s" % repr(e))
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
