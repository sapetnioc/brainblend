import bpy

from . import operators, shader


class BB_PT_main(bpy.types.Panel):
    bl_label = "BrainBlend"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BrainBlend"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.operator(operators.BB_OT_import_nifti.bl_idname, icon="IMPORT")
        layout.prop(scene, "bb_mm_to_bu")
        layout.prop(scene, "bb_active_volume")

        vol = scene.bb_active_volume
        if vol is not None:
            s = vol.bb_volume
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Size: {} x {} x {} voxels".format(*s.dims))
            col.label(text="Voxel: {:.3g} x {:.3g} x {:.3g} mm".format(*s.voxel_size))
            col.label(text=f"Values: {s.value_min:.4g} .. {s.value_max:.4g}")
            box.prop(s, "interpolation")

        col = layout.column(align=True)
        col.label(text="Add slice plane:")
        row = col.row(align=True)
        for axis, label in (("Z", "Axial"), ("Y", "Coronal"), ("X", "Sagittal")):
            row.operator(operators.BB_OT_add_slice.bl_idname, text=label).axis = axis
        col.operator(operators.BB_OT_assign_slice_material.bl_idname, icon="MATERIAL")

        shading = getattr(context.space_data, "shading", None)
        if shading is not None and shading.type not in {"MATERIAL", "RENDERED"}:
            layout.label(text="Switch to Material Preview to see slices", icon="INFO")


class BB_PT_slice(bpy.types.Panel):
    bl_label = "Slice Display"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BrainBlend"

    @classmethod
    def poll(cls, context):
        return operators.active_slice_material(context) is not None

    def draw(self, context):
        layout = self.layout
        mat = operators.active_slice_material(context)
        ms = mat.bb_slice
        layout.label(text=f"{mat.name}  ({ms.volume.name})", icon="MATERIAL")
        col = layout.column(align=True)
        col.prop(ms, "window_min")
        col.prop(ms, "window_max")
        row = layout.row(align=True)
        row.operator(operators.BB_OT_reset_window.bl_idname, text="Auto").mode = "ROBUST"
        row.operator(operators.BB_OT_reset_window.bl_idname, text="Full range").mode = "FULL"
        layout.prop(ms, "colormap")
        nodes = shader.slice_nodes(mat)
        layout.template_color_ramp(nodes[shader.NODE_RAMP], "color_ramp", expand=True)
        layout.prop(ms, "opacity")
        layout.prop(ms, "clip_below")


classes = (BB_PT_main, BB_PT_slice)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
