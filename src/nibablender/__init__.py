from pathlib import Path

import bpy
import nibabel
import numpy as np

from nibablender.optimized import array_to_rgba

_shader_text = '''shader flatten_3d(
    int size_x = 25,
    int size_y = 41,
    int size_z = 33,
    float scale_x = 20,
    float scale_y = 20,
    float scale_z = 20,
    point coordinate = point(0, 0, 0),
    output point flattened = point(0, 0, 0))
{
    float x = coordinate.x * scale_x;
    int y = (int) round(coordinate.y * scale_y);
    y = y % size_x;
    int z = (int) round(coordinate.z * scale_z);
    z = z % size_z;
    flattened = point(
        x / size_x, 
        ((float) z * size_y + y) / (size_y * size_z),
        0);
}
'''

def create_material():
    # Set renderer that supports shading system
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.shading_system = True

    # Load an image from Nibabel
    path = Path(nibabel.__file__).parent / 'tests' / 'data' / 'anatomical.nii'
    volume = nibabel.load(path)

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
    # Create shader image node
    shader_image = nodes.new('ShaderNodeTexImage')
    shader_image.image = image
    # Link nodes
    material.node_tree.links.new(
        shader_image.outputs['Color'],
        nodes["Material Output"].inputs['Surface']
    )
    
    shader_text = bpy.data.texts.new(name)
    shader_text.from_string(_shader_text)
    shader_script = nodes.new('ShaderNodeScript')
    shader_script.script = shader_text
    material.node_tree.links.new(
        shader_script.outputs['flattened'],
        shader_image.inputs['Vector']
    )

    geometry_node = nodes.new('ShaderNodeNewGeometry')
    material.node_tree.links.new(
        geometry_node.outputs['Position'],
        shader_script.inputs['coordinate']
    )

    # assign new material to default cube
    bpy.data.meshes['Cube'].materials[0] = material