"""Shader node trees used to display volume slices.

For each volume:
  * "BB Fetch <name>": reads one voxel (integer i, j, k) from the atlas image.
  * "BB Sampler <name>": maps the shading point to voxel coordinates through the
    volume object's space and samples the volume (nearest or trilinear).
    Outputs the voxel value (original units) and an "Inside" mask.

For each slice material: sampler -> window (Map Range) -> Color Ramp -> Emission,
mixed with a Transparent BSDF outside of the volume.
"""

import bpy

from . import colormaps

# Names of the nodes of a slice material driven by the material settings.
NODE_SAMPLER = "BB Sampler"
NODE_MIN = "BB Window Min"
NODE_MAX = "BB Window Max"
NODE_OPACITY = "BB Opacity"
NODE_CLIP = "BB Clip Below"
NODE_RAMP = "BB Colormap"


class Builder:
    """Small helper to create and link nodes with less boilerplate."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links
        self.column = 0
        self.row = 0

    def node(self, type_name, x=None, y=None, **props):
        node = self.nodes.new(type_name)
        for key, value in props.items():
            setattr(node, key, value)
        if x is None:
            self.row += 1
            x, y = self.column * 200, -self.row * 40
        node.location = (x, y)
        return node

    def next_column(self):
        self.column += 1
        self.row = 0

    def connect(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        elif value is not None:
            socket.default_value = value

    def math(self, op, a, b=None, c=None):
        node = self.node("ShaderNodeMath", operation=op)
        node.hide = True
        for socket, value in zip(node.inputs, (a, b, c)):
            self.connect(socket, value)
        return node.outputs[0]

    def vmath(self, op, a, b=None):
        node = self.node("ShaderNodeVectorMath", operation=op)
        node.hide = True
        for socket, value in zip(node.inputs, (a, b)):
            self.connect(socket, value)
        out = node.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else node.outputs["Vector"]
        return out

    def separate(self, vector):
        node = self.node("ShaderNodeSeparateXYZ")
        node.hide = True
        self.connect(node.inputs[0], vector)
        return node.outputs[0], node.outputs[1], node.outputs[2]

    def combine(self, x, y, z):
        node = self.node("ShaderNodeCombineXYZ")
        node.hide = True
        for socket, value in zip(node.inputs, (x, y, z)):
            self.connect(socket, value)
        return node.outputs[0]

    def clamp(self, value, lo, hi):
        return self.math("MINIMUM", self.math("MAXIMUM", value, lo), hi)

    def lerp(self, a, b, t):
        return self.math("MULTIPLY_ADD", self.math("SUBTRACT", b, a), t, a)


def _new_group(name, sockets):
    """Get or create an empty node group with the given interface.

    The interface is kept when it already matches so that links from the group
    nodes using it (in materials) survive a rebuild.
    `sockets` is a list of (name, "INPUT" | "OUTPUT", socket type).
    """
    group = bpy.data.node_groups.get(name)
    if group is None:
        group = bpy.data.node_groups.new(name, "ShaderNodeTree")
    group.nodes.clear()
    current = [
        (item.name, item.in_out, item.socket_type)
        for item in group.interface.items_tree
        if item.item_type == "SOCKET"
    ]
    if current != list(sockets):
        group.interface.clear()
        for socket_name, in_out, socket_type in sockets:
            group.interface.new_socket(socket_name, in_out=in_out, socket_type=socket_type)
    return group


def build_fetch_group(volume):
    """Group reading the normalised value of voxel (i, j, k) from the atlas."""
    settings = volume.bb_volume
    nx, ny, nz = settings.dims
    cols, rows = settings.atlas_grid
    width, height = nx * cols, ny * rows

    group = _new_group(
        f"BB Fetch {volume.name}",
        [("Voxel", "INPUT", "NodeSocketVector"), ("Value", "OUTPUT", "NodeSocketFloat")],
    )
    b = Builder(group)
    gin = b.node("NodeGroupInput", x=-400, y=0)
    gout = b.node("NodeGroupOutput", x=1600, y=0)

    i, j, k = b.separate(gin.outputs["Voxel"])
    i = b.clamp(i, 0.0, nx - 1.0)
    j = b.clamp(j, 0.0, ny - 1.0)
    k = b.clamp(k, 0.0, nz - 1.0)
    b.next_column()
    layer = b.math("FLOOR", b.math("DIVIDE", k, 4.0))
    channel = b.math("MULTIPLY_ADD", layer, -4.0, k)
    row = b.math("FLOOR", b.math("DIVIDE", layer, float(cols)))
    col = b.math("MULTIPLY_ADD", row, -float(cols), layer)
    b.next_column()
    u = b.math("DIVIDE", b.math("ADD", b.math("MULTIPLY_ADD", col, float(nx), i), 0.5), float(width))
    v = b.math("DIVIDE", b.math("ADD", b.math("MULTIPLY_ADD", row, float(ny), j), 0.5), float(height))
    uv = b.combine(u, v, 0.0)
    b.next_column()

    tex = b.node("ShaderNodeTexImage", interpolation="Closest", extension="EXTEND")
    tex.image = settings.image
    b.connect(tex.inputs["Vector"], uv)
    sep = b.node("ShaderNodeSeparateColor")
    b.connect(sep.inputs[0], tex.outputs["Color"])
    b.next_column()
    channels = [sep.outputs[0], sep.outputs[1], sep.outputs[2], tex.outputs["Alpha"]]
    total = None
    for index, value in enumerate(channels):
        term = b.math("MULTIPLY", value, b.math("COMPARE", channel, float(index), 0.5))
        total = term if total is None else b.math("ADD", total, term)
    b.connect(gout.inputs["Value"], total)
    return group


def build_sampler_group(volume):
    """Group sampling the volume at the shading point (no inputs needed)."""
    settings = volume.bb_volume
    fetch = build_fetch_group(volume)
    nx, ny, nz = settings.dims
    m = settings.local_to_voxel  # 4x4 row-major, object space -> voxel indices

    group = _new_group(
        f"BB Sampler {volume.name}",
        [
            ("Value", "OUTPUT", "NodeSocketFloat"),
            ("Inside", "OUTPUT", "NodeSocketFloat"),
            ("Voxel", "OUTPUT", "NodeSocketVector"),
        ],
    )
    b = Builder(group)
    gout = b.node("NodeGroupOutput", x=2000, y=0)

    texco = b.node("ShaderNodeTexCoord")
    texco.object = volume
    local = texco.outputs["Object"]
    b.next_column()
    coords = []
    for r in range(3):
        row = (m[4 * r], m[4 * r + 1], m[4 * r + 2])
        coords.append(b.math("ADD", b.vmath("DOT_PRODUCT", local, row), m[4 * r + 3]))
    voxel = b.combine(*coords)
    b.next_column()

    inside = None
    for coord, n in zip(coords, (nx, ny, nz)):
        inside_axis = b.math(
            "MULTIPLY", b.math("GREATER_THAN", coord, -0.5), b.math("LESS_THAN", coord, n - 0.5)
        )
        inside = inside_axis if inside is None else b.math("MULTIPLY", inside, inside_axis)
    b.next_column()

    def fetch_at(vector):
        node = b.node("ShaderNodeGroup", node_tree=fetch)
        node.hide = True
        b.connect(node.inputs["Voxel"], vector)
        return node.outputs["Value"]

    if settings.interpolation == "NEAREST":
        value = fetch_at(b.vmath("FLOOR", b.vmath("ADD", voxel, (0.5, 0.5, 0.5))))
    else:
        base = b.vmath("FLOOR", voxel)
        tx, ty, tz = b.separate(b.vmath("SUBTRACT", voxel, base))
        b.next_column()
        corners = {}
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    corners[dx, dy, dz] = fetch_at(b.vmath("ADD", base, (dx, dy, dz)))
        b.next_column()
        cy = {}
        for dy in (0, 1):
            for dz in (0, 1):
                cy[dy, dz] = b.lerp(corners[0, dy, dz], corners[1, dy, dz], tx)
        cz = {dz: b.lerp(cy[0, dz], cy[1, dz], ty) for dz in (0, 1)}
        value = b.lerp(cz[0], cz[1], tz)
    b.next_column()
    span = settings.value_max - settings.value_min
    value = b.math("MULTIPLY_ADD", value, span, settings.value_min)
    b.connect(gout.inputs["Value"], value)
    b.connect(gout.inputs["Inside"], inside)
    b.connect(gout.inputs["Voxel"], voxel)
    return group


def create_slice_material(volume, name=None):
    """New material showing `volume` on any surface it is assigned to."""
    settings = volume.bb_volume
    mat = bpy.data.materials.new(name or f"BB Slice {volume.name}")
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    mat.use_backface_culling = False
    tree = mat.node_tree
    tree.nodes.clear()
    b = Builder(tree)

    sampler = b.node("ShaderNodeGroup", x=0, y=0, node_tree=settings.sampler, name=NODE_SAMPLER, label=NODE_SAMPLER)
    vmin = b.node("ShaderNodeValue", x=0, y=-200, name=NODE_MIN, label=NODE_MIN)
    vmax = b.node("ShaderNodeValue", x=0, y=-300, name=NODE_MAX, label=NODE_MAX)
    opacity = b.node("ShaderNodeValue", x=0, y=-400, name=NODE_OPACITY, label=NODE_OPACITY)
    clip = b.node("ShaderNodeValue", x=0, y=-500, name=NODE_CLIP, label=NODE_CLIP)
    vmin.outputs[0].default_value = settings.window_min
    vmax.outputs[0].default_value = settings.window_max
    opacity.outputs[0].default_value = 1.0
    clip.outputs[0].default_value = 0.0

    window = b.node("ShaderNodeMapRange", x=250, y=0, clamp=True)
    b.connect(window.inputs["Value"], sampler.outputs["Value"])
    b.connect(window.inputs["From Min"], vmin.outputs[0])
    b.connect(window.inputs["From Max"], vmax.outputs[0])
    ramp = b.node("ShaderNodeValToRGB", x=450, y=0, name=NODE_RAMP, label=NODE_RAMP)
    colormaps.apply_colormap(ramp.color_ramp, "GRAY")
    b.connect(ramp.inputs["Fac"], window.outputs["Result"])
    emission = b.node("ShaderNodeEmission", x=750, y=0)
    b.connect(emission.inputs["Color"], ramp.outputs["Color"])

    # alpha = inside * opacity * max(value >= min, 1 - clip)
    b.column, b.row = 1, 8
    above = b.math("SUBTRACT", 1.0, b.math("LESS_THAN", sampler.outputs["Value"], vmin.outputs[0]))
    keep = b.math("MAXIMUM", above, b.math("SUBTRACT", 1.0, clip.outputs[0]))
    alpha = b.math("MULTIPLY", b.math("MULTIPLY", sampler.outputs["Inside"], opacity.outputs[0]), keep)

    transparent = b.node("ShaderNodeBsdfTransparent", x=750, y=-150)
    mix = b.node("ShaderNodeMixShader", x=950, y=0)
    b.connect(mix.inputs[0], alpha)
    b.connect(mix.inputs[1], transparent.outputs[0])
    b.connect(mix.inputs[2], emission.outputs[0])
    out = b.node("ShaderNodeOutputMaterial", x=1150, y=0)
    b.connect(out.inputs["Surface"], mix.outputs[0])

    ms = mat.bb_slice
    ms.volume = volume
    ms.window_min = settings.window_min
    ms.window_max = settings.window_max
    ms.colormap = "GRAY"
    return mat


def slice_nodes(mat):
    if mat is None or mat.node_tree is None:
        return None
    nodes = mat.node_tree.nodes
    names = (NODE_SAMPLER, NODE_MIN, NODE_MAX, NODE_OPACITY, NODE_CLIP, NODE_RAMP)
    if not all(n in nodes for n in names):
        return None
    return {n: nodes[n] for n in names}
