"""End-to-end check: render slices with Cycles and compare with numpy sampling."""

import math
import os

import bpy
import nibabel as nib
import numpy as np
import pytest
from mathutils import Matrix, Vector

from brainblend import shader

SHAPE = (20, 16, 13)


def make_affine():
    rot = Matrix.Rotation(0.3, 3, Vector((1, 2, 3)).normalized())
    lin = np.array(rot) @ np.diag([-1.2, 1.0, 2.5])  # x flip, anisotropic voxels
    lin = lin @ np.array([[1, 0.15, 0], [0, 1, 0], [0, 0, 1]])  # shear
    a = np.eye(4)
    a[:3, :3] = lin
    a[:3, 3] = (12.0, -8.0, 5.0)
    return a


def make_data():
    i, j, k = np.meshgrid(*[np.arange(n) for n in SHAPE], indexing="ij")
    return (100 + 50 * np.sin(i * 0.7) * np.cos(j * 0.5) + 3 * k).astype(np.float32)


def trilinear(data, p):
    nx, ny, nz = data.shape
    f = np.floor(p).astype(int)
    t = p - f
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[0] if dx else 1 - t[0]) * (t[1] if dy else 1 - t[1]) * (t[2] if dz else 1 - t[2])
                i = min(max(f[0] + dx, 0), nx - 1)
                j = min(max(f[1] + dy, 0), ny - 1)
                k = min(max(f[2] + dz, 0), nz - 1)
                out += w * data[i, j, k]
    return out


def nearest(data, p):
    q = np.clip(np.floor(p + 0.5).astype(int), 0, np.array(data.shape) - 1)
    return data[tuple(q)]


@pytest.fixture
def imported(clean_scene, tmp_path):
    data, affine = make_data(), make_affine()
    path = str(tmp_path / "test.nii.gz")
    nib.save(nib.Nifti1Image(data, affine), path)
    scene = clean_scene
    scene.bb_mm_to_bu = 0.01
    res = bpy.ops.brainblend.import_nifti(filepath=path, add_slices=True)
    assert res == {"FINISHED"}
    vol = scene.bb_active_volume
    assert vol is not None and vol.name == "test"
    return scene, vol, data, affine, tmp_path


def render_plane(scene, plane, size, tmp_path, res=24, engine="CYCLES"):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    cam.matrix_world = plane.matrix_world @ Matrix.Translation((0, 0, 1.0))
    cam_data.clip_start, cam_data.clip_end = 0.01, 10
    scene.camera = cam
    scene.render.engine = engine
    scene.render.filter_size = 0.01
    if engine == "BLENDER_EEVEE":
        scene.eevee.taa_render_samples = 1
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.cycles.filter_width = 0.01
    scene.cycles.seed = 0
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.filepath = str(tmp_path / "render.exr")
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(scene.render.filepath)
    pixels = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)
    bpy.data.images.remove(img)
    return pixels


def linear_ramp(mat):
    ramp = shader.slice_nodes(mat)[shader.NODE_RAMP].color_ramp
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])
    ramp.elements[0].position, ramp.elements[0].color = 0.0, (0, 0, 0, 1)
    ramp.elements[1].position, ramp.elements[1].color = 1.0, (1, 1, 1, 1)


ENGINES = ["CYCLES"] + (["BLENDER_EEVEE"] if os.environ.get("BB_TEST_EEVEE") else [])


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("interp", ["TRILINEAR", "NEAREST"])
def test_slice_matches_numpy(imported, interp, engine):
    scene, vol, data, affine, tmp_path = imported
    vol.bb_volume.interpolation = interp
    plane = bpy.data.objects[f"{vol.name} axial"]
    for label in ("coronal", "sagittal"):
        bpy.data.objects.remove(bpy.data.objects[f"{vol.name} {label}"])
    mat = plane.active_material
    linear_ramp(mat)
    lo, hi = float(data.min()) - 10, float(data.max()) + 10
    mat.bb_slice.window_min, mat.bb_slice.window_max = lo, hi

    # Move and tilt the plane: the slice must follow.
    plane.matrix_world = (
        Matrix.Translation(vol.matrix_world.translation + Vector((0.02, -0.01, 0.03)))
        @ Matrix.Rotation(0.4, 4, "X")
        @ Matrix.Rotation(0.2, 4, "Y")
    )
    size = 0.3
    res = 24
    pixels = render_plane(scene, plane, size, tmp_path, res, engine)

    world_to_voxel = np.linalg.inv(np.diag([0.01, 0.01, 0.01, 1.0]) @ affine)
    m = np.array(plane.matrix_world)
    errors, inside_count = [], 0
    for py in range(res):
        for px in range(res):
            u = ((px + 0.5) / res - 0.5) * size
            v = ((py + 0.5) / res - 0.5) * size
            world = m @ np.array([u, v, 0.0, 1.0])
            p = (world_to_voxel @ world)[:3]
            inside = all(-0.5 < p[a] < SHAPE[a] - 0.5 for a in range(3))
            margin = min(min(p[a] + 0.5, SHAPE[a] - 0.5 - p[a]) for a in range(3))
            if abs(margin) < 0.05:
                continue  # too close to the border to be decided reliably
            alpha = pixels[py, px, 3]
            assert alpha == pytest.approx(1.0 if inside else 0.0, abs=1e-3), (px, py, p)
            if not inside:
                continue
            inside_count += 1
            sample = trilinear if interp == "TRILINEAR" else nearest
            expected = (sample(data, p) - lo) / (hi - lo)
            if interp == "NEAREST" and np.min(np.abs((p + 0.5) % 1.0 - 0.5)) > 0.48:
                continue  # on a voxel boundary
            errors.append(abs(pixels[py, px, 0] - expected))
    assert inside_count > 100
    print("max error", engine, interp, max(errors), len(errors))
    assert max(errors) < 2e-3, max(errors)


def test_window_colormap_and_reload(imported):
    scene, vol, data, affine, tmp_path = imported
    plane = bpy.data.objects[f"{vol.name} coronal"]
    mat = plane.active_material
    ms = mat.bb_slice
    ms.window_min, ms.window_max = 50.0, 150.0
    nodes = shader.slice_nodes(mat)
    assert nodes[shader.NODE_MIN].outputs[0].default_value == 50.0
    ms.colormap = "HOT"
    assert len(nodes[shader.NODE_RAMP].color_ramp.elements) == 16
    ms.opacity = 0.5
    assert nodes[shader.NODE_OPACITY].outputs[0].default_value == 0.5

    image = vol.bb_volume.image
    before = np.array(image.pixels[:], dtype=np.float32)
    path = str(tmp_path / "scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    vol = bpy.context.scene.bb_active_volume
    image = vol.bb_volume.image
    assert image.packed_file is not None
    after = np.array(image.pixels[:], dtype=np.float32)
    assert np.array_equal(before, after)
    assert bpy.data.objects[f"{vol.name} coronal"].active_material.bb_slice.colormap == "HOT"
