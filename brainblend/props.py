import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)

from . import colormaps, shader


def _rebuild_sampler(self, context):
    obj = self.id_data
    if self.is_volume and self.image is not None:
        self.sampler = shader.build_sampler_group(obj)


def _is_volume(self, obj):
    return obj.bb_volume.is_volume


class BBVolumeSettings(bpy.types.PropertyGroup):
    is_volume: BoolProperty(default=False)
    filepath: StringProperty(name="File", subtype="FILE_PATH")
    dims: IntVectorProperty(name="Dimensions", size=3)
    voxel_size: FloatVectorProperty(name="Voxel size (mm)", size=3)
    atlas_grid: IntVectorProperty(size=2)
    local_to_voxel: FloatVectorProperty(size=16)
    value_min: FloatProperty(name="Min value")
    value_max: FloatProperty(name="Max value")
    window_min: FloatProperty(name="Default window min")
    window_max: FloatProperty(name="Default window max")
    image: PointerProperty(type=bpy.types.Image)
    sampler: PointerProperty(type=bpy.types.NodeTree)
    interpolation: EnumProperty(
        name="Interpolation",
        items=[
            ("NEAREST", "Nearest", "Show voxels as blocks (fastest)"),
            ("TRILINEAR", "Trilinear", "Smooth interpolation between voxels"),
        ],
        default="TRILINEAR",
        update=_rebuild_sampler,
    )


def _slice_nodes(self):
    return shader.slice_nodes(self.id_data)


def _update_window(self, context):
    nodes = _slice_nodes(self)
    if nodes:
        nodes[shader.NODE_MIN].outputs[0].default_value = self.window_min
        nodes[shader.NODE_MAX].outputs[0].default_value = self.window_max


def _update_colormap(self, context):
    nodes = _slice_nodes(self)
    if nodes:
        colormaps.apply_colormap(nodes[shader.NODE_RAMP].color_ramp, self.colormap)


def _update_alpha(self, context):
    nodes = _slice_nodes(self)
    if nodes:
        nodes[shader.NODE_OPACITY].outputs[0].default_value = self.opacity
        nodes[shader.NODE_CLIP].outputs[0].default_value = float(self.clip_below)


class BBSliceSettings(bpy.types.PropertyGroup):
    volume: PointerProperty(type=bpy.types.Object, name="Volume", poll=_is_volume)
    window_min: FloatProperty(name="Min", description="Value shown with the start of the color map", update=_update_window)
    window_max: FloatProperty(name="Max", description="Value shown with the end of the color map", update=_update_window)
    colormap: EnumProperty(name="Color map", items=colormaps.ENUM_ITEMS, default="GRAY", update=_update_colormap)
    opacity: FloatProperty(name="Opacity", min=0.0, max=1.0, default=1.0, subtype="FACTOR", update=_update_alpha)
    clip_below: BoolProperty(
        name="Transparent below min",
        description="Make values below the window minimum transparent (useful for overlays)",
        update=_update_alpha,
    )


classes = (BBVolumeSettings, BBSliceSettings)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.bb_volume = PointerProperty(type=BBVolumeSettings)
    bpy.types.Material.bb_slice = PointerProperty(type=BBSliceSettings)
    bpy.types.Scene.bb_mm_to_bu = FloatProperty(
        name="Scale (units per mm)",
        description="Blender units per millimetre used when importing volumes "
        "(0.001 keeps real-world size with metric units)",
        default=0.001,
        min=1e-6,
        precision=4,
    )
    bpy.types.Scene.bb_active_volume = PointerProperty(type=bpy.types.Object, name="Volume", poll=_is_volume)


def unregister():
    del bpy.types.Scene.bb_active_volume
    del bpy.types.Scene.bb_mm_to_bu
    del bpy.types.Material.bb_slice
    del bpy.types.Object.bb_volume
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
