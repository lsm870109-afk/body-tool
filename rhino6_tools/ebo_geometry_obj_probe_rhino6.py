# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live 06 headAShape OBJ extraction probe
# READ ONLY: reads EBO and writes diagnostic OBJ files only. Never modifies EBO.

import os
import struct
import rhinoscriptsyntax as rs

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]

def read_file(path):
    f = open(path, 'rb')
    try:
        return f.read()
    finally:
        f.close()

def write_text(path, text):
    f = open(path, 'wb')
    try:
        f.write(text)
    finally:
        f.close()

def finite(v):
    return (v == v and abs(v) < 1.0e20)

def get_vec3(d, off):
    return struct.unpack_from('<fff', d, off)

def get_vec2(d, off):
    return struct.unpack_from('<ff', d, off)

def build_faces(indices, mode):
    faces = []
    degenerate = 0
    if mode == 'list':
        usable = (len(indices) // 3) * 3
        for i in range(0, usable, 3):
            a, b, c = indices[i], indices[i+1], indices[i+2]
            if a == b or b == c or a == c:
                degenerate += 1
            else:
                faces.append((a, b, c))
    else:
        for i in range(len(indices) - 2):
            a, b, c = indices[i], indices[i+1], indices[i+2]
            if (i % 2) == 1:
                a, b = b, a
            if a == b or b == c or a == c:
                degenerate += 1
            else:
                faces.append((a, b, c))
    return faces, degenerate

def write_obj(path, positions, normals, uvs, faces, label):
    lines = []
    lines.append('# NBA Live 06 headAShape diagnostic export')
    lines.append('# Candidate: ' + label)
    lines.append('o headAShape_' + label)
    for v in positions:
        lines.append('v %.9g %.9g %.9g' % (v[0], v[1], v[2]))
    for uv in uvs:
        lines.append('vt %.9g %.9g' % (uv[0], uv[1]))
    for n in normals:
        lines.append('vn %.9g %.9g %.9g' % (n[0], n[1], n[2]))
    for face in faces:
        a, b, c = face
        # Same vertex index is used for position, UV and normal.
        lines.append('f %d/%d/%d %d/%d/%d %d/%d/%d' %
                     (a+1, a+1, a+1, b+1, b+1, b+1, c+1, c+1, c+1))
    write_text(path, '\n'.join(lines) + '\n')

def main():
    src = rs.OpenFileName('Select NBA Live 06 base_lodB.ebo',
                          'EBO files (*.ebo)|*.ebo||')
    if not src:
        print('Cancelled.')
        return
    out_dir = rs.BrowseForFolder(os.path.dirname(src),
                                 'Choose folder for diagnostic OBJ exports')
    if not out_dir:
        print('Cancelled.')
        return

    try:
        d = read_file(src)
        if len(d) != 204248 or d[:4] != 'EBO\x00' or u32(d, 4) != 17:
            print('STOP: This probe is calibrated for the inspected base_lodB.ebo v17 sample.')
            print('File size=%d, version=%s' %
                  (len(d), str(u32(d, 4) if len(d) >= 8 else 'unknown')))
            return

        # Verified headAShape fields from the supplied Geometry probe.
        geom = 0xC834
        pos_desc = u32(d, geom + 0xB0)
        nrm_desc = u32(d, geom + 0xB4)
        uv_desc  = u32(d, geom + 0xBC)
        idx_desc = u32(d, geom + 0xC0)
        vertex_count = u32(d, geom + 0xC4)
        index_count = u32(d, geom + 0xC8)

        if (pos_desc, nrm_desc, uv_desc, idx_desc) != (0xC91C, 0x113A0, 0xEB94, 0x13618):
            print('STOP: headAShape descriptor pointers differ from the verified sample.')
            print('pos=0x%X normal=0x%X uv=0x%X index=0x%X' %
                  (pos_desc, nrm_desc, uv_desc, idx_desc))
            return
        if vertex_count != 733 or index_count != 2010:
            print('STOP: unexpected counts: vertices=%d indices=%d' %
                  (vertex_count, index_count))
            return

        # Descriptor payload offsets and byte lengths established by the array probe.
        pos_data = pos_desc + 0x1C
        nrm_data = nrm_desc + 0x1C
        uv_data = uv_desc + 0x1C
        idx_data = idx_desc + 0x18
        if (pos_data, nrm_data, uv_data, idx_data) != (0xC938, 0x113BC, 0xEBB0, 0x13630):
            print('STOP: payload offsets do not match the inspected sample.')
            return
        if (vertex_count * 12 > len(d) - pos_data or
            vertex_count * 12 > len(d) - nrm_data or
            vertex_count * 8 > len(d) - uv_data or
            4024 > len(d) - idx_data):
            print('STOP: one or more payloads exceed file bounds.')
            return

        positions = [get_vec3(d, pos_data + i*12) for i in range(vertex_count)]
        normals = [get_vec3(d, nrm_data + i*12) for i in range(vertex_count)]
        uvs = [get_vec2(d, uv_data + i*8) for i in range(vertex_count)]

        for label, rows in (('position', positions), ('normal', normals), ('uv', uvs)):
            for row in rows:
                for value in row:
                    if not finite(value):
                        print('STOP: non-finite value found in %s stream.' % label)
                        return

        report = []
        report.append('NBA LIVE 06 headAShape OBJ PROBE')
        report.append('Source: %s' % os.path.basename(src))
        report.append('Geometry offset: 0x%X' % geom)
        report.append('Vertices: %d' % vertex_count)
        report.append('Indices expected: %d' % index_count)
        report.append('Position data: 0x%X, %d bytes, stride 12' % (pos_data, vertex_count*12))
        report.append('Normal data:   0x%X, %d bytes, stride 12' % (nrm_data, vertex_count*12))
        report.append('UV data:       0x%X, %d bytes, stride 8' % (uv_data, vertex_count*8))
        report.append('Index data:    0x%X, 4024 bytes (2012 uint16 available)' % idx_data)
        report.append('')
        report.append('Each OBJ uses matching v/vt/vn indices.')
        report.append('Compare LIST vs STRIP topology in Rhino; no index interpretation is selected as final.')

        made = 0
        for skip in (0, 2, 4):
            indices = list(struct.unpack_from('<%dH' % index_count,
                                              d, idx_data + skip))
            if min(indices) < 0 or max(indices) >= vertex_count:
                report.append('SKIP offset+%d: out-of-range index' % skip)
                continue
            for mode in ('list', 'strip'):
                faces, degenerate = build_faces(indices, mode)
                label = 'offset%d_%s' % (skip, mode)
                out_path = os.path.join(out_dir, 'headAShape_' + label + '.obj')
                write_obj(out_path, positions, normals, uvs, faces, label)
                report.append('%s: faces=%d degenerate_skipped=%d min=%d max=%d' %
                              (label, len(faces), degenerate, min(indices), max(indices)))
                report.append('  file: ' + os.path.basename(out_path))
                made += 1

        report_path = os.path.join(out_dir, 'headAShape_probe_report.txt')
        write_text(report_path, '\n'.join(report) + '\n')
        print('')
        print('===== OBJ PROBE COMPLETE =====')
        print('Created %d diagnostic OBJ files.' % made)
        print('Output folder: %s' % out_dir)
        print('Report: %s' % report_path)
        print('Import the six OBJ files into Rhino and compare which topology forms the head correctly.')
        print('The source EBO was opened read-only and was not changed.')
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
