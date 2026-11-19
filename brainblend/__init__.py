"""BrainBlend: display MRI volume slices on any surface in Blender.

A NIfTI volume is imported as a wire box placed in world space with the image
affine (millimetres scaled to Blender units). Its voxels are stored in a packed
float image and sampled by shader nodes at the world position of each shading
point, so any mesh using a "BB Slice" material shows the matching cut through
the volume and updates live when moved.
"""

from . import operators, props, ui

_modules = (props, operators, ui)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
