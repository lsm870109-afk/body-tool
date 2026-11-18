# -*- coding: utf-8 -*-
"""
DAMILB SD TEST - STEP 1 + 2
NBA Live 06 / Rhino 6 / IronPython 2.7
1) Enlarge head moderately
2) Make skull rounder by widening X/Z and slightly reducing vertical height
Original EBO is never overwritten. Only the verified 573*XYZ morph payload is changed.
"""

import os
import struct
import math
import rhinoscriptsyntax as rs

VERTEX_COUNT = 573
PAYLOAD_SIZE = 6876
SIZE_FIELD = 0x11C
OFFSET_FIELD = 0x120
PIVOT_Y = 5.74519062
CENTER_X = 0.0
CENTER_Z = 0.10241555

# Step 1: overall head enlargement; Step 2: roundness.
HEAD_SCALE = 1.15
ROUND_XZ = 1.06
ROUND_Y = 0.96

HEAD_WEIGHTS = [1,0.0554,0.0554,1,1,0.8017,1,1,0.8017,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0.0554,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0.8017,1,1,1,0.8017,1,1,0.8017,1,0.8017,0,1,1,1,1,0,1,1,0.0554,1,1,0,0.3936,1,1,1,1,1,0,0.0554,1,0,1,1,0,1,1,1,0.0554,1,0,1,1,1,0,0.3936,0.8017,0,0,0.8017,0,1,1,1,1,0.8017,1,0,0.3936,0.3936,1,1,0,1,0,1,1,1,1,0.8017,1,1,0.3936,0,1,0,0.0554,0,1,0,1,0.8017,1,1,1,1,1,0,0.8017,1,1,1,1,1,1,1,1,1,1,1,1,0.3936,1,1,1,1,1,1,0.3936,1,1,0.3936,1,1,0.0554,0.0554,0.8017,0.3936,1,1,1,1,1,1,1,0.8017,1,1,1,1,0.3936,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0.8017,0.3936,0.8017,1,1,0.8017,1,1,0.3936,0.0554,1,0.3936,1,0,1,1,1,1,0.0554,1,1,1,1,1,1,1,1,0.3936,1,1,0.8017,1,1,0.8017,1,1,1,1,0.0554,1,1,0.0554,0.8017,1,0.3936,1,1,1,1,1,1,1,1,1,1,1,1,1,0.0554,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0.8017,0.8017,0.8017,1,0.0554,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,0.3936,0.8017,1,1,1,1,0.8017,1,0,0,0,0,0,0.3936,1,1,0.8017,1,1,1,1,0.0554,0.8017,0.3936,0,0,0,0,1,0,0.8017,0,0,0,0,1,1,1,1,1,1,1,1,0.0554,1,1,1,1,1,0.8017,1,1,0.3936,0.3936,0.3936,0.0554,1,0.0554,0.3936,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0.3936,1,0,0.0554,1,1,1,1,0,1,1,1,1,1,1,1,1,1,0,0.0554,0.3936,0,1,0.3936,0,0,0,0,1,0.8017,0,0,0,0.3936,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,0,1,1,1,1,1,1,1,1,1,0,0.3936,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0.3936,0.8017,0.3936,1,1,1,0,1,1,1,0.8017,1,0,1,1,0.0554,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0.8017,0.8017,1,1,0.8017,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1]

