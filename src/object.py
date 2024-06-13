import bpy, random, math

class ObjectManipulator:
    def set_active_object(self, obj: bpy.types.Object) -> None:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    def convert_to_mesh(self, obj: bpy.types.Object) -> None:
        self.set_active_object(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.curve.select_all(action="SELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.convert(target="MESH")

    def clean_up_mesh(self, target_obj: bpy.types.Object) -> None:
        self.set_active_object(target_obj)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as e:
            raise ValueError(f"Error while cleaning up the mesh: {e}")

    def add_bevel(
        self,
        obj: bpy.types.Object,
        width: float,
        segments: int
    ) -> None:
        
        self.set_active_object(obj)
        bpy.ops.object.modifier_add(type="BEVEL")
        bpy.context.object.modifiers["Bevel"].width = width
        bpy.context.object.modifiers["Bevel"].segments = segments
        self.apply_modifier(obj, "Bevel")

    # def apply_boolean_modifier(
    #     self,
    #     obj: bpy.types.Object,
    #     target: bpy.types.Object,
    #     vertex_group_name: str = "",
    # ) -> None:
        
    #     self.set_active_object(obj)

    #     original_vertices = set(tuple(v.co) for v in obj.data.vertices)

    #     bpy.ops.object.modifier_add(type="BOOLEAN")
    #     bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
    #     bpy.context.object.modifiers["Boolean"].object = target
    #     self.apply_modifier(obj, "Boolean")

    #     if len(vertex_group_name):
    #         new_vertices = []
    #         for v in obj.data.vertices:
    #             if tuple(v.co) not in original_vertices and v.co.z != 0:
    #                 new_vertices.append(v.index)
    #         self.assign_vertices_to_group(obj, new_vertices, vertex_group_name)

    def apply_boolean_modifier(
        self,
        obj: bpy.types.Object,
        target: bpy.types.Object,
        vertex_group_name: str = "",
    ) -> None:

        self.set_active_object(obj)

        original_vertices = set(tuple(v.co) for v in obj.data.vertices)

        bpy.ops.object.modifier_add(type="BOOLEAN")
        bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
        bpy.context.object.modifiers["Boolean"].object = target
        self.apply_modifier(obj, "Boolean")

        if len(vertex_group_name):
            new_vertices = []
            for v in obj.data.vertices:
                if 0 <= v.co.z <= 0.9 and tuple(v.co) not in original_vertices:
                    new_vertices.append(v.index)
            self.assign_vertices_to_group(obj, new_vertices, vertex_group_name)

    def apply_modifier(self, obj: bpy.types.Object, modifier_name: str) -> None:
        override = bpy.context.copy()
        override["object"] = obj
        override["active_object"] = obj
        override["selected_objects"] = [obj]
        bpy.ops.object.modifier_apply(modifier=modifier_name)

    def assign_vertices_to_group(
        self,
        obj: bpy.types.Object,
        vertex_indices: list,
        group_name: str
    ) -> None:
        if group_name not in obj.vertex_groups:
            vertex_group = obj.vertex_groups.new(name=group_name)
        else:
            vertex_group = obj.vertex_groups[group_name]

        vertex_group.add(vertex_indices, 1.0, "ADD")

    def add_subdivision_surface(
        self,
        obj: bpy.types.Object,
        levels: int,
        render_levels: int
    ) -> None:
        self.set_active_object(obj)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "CATMULL_CLARK"
        bpy.context.object.modifiers["Subdivision"].levels = levels
        bpy.context.object.modifiers["Subdivision"].render_levels = render_levels
        self.apply_modifier(obj, "Subdivision")

    def delete_object_and_collection(self, obj: bpy.types.Object) -> None:
        bpy.data.objects.remove(obj, do_unlink=True)
        if obj.name in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections[obj.name])

    def hide_object(self, obj: bpy.types.Object) -> None:
        obj.hide_set(True)

    def add_holes(self, body, holes) -> bool:
        try:
            self.apply_boolean_modifier(body, holes)
            self.hide_object(holes)
        except Exception as e:
            print(f"Error while adding holes: {e}")
            return False
        return True

    def apply_engraving(
        self,
        body: bpy.types.Object,
        engraving: bpy.types.Object
    ) -> bool:
        try:
            self.apply_boolean_modifier(body, engraving, vertex_group_name="engraving")
            self.hide_object(engraving)
        except Exception as e:
            print(f"Error while applying engraving: {e}")
            return False
        return True

    @staticmethod
    def rotate_object(
        object: bpy.types.Object,
        rx: float,
        ry: float,
        rz: float,
    ) -> None:
        object.rotation_euler[0] = math.radians(rx)
        object.rotation_euler[1] = math.radians(ry)
        object.rotation_euler[2] = math.radians(rz)


class Extruder:
    def __init__(self, manipulator: ObjectManipulator):
        self.manipulator = manipulator

    def extrude_object(
        self,
        obj: bpy.types.Object,
        height: float,
        fill: bool = True
    ) -> None:
        
        if obj.type != "MESH":
            self.manipulator.convert_to_mesh(obj)
 
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, height)})

        if fill: self.fill_face()
        self.manipulator.clean_up_mesh(obj)

    def extrude_body(self, body: bpy.types.Object) -> bool:
        try:
            self.extrude_object(body, height=0.9)
            self.manipulator.add_bevel(
                body,
                width=random.uniform(0.15, 0.25),
                segments=random.randint(15, 25),
            )
            self.manipulator.add_subdivision_surface(body, levels=2, render_levels=1)
            bpy.ops.object.shade_smooth()
        except Exception as e:
            print(f"Error while extruding the body: {e}")
            return False
        return True

    def extrude_holes(self, hole: bpy.types.Object) -> bool:
        try:
            self.extrude_object(hole, height=1.3)
        except Exception as e:
            print(f"Error while extruding the holes: {e}")
            return False
        return True

    def extrude_engraving(self, engraving: bpy.types.Object) -> bool:
        try:
            self.extrude_object(engraving, height=0.25)
        except Exception as e:
            print(f"Error while extruding the engraving: {e}")
            return False
        return True

    def fill_face(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()