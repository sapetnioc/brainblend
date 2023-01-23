# brainblend

This project is still a simple proof of concept. Its goal is to make it easy to import a 3D brain image into [Blender](https://www.blender.org/) and use it as dynamic 3D texture allowing to use any mesh to "cut" the volume in animated scenes. To date I just tried with one cropped MRI included in the [Nibabel](https://nipy.org/nibabel/) project and was able to create this animation:


https://user-images.githubusercontent.com/3062350/214160523-7f3689fa-b4cd-4f5a-a149-31f40d9644b6.mp4



With the appropriate settings, the 3D texture can be seen in real time in the Blender modeling interface as one can see in the following video: 


https://user-images.githubusercontent.com/3062350/214160159-f5956081-6f90-408a-bd94-0fee2c68ec38.mp4



## Disclaimer

I am really not an expert in Blender or Nibabel, I worked by trial and error until I got a result. There are mistakes and bad choices in this project. Hopefully it will improve with time.

## How it works

Long ago I had been able to use a voxel data structure to have a 3D texture in Blender. But voxel data have disappeared when the API had been completely rewritten and I do not know any equivalent in current Blender (latest release at the time of this writing is 3.4.1). Therefore, I choosed to convert the 3D image in a 2D texture and to use a dynamic mesh texture (based on shaders) that projects 3D coordinates to this 2D image.

For the creation of the 2D image from the 3D volume, I needed something faster than Python code. I tried Cython just to see if it could work within Blender. I was surprised how easy it was to make it work. I probably could have use Numpy but did not even try yet. 

For the dynamic texture I used shader nodes. The computation of a 2D coordinate from a 3D coordinate is done with a node using an [Open Shading Language (OSL)](https://github.com/AcademySoftwareFoundation/OpenShadingLanguage) script. For this to work in Blender, it seems necessary to use the "Cycles" renderer and to activate the support of OSL. These steps are done automatically via the Python API in the following instructions.

## Usage instructions

These instructions are supposed to be able to be copied and pasted into a terminal. They allow to create a material including the 3D texture of an image provided with Nibabel and to use this material on the cube of the default scene of Blender.

1. Download and install Blender

```
wget https://mirrors.dotsrc.org/blender/release/Blender3.4/blender-3.4.1-linux-x64.tar.xz
tar xf blender-3.4.1-linux-x64.tar.xz
rm blender-3.4.1-linux-x64.tar.xz
BLPYTHON_DIR="$PWD/blender-3.4.1-linux-x64/3.4/python"
BLPYTHON=`echo "$BLPYTHON_DIR/bin/"python*`
BLPYTHON_VERSION=`"$BLPYTHON" -c 'import platform; print(".".join(platform.python_version_tuple()))'`
BLPYTHON_SHORT_VERSION=`"$BLPYTHON" -c 'import platform; print(".".join(platform.python_version_tuple()[:2]))'`
```

2. Install pip and Nibabel

```
"$BLPYTHON" -m ensurepip
export BLPIP="$BLPYTHON_DIR/bin/pip3"
"$BLPIP" install --upgrade pip
"$BLPIP" install --upgrade nibabel cython
```

3. Download and setup brainblend

It is necessary for the compilation of cython modules to add Python include files that are not included in Blender's Python distribution.
Then Cython modules can be compiled. Be sure that required compilation tools are installed on your system.

```
"$BLPIP" install git+https://github.com/sapetnioc/brainblend
wget https://www.python.org/ftp/python/$BLPYTHON_VERSION/Python-$BLPYTHON_VERSION.tar.xz
tar xf Python-$BLPYTHON_VERSION.tar.xz
mv Python-$BLPYTHON_VERSION/Include/* "$BLPYTHON_DIR/include/python$BLPYTHON_SHORT_VERSION"
rm -r Python-$BLPYTHON_VERSION Python-$BLPYTHON_VERSION.tar.xz
"$BLPYTHON_DIR/bin/cythonize" -i "$BLPYTHON_DIR/lib/python3.10/site-packages/brainblend/optimized.pyx"
```

4. Create scene

To date there is a single proof of concept command that loads a NIFTI image provided by Nibabel and setup a material on the cube of the default Blender scene. This command must be launched from Python within Blender:

```
import brainblend
brainblend.create_material()
```

5. Check if it's working

Render an image (for instance by pressing F12). You should see a black cube with some MRI voxels in a corner. To see the texture in Blender, you must set the viewport shading to "rendered" (look at the circle icons in the top right corner of Blender's 3D views). You can now move the cube around to see the 3D texture.
