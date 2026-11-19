"""Creation of the Blender objects representing an imported volume."""

import bpy
import numpy as np
from mathutils import Matrix

from . import atlas, shader

BOX_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def split_affine(voxel_to_world):
    """Split a voxel -> world affine into a rigid object matrix and a residual.

    Blender object matrices cannot hold shear (or reflections), so the object
    gets the closest rotation (polar decomposition) placed at the volume centre,
    and the remaining linear part (scaling, flips, shear) is applied in the
    shader through `local_to_voxel`.
    Returns (object_matrix, voxel_to_local), both 4x4 numpy arrays.
    """
    a = np.asarray(voxel_to_world, dtype=np.float64)
    u, _, vt = np.linalg.svd(a[:3, :3])
    if np.linalg.det(u @ vt) < 0:
        u[:, 2] *= -1
    obj = np.eye(4)
    obj[:3, :3] = u @ vt
    obj[:3, 3] = a[:3, 3]
    return obj, np.linalg.inv(obj) @ a


def create_volume_object(context, vol, interpolation="TRILINEAR", collection=None):
    scene = context.scene
    scale = scene.bb_mm_to_bu
    voxel_to_world = np.diag([scale, scale, scale, 1.0]) @ vol.affine
    nx, ny, nz = vol.shape
    # Put the object origin at the volume centre.
    center_voxel = np.array([(nx - 1) / 2, (ny - 1) / 2, (nz - 1) / 2, 1.0])
    center = voxel_to_world @ center_voxel
    shift = np.eye(4)
    shift[:3, 3] = center_voxel[:3]
    obj_matrix, voxel_to_local = split_affine(voxel_to_world @ shift)
    voxel_to_local = voxel_to_local @ np.linalg.inv(shift)
    assert np.allclose(obj_matrix[:3, 3], center[:3])

    # Bounding box mesh (edges only), in object space.
    corners = []
    for k in (-0.5, nz - 0.5):
        for j in (-0.5, ny - 0.5):
            for i in (-0.5, nx - 0.5):
                corners.append(tuple((voxel_to_local @ np.array([i, j, k, 1.0]))[:3]))
    mesh = bpy.data.meshes.new(vol.name)
    mesh.from_pydata(corners, BOX_EDGES, [])
    obj = bpy.data.objects.new(vol.name, mesh)
    obj.matrix_world = Matrix(obj_matrix.tolist())
    obj.display_type = "WIRE"
    obj.show_name = True
    obj.hide_render = True
    obj.visible_camera = obj.visible_shadow = False
    (collection or context.collection or scene.collection).objects.link(obj)

    vmin, vmax = atlas.value_range(vol.data)
    wmin, wmax = atlas.robust_range(vol.data)
    layout, pixels = atlas.build_atlas(vol.data, vmin, vmax)
    image = bpy.data.images.new(f"BB {vol.name}", layout.width, layout.height, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    image.alpha_mode = "CHANNEL_PACKED"
    image.use_half_precision = False
    image.pixels.foreach_set(pixels.ravel())
    image.file_format = "OPEN_EXR"
    image.pack()
    image.use_fake_user = True

    s = obj.bb_volume
    s.is_volume = True
    s.filepath = vol.filepath
    s.dims = (nx, ny, nz)
    s.voxel_size = tuple(vol.voxel_size)
    s.atlas_grid = (layout.cols, layout.rows)
    s.local_to_voxel = tuple(np.linalg.inv(voxel_to_local).ravel())
    s.value_min, s.value_max = vmin, vmax
    s.window_min, s.window_max = wmin, wmax
    s.image = image
    s["interpolation"] = 0 if interpolation == "NEAREST" else 1
    s.sampler = shader.build_sampler_group(obj)
    return obj


def slice_plane(context, volume, axis="Z", name=None):
    """Add a plane through the volume centre, normal to a world axis.

    The plane covers the world-aligned bounding box of the volume.
    """
    corners = np.array([tuple(volume.matrix_world @ v.co) for v in volume.data.vertices])
    lo, hi = corners.min(axis=0), corners.max(axis=0)
    center = (lo + hi) / 2
    # plane axes (u, v) and normal for each orientation, in world space
    u_axis, v_axis = {"Z": (0, 1), "Y": (0, 2), "X": (1, 2)}[axis]
    hu = (hi[u_axis] - lo[u_axis]) / 2
    hv = (hi[v_axis] - lo[v_axis]) / 2
    verts = [(-hu, -hv, 0), (hu, -hv, 0), (hu, hv, 0), (-hu, hv, 0)]
    mesh = bpy.data.meshes.new(name or f"{volume.name} slice")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.uv_layers.new()
    plane = bpy.data.objects.new(mesh.name, mesh)
    rot = {
        "Z": Matrix.Identity(3),
        "Y": Matrix.Rotation(np.pi / 2, 3, "X"),  # coronal: local x, y -> world X, Z
        "X": Matrix.Rotation(np.pi / 2, 3, "Z") @ Matrix.Rotation(np.pi / 2, 3, "X"),  # sagittal: -> world Y, Z
    }[axis]
    plane.matrix_world = Matrix.Translation(tuple(center)) @ rot.to_4x4()
    (context.collection or context.scene.collection).objects.link(plane)
    plane.data.materials.append(shader.create_slice_material(volume))
    return plane
