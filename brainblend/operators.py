import os

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import nifti, shader, volume

INTERPOLATION_ITEMS = [
    ("TRILINEAR", "Trilinear", "Smooth interpolation between voxels"),
    ("NEAREST", "Nearest", "Show voxels as blocks"),
]


def active_volume(context):
    obj = context.active_object
    if obj is not None and obj.bb_volume.is_volume:
        return obj
    vol = context.scene.bb_active_volume
    if vol is not None and vol.name in context.scene.objects:
        return vol
    return None


def active_slice_material(context):
    obj = context.active_object
    if obj is None or obj.bb_volume.is_volume:
        return None
    mat = obj.active_material
    if mat is not None and mat.bb_slice.volume is not None and shader.slice_nodes(mat):
        return mat
    return None


class BB_OT_import_nifti(bpy.types.Operator, ImportHelper):
    """Import NIfTI volumes, placed in world space with their affine (millimetres)"""

    bl_idname = "brainblend.import_nifti"
    bl_label = "Import NIfTI Volume"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".nii"
    filter_glob: StringProperty(default="*.nii;*.nii.gz;*.img;*.hdr;*.mgz", options={"HIDDEN"})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"})
    directory: StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})
    volume_index: IntProperty(name="Volume index", description="Volume to load from a 4D image", min=0, default=0)
    interpolation: EnumProperty(name="Interpolation", items=INTERPOLATION_ITEMS, default="TRILINEAR")
    add_slices: BoolProperty(name="Add slice planes", description="Add axial, coronal and sagittal planes", default=True)
    standard_view: BoolProperty(
        name="Use Standard view transform",
        description="Switch color management to 'Standard' so that displayed colors match the color map "
        "(the default AgX transform alters them)",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "bb_mm_to_bu")
        layout.prop(self, "volume_index")
        layout.prop(self, "interpolation")
        layout.prop(self, "add_slices")
        layout.prop(self, "standard_view")

    def execute(self, context):
        paths = [os.path.join(self.directory, f.name) for f in self.files if f.name] or [self.filepath]
        created = []
        for path in paths:
            try:
                vol = nifti.load_nifti(path, self.volume_index)
                obj = volume.create_volume_object(context, vol, self.interpolation)
            except Exception as e:  # report and continue with the other files
                self.report({"ERROR"}, f"{os.path.basename(path)}: {e}")
                continue
            created.append(obj)
            if self.add_slices and len(created) == 1:
                for axis, label in (("Z", "axial"), ("Y", "coronal"), ("X", "sagittal")):
                    volume.slice_plane(context, obj, axis, f"{obj.name} {label}")
        if not created:
            return {"CANCELLED"}
        if self.standard_view:
            context.scene.view_settings.view_transform = "Standard"
            context.scene.view_settings.look = "None"
        context.scene.bb_active_volume = created[-1]
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        context.view_layer.objects.active = created[-1]
        self.report({"INFO"}, f"Imported {len(created)} volume(s). Use Material Preview to see slices.")
        return {"FINISHED"}


class BB_OT_add_slice(bpy.types.Operator):
    """Add a plane showing the active volume through its centre"""

    bl_idname = "brainblend.add_slice"
    bl_label = "Add Slice Plane"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Orientation",
        items=[("Z", "Axial", "Plane normal to Z"), ("Y", "Coronal", "Plane normal to Y"), ("X", "Sagittal", "Plane normal to X")],
    )

    @classmethod
    def poll(cls, context):
        return active_volume(context) is not None

    def execute(self, context):
        vol = active_volume(context)
        label = {"Z": "axial", "Y": "coronal", "X": "sagittal"}[self.axis]
        plane = volume.slice_plane(context, vol, self.axis, f"{vol.name} {label}")
        for obj in context.selected_objects:
            obj.select_set(False)
        plane.select_set(True)
        context.view_layer.objects.active = plane
        return {"FINISHED"}


class BB_OT_assign_slice_material(bpy.types.Operator):
    """Give the selected objects a material showing the active volume"""

    bl_idname = "brainblend.assign_slice_material"
    bl_label = "Show Volume on Selected"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.bb_active_volume is not None and any(
            o.type == "MESH" and not o.bb_volume.is_volume for o in context.selected_objects
        )

    def execute(self, context):
        vol = context.scene.bb_active_volume
        count = 0
        for obj in context.selected_objects:
            if obj.type != "MESH" or obj.bb_volume.is_volume:
                continue
            mat = shader.create_slice_material(vol)
            if obj.data.materials:
                for i in range(len(obj.data.materials)):
                    obj.data.materials[i] = mat
            else:
                obj.data.materials.append(mat)
            count += 1
        self.report({"INFO"}, f"Assigned {vol.name} to {count} object(s)")
        return {"FINISHED"}


class BB_OT_reset_window(bpy.types.Operator):
    """Reset the display window of the active slice material"""

    bl_idname = "brainblend.reset_window"
    bl_label = "Reset Window"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        items=[("ROBUST", "Robust", "1st to 99.5th percentile"), ("FULL", "Full range", "Minimum to maximum value")]
    )

    @classmethod
    def poll(cls, context):
        return active_slice_material(context) is not None

    def execute(self, context):
        ms = active_slice_material(context).bb_slice
        vs = ms.volume.bb_volume
        if self.mode == "FULL":
            ms.window_min, ms.window_max = vs.value_min, vs.value_max
        else:
            ms.window_min, ms.window_max = vs.window_min, vs.window_max
        return {"FINISHED"}


def menu_import(self, context):
    self.layout.operator(BB_OT_import_nifti.bl_idname, text="NIfTI volume (.nii, .nii.gz)")


classes = (BB_OT_import_nifti, BB_OT_add_slice, BB_OT_assign_slice_material, BB_OT_reset_window)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
