"""Colour maps applied to slice values through a Color Ramp node.

Stops are given in display (sRGB) space and are densified then converted to
scene-linear colours, so that the ramp looks right with the "Standard" view
transform (a gray ramp gives perceptually linear gray levels on screen).
"""

import numpy as np

# name -> (label, list of sRGB stops)
COLORMAPS = {
    "GRAY": ("Gray", [(0, 0, 0), (1, 1, 1)]),
    "HOT": ("Hot", [(0, 0, 0), (0.9, 0, 0), (1, 0.8, 0), (1, 1, 1)]),
    "INFERNO": (
        "Inferno",
        [(0.0015, 0.0005, 0.0139), (0.258, 0.039, 0.406), (0.578, 0.148, 0.404),
         (0.865, 0.317, 0.226), (0.988, 0.645, 0.040), (0.988, 0.998, 0.645)],
    ),
    "VIRIDIS": (
        "Viridis",
        [(0.267, 0.005, 0.329), (0.229, 0.322, 0.546), (0.128, 0.567, 0.551),
         (0.369, 0.789, 0.383), (0.993, 0.906, 0.144)],
    ),
    "JET": (
        "Jet",
        [(0, 0, 0.5), (0, 0, 1), (0, 1, 1), (1, 1, 0), (1, 0, 0), (0.5, 0, 0)],
    ),
    "COOLWARM": (
        "Cool-warm (diverging)",
        [(0.230, 0.299, 0.754), (0.865, 0.865, 0.865), (0.706, 0.016, 0.150)],
    ),
    "RED": ("Red", [(0, 0, 0), (1, 0, 0)]),
    "GREEN": ("Green", [(0, 0, 0), (0, 1, 0)]),
    "BLUE": ("Blue", [(0, 0, 0), (0, 0.3, 1)]),
}

ENUM_ITEMS = [(key, label, "") for key, (label, _) in COLORMAPS.items()] + [
    ("CUSTOM", "Custom", "Edit the color ramp freely")
]


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def ramp_stops(name, count=16):
    """List of (position, linear RGBA) for the named colormap."""
    stops = np.asarray(COLORMAPS[name][1], dtype=np.float64)
    src = np.linspace(0.0, 1.0, len(stops))
    pos = np.linspace(0.0, 1.0, count)
    srgb = np.stack([np.interp(pos, src, stops[:, c]) for c in range(3)], axis=1)
    lin = srgb_to_linear(srgb)
    return [(float(p), (*map(float, rgb), 1.0)) for p, rgb in zip(pos, lin)]


def apply_colormap(color_ramp, name):
    if name not in COLORMAPS:
        return
    stops = ramp_stops(name)
    elements = color_ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    elements[0].position = stops[0][0]
    elements[0].color = stops[0][1]
    for pos, color in stops[1:]:
        elements.new(pos).color = color
    color_ramp.color_mode = "RGB"
    color_ramp.interpolation = "LINEAR"
