import bpy
import bmesh

def fill_faces_with_holes(obj):
    if obj.type != 'MESH':
        bpy.ops.object.convert(target="MESH")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    bmesh.ops.holes_fill(bm, edges=bm.edges)
    
    bmesh.ops.triangulate(bm, faces=bm.faces)
    
    bmesh.ops.dissolve_limit(bm, angle_limit=0.1, use_dissolve_boundaries=False, verts=bm.verts, edges=bm.edges, delimit={'NORMAL'})
    
    bm.to_mesh(obj.data)
    bm.free()
    
    obj.data.update()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

obj = bpy.context.active_object

fill_faces_with_holes(obj)