# -*- coding: utf-8 -*-
# NBA Live 06 HEAD POINT PREVIEW V15
# Rhino 6 / IronPython 2.7
# READ ONLY: extracts the 733 rendered head positions as one Rhino PointCloud.
# Does not modify the EBO file and does not guess face topology.

from System.Windows.Forms import OpenFileDialog, DialogResult
from System.IO import File
from System import BitConverter
import math
import Rhino
import scriptcontext as sc

def bval(d, o):
    return int(d[o])

def u16(d, o):
    return bval(d,o) | (bval(d,o+1) << 8)

def u32(d, o):
    return (bval(d,o) | (bval(d,o+1) << 8) |
            (bval(d,o+2) << 16) | (bval(d,o+3) << 24))

def f32(d, o):
    return float(BitConverter.ToSingle(d, o))

def chunk_ranges(d):
    p=u32(d,0x10)
    count=u16(d,0x24)
    out=[]
    for i in range(count):
        if p+0x14 > len(d):
            break
        size=u32(d,p+0x10)
        if size < 0x14 or p+size > len(d):
            break
        out.append((p,p+size))
        p += size
    return out

def owner_start(ranges, off):
    for s,e in ranges:
        if s <= off < e:
            return s
    return -1

def find_head_mapping(d):
    ranges=chunk_ranges(d)
    found=[]
    for off in range(0,len(d)-24,4):
        logical=u32(d,off)
        one=u32(d,off+4)
        rendered=u32(d,off+8)
        pos=u32(d,off+12)
        mp=u32(d,off+16)
        vb=u32(d,off+20)
        if logical != 573 or one != 1 or rendered != 733:
            continue
        if mp > len(d)-rendered*2 or pos > len(d)-rendered*12 or vb+12 > len(d):
            continue
        if u32(d,vb+4) != 12 or u32(d,vb) != rendered*12 or u32(d,vb+8) != pos:
            continue
        vals=[u16(d,mp+i*2) for i in range(rendered)]
        if min(vals) != 0 or max(vals) != 572 or len(set(vals)) != 573:
            continue
        found.append((off,logical,rendered,pos,mp,owner_start(ranges,off),vals))
    if len(found) != 1:
        raise ValueError('Expected exactly one 573 -> 733 head mapping; found %d' % len(found))
    return found[0]

def main():
    dlg=OpenFileDialog()
    dlg.Title='Select NBA Live 06 base_lodB.ebo'
    dlg.Filter='EBO files (*.ebo)|*.ebo|All files (*.*)|*.*'
    dlg.Multiselect=False
    if dlg.ShowDialog() != DialogResult.OK:
        print('Cancelled.')
        return

    path=dlg.FileName
    d=File.ReadAllBytes(path)
    if len(d)<0x60 or bval(d,0)!=69 or bval(d,1)!=66 or bval(d,2)!=79 or bval(d,3)!=0:
        print('ERROR: invalid EBO file')
        return

    record,logical,rendered,posptr,mapptr,owner,mapping=find_head_mapping(d)
    points=Rhino.Geometry.PointCloud()
    finite=True
    for i in range(rendered):
        x=f32(d,posptr+i*12)
        y=f32(d,posptr+i*12+4)
        z=f32(d,posptr+i*12+8)
        if math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y) or math.isnan(z) or math.isinf(z):
            finite=False
            raise ValueError('Non-finite position at rendered vertex %d' % i)
        points.Add(Rhino.Geometry.Point3d(x,y,z))

    if points.Count != 733 or not finite:
        raise ValueError('PointCloud validation failed: count=%d finite=%s' % (points.Count,str(finite)))

    attr=Rhino.DocObjects.ObjectAttributes()
    attr.Name='NBA06_headAShape_733_rendered_points'
    attr.SetUserString('SourceFile', path)
    attr.SetUserString('LogicalVertices', str(logical))
    attr.SetUserString('RenderedVertices', str(rendered))
    attr.SetUserString('PositionOffset', '0x%X' % posptr)
    attr.SetUserString('MapOffset', '0x%X' % mapptr)
    attr.SetUserString('MappingRule', 'rendered vertex -> logical vertex')

    gid=sc.doc.Objects.AddPointCloud(points, attr)
    if gid == System.Guid.Empty:
        print('ERROR: Rhino failed to add PointCloud')
        return
    sc.doc.Views.Redraw()

    print('')
    print('='*72)
    print('V15 HEAD POINT PREVIEW COMPLETE')
    print('SOURCE: %s' % path)
    print('GEOMETRY_CHUNK=0x%X MAP_RECORD=0x%X' % (owner,record))
    print('LOGICAL_VERTICES=%d RENDERED_VERTICES=%d' % (logical,rendered))
    print('POSITION_BUFFER=0x%X MAP_BUFFER=0x%X' % (posptr,mapptr))
    print('RHINO_OBJECT=PointCloud POINTS=%d' % points.Count)
    print('EBO_SOURCE_MODIFIED=NO')
    print('NOTE: point order follows the EBO rendered-vertex buffer.')
    print('='*72)

if __name__ == '__main__':
    import System
    main()
