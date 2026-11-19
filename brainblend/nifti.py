"""Loading of NIfTI volumes (via nibabel)."""

import os

import numpy as np


class VolumeData:
    """A 3D scalar volume with its voxel-to-millimetre affine."""

    def __init__(self, data, affine, name, filepath=""):
        self.data = data  # float32 array of shape (nx, ny, nz)
        self.affine = np.asarray(affine, dtype=np.float64)  # 4x4 voxel -> mm (RAS)
        self.name = name
        self.filepath = filepath

    @property
    def shape(self):
        return self.data.shape

    @property
    def voxel_size(self):
        return np.sqrt((self.affine[:3, :3] ** 2).sum(axis=0))


def volume_name(filepath):
    name = os.path.basename(filepath)
    for ext in (".nii.gz", ".nii", ".img", ".hdr", ".mgz", ".mgh"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name


def count_volumes(filepath):
    """Number of 3D volumes stored in the file (1 for a 3D image)."""
    import nibabel as nib

    img = nib.load(filepath)
    shape = img.shape
    return int(np.prod(shape[3:])) if len(shape) > 3 else 1


def load_nifti(filepath, volume_index=0):
    """Load one 3D volume from a NIfTI file (any format nibabel can read)."""
    try:
        import nibabel as nib
    except ImportError as e:  # pragma: no cover - depends on the install
        raise RuntimeError(
            "nibabel is not available. Install BrainBlend as a Blender extension "
            "(zip built with tools/build.py) so that its bundled wheels are installed."
        ) from e

    img = nib.load(filepath)
    shape = img.shape
    if len(shape) < 3:
        raise ValueError(f"{filepath}: expected a 3D or 4D image, got shape {shape}")
    if len(shape) == 3:
        data = img.get_fdata(dtype=np.float32)
    else:
        extra = shape[3:]
        n = int(np.prod(extra))
        if not 0 <= volume_index < n:
            raise ValueError(f"Volume index {volume_index} out of range (0..{n - 1})")
        index = np.unravel_index(volume_index, extra)
        data = np.asarray(img.dataobj[(Ellipsis,) + tuple(int(i) for i in index)])
    data = np.nan_to_num(np.asarray(data, dtype=np.float32), copy=False)
    return VolumeData(data, img.affine, volume_name(filepath), filepath)