def read_bytes(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def write_bytes(path, data):
    f = open(path, 'wb')
    try:
        f.write(data)
    finally:
        f.close()

def parse_obj_vertices(path):
    vertices = []
    f = open(path, 'r')
    try:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if line.startswith('v '):
                p = line.split()
                if len(p) < 4:
                    raise Exception('Invalid OBJ vertex at line %d' % line_no)
                xyz = (float(p[1]), float(p[2]), float(p[3]))
                if any(math.isnan(v) or math.isinf(v) for v in xyz):
                    raise Exception('Non-finite OBJ vertex at line %d' % line_no)
                vertices.append(xyz)
    finally:
        f.close()
    return vertices

def main():
    ebo_path = rs.OpenFileName(
        'Select original damilicB.ebo',
        'EBO files (*.ebo)|*.ebo||')
    if not ebo_path:
        return

    obj_path = rs.OpenFileName(
        'Select 06_head_neutral_mesh.obj',
        'OBJ files (*.obj)|*.obj||')
    if not obj_path:
        return

    try:
        base = parse_obj_vertices(obj_path)
        if len(base) != VERTEX_COUNT:
            raise Exception('Neutral OBJ must have 573 vertices; found %d' % len(base))
        if len(HEAD_WEIGHTS) != VERTEX_COUNT:
            raise Exception('Internal head-weight count is not 573.')

        src = read_bytes(ebo_path)
        if len(src) < 0x124 or src[:3] != 'EBO' or ord(src[3]) != 0:
            raise Exception('Invalid or incomplete EBO file.')

        size = struct.unpack_from('<I', src, SIZE_FIELD)[0]
        offset = struct.unpack_from('<I', src, OFFSET_FIELD)[0]
        if size != PAYLOAD_SIZE:
            raise Exception('Unexpected morph payload size: %d (expected 6876)' % size)
        if offset + size > len(src):
            raise Exception('Morph payload lies outside EBO file.')

        out_payload = []
        moved = 0
        max_move = 0.0
        sum_move = 0.0

        for i in range(VERTEX_COUNT):
            dx, dy, dz = struct.unpack_from('<fff', src, offset + i * 12)
            bx, by, bz = base[i]
            x, y, z = bx + dx, by + dy, bz + dz

            w = HEAD_WEIGHTS[i]
            # First enlarge around the established head pivot.
            x1 = CENTER_X + (x - CENTER_X) * (1.0 + (HEAD_SCALE - 1.0) * w)
            y1 = PIVOT_Y + (y - PIVOT_Y) * (1.0 + (HEAD_SCALE - 1.0) * w)
            z1 = CENTER_Z + (z - CENTER_Z) * (1.0 + (HEAD_SCALE - 1.0) * w)

            # Then round the skull: slightly wider/deeper and less vertically elongated.
            x2 = CENTER_X + (x1 - CENTER_X) * (1.0 + (ROUND_XZ - 1.0) * w)
            y2 = PIVOT_Y + (y1 - PIVOT_Y) * (1.0 + (ROUND_Y - 1.0) * w)
            z2 = CENTER_Z + (z1 - CENTER_Z) * (1.0 + (ROUND_XZ - 1.0) * w)

            ndx, ndy, ndz = x2 - bx, y2 - by, z2 - bz
            move = math.sqrt((x2-x)*(x2-x) + (y2-y)*(y2-y) + (z2-z)*(z2-z))
            if move > 0.000001:
                moved += 1
            if move > max_move:
                max_move = move
            sum_move += move
            out_payload.append(struct.pack('<fff', ndx, ndy, ndz))

        payload = ''.join(out_payload)
        if len(payload) != PAYLOAD_SIZE:
            raise Exception('Generated payload length mismatch.')

        result = src[:offset] + payload + src[offset + size:]
        if len(result) != len(src):
            raise Exception('Output file size changed unexpectedly.')
        if result[:offset] != src[:offset] or result[offset+size:] != src[offset+size:]:
            raise Exception('Bytes outside morph payload changed.')

        default_name = 'DAMILB_SD_step1_2.ebo'
        out_path = rs.SaveFileName(
            'Save new SD test EBO (original will not be overwritten)',
            'EBO files (*.ebo)|*.ebo||',
            os.path.dirname(ebo_path), default_name)
        if not out_path:
            return
        if os.path.abspath(out_path).lower() == os.path.abspath(ebo_path).lower():
            raise Exception('Output path must differ from original EBO.')

        write_bytes(out_path, result)
        check = read_bytes(out_path)
        if len(check) != len(src) or check[offset:offset+size] != payload:
            raise Exception('Saved EBO verification failed.')
        if check[:offset] != src[:offset] or check[offset+size:] != src[offset+size:]:
            raise Exception('Saved EBO outside-payload verification failed.')

        rs.MessageBox(
            'DAMILB SD STEP 1 + 2 COMPLETE\\n\\n'
            'Head enlargement: %.2f\\n'
            'Roundness X/Z: %.2f\\n'
            'Roundness Y: %.2f\\n'
            'Changed vertices: %d / %d\\n'
            'Average displacement: %.6f\\n'
            'Maximum displacement: %.6f\\n'
            'Morph payload: offset 0x%X / %d bytes\\n'
            'Original size: %d bytes\\n'
            'Output size: %d bytes\\n\\n'
            'All bytes outside the morph payload were preserved.\\n'
            'Output: %s' % (
                HEAD_SCALE, ROUND_XZ, ROUND_Y, moved, VERTEX_COUNT,
                sum_move / float(VERTEX_COUNT), max_move,
                offset, size, len(src), len(check), out_path),
            0, 'DAMILB SD Test')
    except Exception as e:
        rs.MessageBox('DAMILB SD TEST ERROR\\n\\n%s' % str(e), 0, 'DAMILB SD Test')

if __name__ == '__main__':
    main()
