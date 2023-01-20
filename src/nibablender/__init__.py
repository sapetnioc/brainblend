from pathlib import Path

try:
    import bpy
except ImportError:
    raise RuntimeError('This module must be used from within Blender')

from mathutils import Vector

import nibabel
import numpy as np

import pyximport
pyximport.install()
from nibablender.optimized import array_to_rgba

flatten_3d = '''shader flatten_3d(
    int size_x = 25,
    int size_y = 41,
    int size_z = 33,
    float scale_x = 20,
    float scale_y = 20,
    float scale_z = 20,
    point coordinate = point(0, 0, 0),
    output int outside = 0,
    output point flattened = point(0, 0, 0))
{
    float x = coordinate.x * scale_x;
    if (x < 0 || x > size_x)
        outside = 1;
    int y = (int) round(coordinate.y * scale_y);
    if (y < 0 || y > size_y)
        outside = 1;
    y = y % size_y;
    int z = (int) round(coordinate.z * scale_z);
    if (z < 0 || z > size_z)
        outside = 1;
    z = z % size_z;
    flattened = point(
        x / size_x, 
        ((float) z * size_y + y) / (size_y * size_z),
        0);
}'''

color_or_default = '''shader color_or_default(
    color voxel_color = color(0, 0, 0),
    int outside = 0,
    color default_color = color(0, 0, 0),
    output color selected_color = color(0, 0, 0))
{
    if (outside) 
        selected_color = default_color;
    else
        selected_color = voxel_color;
}'''


def setup():
    # Set renderer that supports shading system
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.shading_system = True

    # ensure script texts are loaded in Blended
    if 'flatten_3d' not in bpy.data.texts:
        text = bpy.data.texts.new('flatten_3d')
        text.from_string(flatten_3d)
    if 'color_or_default' not in bpy.data.texts:
        text = bpy.data.texts.new('color_or_default')
        text.from_string(color_or_default)


def create_material():
    setup()

    # Load an image from Nibabel
    path = Path(nibabel.__file__).parent / 'tests' / 'data' / 'anatomical.nii'
    volume = nibabel.load(path)

    # Create 2D image from 3D volume
    name = path.name
    image = bpy.data.images.new(name, volume.shape[2], volume.shape[0] * volume.shape[1])
    volume_rgba = array_to_rgba(volume.get_fdata(dtype=np.float32))
    image.pixels.foreach_set(volume_rgba.reshape(-1))

    # Create new material
    material = bpy.data.materials.new(name)
    # Enable shader nodes
    material.use_nodes = True
    # Remove main node
    nodes = material.node_tree.nodes 
    node = nodes['Principled BSDF']
    nodes.remove(node)
    
    # Create geometry node
    geometry_node = nodes.new('ShaderNodeNewGeometry')
    geometry_node.location = Vector((-542,143))

    # Create node converting 3D coordinates to 2D     
    flatten_3d = nodes.new('ShaderNodeScript')
    flatten_3d.script = bpy.data.texts['flatten_3d']
    #flatten_3d.size_z, flatten_3d.size_y, flatten_3d.size_x = image.shape
    flatten_3d.location = Vector((-330,177))

    # Create texture node with 2D image
    shader_image = nodes.new('ShaderNodeTexImage')
    shader_image.image = image
    shader_image.location = Vector((-244,430))

    # Create node selecting between 2D image color or
    # background color     
    color_or_default = nodes.new('ShaderNodeScript')
    color_or_default.script = bpy.data.texts['color_or_default']
    color_or_default.location = Vector((32,278))

    # Link nodes
    material.node_tree.links.new(
        geometry_node.outputs['Position'],
        flatten_3d.inputs['coordinate']
    )
    material.node_tree.links.new(
        flatten_3d.outputs['flattened'],
        shader_image.inputs['Vector']
    )
    material.node_tree.links.new(
        flatten_3d.outputs['outside'],
        color_or_default.inputs['outside']
    )
    material.node_tree.links.new(
        shader_image.outputs['Color'],
        color_or_default.inputs['voxel_color']
    )
    material.node_tree.links.new(
        color_or_default.outputs['selected_color'],
        nodes["Material Output"].inputs['Surface']
    )

    if 'Cube' in bpy.data.meshes:
        # assign new material to default cube
        bpy.data.meshes['Cube'].materials[0] = material
