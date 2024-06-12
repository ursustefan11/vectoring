import bpy

class MaterialManager:
    @staticmethod
    def create_material(
        name: str,
        color: tuple,
        metallic: float = 0.5,
        roughness: float = 0.5
    ) -> bpy.types.Material:
        
        material = bpy.data.materials.new(name=name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        return material

    @staticmethod
    def apply_material(
        obj: bpy.types.Object,
        material: bpy.types.Material
    ) -> None:
        
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    @staticmethod
    def assign_material_to_vertex_group(
        obj: bpy.types.Object,
        group_name: str,
        material_index: int
    ) -> None:
        
        vertex_group = obj.vertex_groups.get(group_name)
        if not vertex_group:
            print(f"Vertex group '{group_name}' not found in object '{obj.name}'")
            return

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.object.vertex_group_set_active(group=vertex_group.name)
        bpy.ops.object.vertex_group_select()

        bpy.context.object.active_material_index = material_index
        bpy.ops.object.material_slot_assign()

        bpy.ops.object.mode_set(mode="OBJECT")

    def set_materials(self, body: bpy.types.Object) -> None:
        silver_material = self.create_material(
            name="Silver", color=(0.827, 0.827, 0.827, 1), metallic=1, roughness=0.1
        )
        dark_material = self.create_material(
            name="Dark", color=(0.0, 0.0, 0.0, 1), metallic=0.5, roughness=1.0
        )

        self.apply_material(body, silver_material)
        body.data.materials.append(dark_material)
        dark_material_index = len(body.material_slots) - 1

        self.assign_material_to_vertex_group(body, "engraving", dark_material_index)