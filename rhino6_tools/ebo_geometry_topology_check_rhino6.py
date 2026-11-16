# -*- coding: utf-8 -*-
# Rhino 6 / IronPython 2.7
# NBA Live 06 headAShape topology and normal diagnostic
# READ ONLY: reads base_lodB.ebo and writes a TXT report only.

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

def write_text(path, value):
    f = open(path, 'wb')
    try:
        f.write(value)
    finally:
        f.close()

def vec3(d, off):
    return struct.unpack_from('<fff', d, off)

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def make_faces(indices, mode):
    faces = []
    degenerate = 0
    if mode == 'list':
        for i in range(0, (len(indices)//3)*3, 3):
            a, b, c = indices[i], indices[i+1], indices[i+2]
            if a == b or b == c or a == c:
                degenerate += 1
            else:
                faces.append((a, b, c))
    else:
        for i in range(len(indices)-2):
            a, b, c = indices[i], indices[i+1], indices[i+2]
            if i % 2:
                a, b = b, a
            if a == b or b == c or a == c:
                degenerate += 1
            else:
                faces.append((a, b, c))
    return faces, degenerate

def analyze(faces, positions, normals):
    edge_counts = {}
    used = set()
    face_adjacency = [set() for x in faces]
    edge_faces = {}
    zero_area = 0
    positive = 0
    negative = 0
    near_zero = 0
    duplicate_keys = set()
    duplicate_faces = 0

    for fi, face in enumerate(faces):
        a, b, c = face
        used.add(a); used.add(b); used.add(c)
        key = tuple(sorted(face))
        if key in duplicate_keys:
            duplicate_faces += 1
        else:
            duplicate_keys.add(key)

        p0, p1, p2 = positions[a], positions[b], positions[c]
        n = cross(sub(p1, p0), sub(p2, p0))
        area2 = (dot(n, n)) ** 0.5
        if area2 < 1.0e-12:
            zero_area += 1

        avg_n = (normals[a][0]+normals[b][0]+normals[c][0],
                 normals[a][1]+normals[b][1]+normals[c][1],
                 normals[a][2]+normals[b][2]+normals[c][2])
        agreement = dot(n, avg_n)
        if agreement > 1.0e-10:
            positive += 1
        elif agreement < -1.0e-10:
            negative += 1
        else:
            near_zero += 1

        for e in ((a,b), (b,c), (c,a)):
            ek = (min(e[0], e[1]), max(e[0], e[1]))
            edge_counts[ek] = edge_counts.get(ek, 0) + 1
            edge_faces.setdefault(ek, []).append(fi)

    boundary = sum(1 for v in edge_counts.values() if v == 1)
    manifold2 = sum(1 for v in edge_counts.values() if v == 2)
    nonmanifold = sum(1 for v in edge_counts.values() if v > 2)

    for ek, flist in edge_faces.items():
        if len(flist) == 2:
            face_adjacency[flist[0]].add(flist[1])
            face_adjacency[flist[1]].add(flist[0])

    seen = set()
    components = 0
    for start in range(len(faces)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            for nxt in face_adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)

    return {
        'faces': len(faces), 'used_vertices': len(used),
        'boundary_edges': boundary, 'two_face_edges': manifold2,
        'nonmanifold_edges': nonmanifold, 'zero_area': zero_area,
        'duplicate_faces': duplicate_faces, 'components': components,
        'normal_positive': positive, 'normal_negative': negative,
        'normal_neutral': near_zero
    }

def fmt(label, stats, degenerate, min_index, max_index):
    lines = []
    lines.append('[' + label + ']')
    lines.append('indices min/max: %d / %d' % (min_index, max_index))
    lines.append('faces kept: %d; repeated-index strip/list triangles skipped: %d' %
                 (stats['faces'], degenerate))
    lines.append('used vertices: %d / 733; connected face components: %d' %
                 (stats['used_vertices'], stats['components']))
    lines.append('edges: boundary=%d, shared-by-2=%d, nonmanifold(>2)=%d' %
                 (stats['boundary_edges'], stats['two_face_edges'], stats['nonmanifold_edges']))
    lines.append('zero-area faces: %d; duplicate faces: %d' %
                 (stats['zero_area'], stats['duplicate_faces']))
    lines.append('face cross-product vs averaged vertex normals: +%d / -%d / neutral=%d' %
                 (stats['normal_positive'], stats['normal_negative'], stats['normal_neutral']))
    lines.append('')
    return lines

def main():
    src = rs.OpenFileName('Select NBA Live 06 base_lodB.ebo', 'EBO files (*.ebo)|*.ebo||')
    if not src:
        print('Cancelled.')
        return
    out_dir = rs.BrowseForFolder(os.path.dirname(src), 'Choose folder for topology report')
    if not out_dir:
        print('Cancelled.')
        return

    try:
        d = read_file(src)
        if len(d) != 204248 or d[:4] != 'EBO\x00' or u32(d, 4) != 17:
            print('STOP: Expected inspected base_lodB.ebo (204248 bytes, EBO v17).')
            print('File size=%d' % len(d))
            return

        geom = 0xC834
        pos_desc = u32(d, geom+0xB0)
        nrm_desc = u32(d, geom+0xB4)
        idx_desc = u32(d, geom+0xC0)
        vcount = u32(d, geom+0xC4)
        icount = u32(d, geom+0xC8)
        if (pos_desc, nrm_desc, idx_desc, vcount, icount) != (0xC91C, 0x113A0, 0x13618, 733, 2010):
            print('STOP: Geometry descriptors/counts do not match the inspected sample.')
            return

        pos_data = pos_desc+0x1C
        nrm_data = nrm_desc+0x1C
        idx_data = idx_desc+0x18
        positions = [vec3(d, pos_data+i*12) for i in range(vcount)]
        normals = [vec3(d, nrm_data+i*12) for i in range(vcount)]

        report = []
        report.append('NBA LIVE 06 headAShape TOPOLOGY / NORMAL REPORT')
        report.append('Source: %s' % os.path.basename(src))
        report.append('Geometry: headAShape @ 0x%X' % geom)
        report.append('Vertex count: %d; declared index count: %d' % (vcount, icount))
        report.append('Index payload: 0x%X; testing candidate byte offsets +0 and +4' % idx_data)
        report.append('Normal agreement is sign-only: positive/negative counts are not a final winding verdict.')
        report.append('')

        for skip in (0, 4):
            indices = list(struct.unpack_from('<%dH' % icount, d, idx_data+skip))
            if min(indices) >= vcount or max(indices) >= vcount:
                report.append('offset+%d: OUT OF RANGE; skipped' % skip)
                continue
            for mode in ('strip', 'list'):
                faces, degenerate = make_faces(indices, mode)
                stats = analyze(faces, positions, normals)
                report.extend(fmt('offset+%d / %s' % (skip, mode), stats,
                                  degenerate, min(indices), max(indices)))

        report_path = os.path.join(out_dir, 'headAShape_topology_report.txt')
        write_text(report_path, '\n'.join(report)+'\n')
        print('')
        print('===== TOPOLOGY CHECK COMPLETE =====')
        print('Report: %s' % report_path)
        print('No EBO data was changed.')
        print('Send the full report text for interpretation.')
    except Exception as e:
        print('ERROR: ' + str(e))

if __name__ == '__main__':
    main()
