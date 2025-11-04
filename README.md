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

## Compile blender with pixi

In order to be able to use a specific Python version compatible with BrainVISA conda packages, I chose to compile Blender. Here is how I compiled Blender 5.0 using Pixi:

```sh
pixi init blender-pixi
cd blender-pixi
# The initial list of packages comes from Blender compilation documentation.
# I modified it until I was able to compile.
# Restriction on the Python version is probably useless at this time
pixi add python=3.11 pkgconfig gcc=14 gxx=14 make cmake git git-lfs subversion xorg-libx11 xorg-xproto xorg-kbproto xorg-libxxf86vm xorg-libxcursor xorg-libxi xorg-libxrandr xorg-libxinerama xorg-libsm libegl wayland wayland-protocols libxkbcommon dbus libegl-devel numpy requests zstandard

# I will use openvdb format. Therefore, I add the lib and the corresponding tools.
pixi add openvdb openvdb-tools

pixi shell

# Get Blender sources

git clone -b blender-v5.0-release https://projects.blender.org/blender/blender.git
cd blender

make update

# Ugly workaround: four MaterialX libraries are missing to link the blender executable
# How to fix this the right way ?
pixi add sed
cp -a lib/linux_x64/materialx/lib/* $CONDA_PREFIX/lib
sed -i 's/set(PLATFORM_LINKLIBS "")/set(PLATFORM_LINKLIBS "-lMaterialXRender -lMaterialXGenGlsl -lMaterialXGenMsl -lMaterialXGenShader")/g' CMakeLists.txt

# Fix a problem to find numpy includes
sed -i 's:set(_numpy_include "core/include"):set(_numpy_include "_core/include"):g' CMakeLists.txt

# Do not use Python provided by Blender
rm -r lib/linux_x64/python

# Blender compilation and installation
mkdir ../build_linux
cd ../build_linux
cmake ../blender -DCMAKE_INSTALL_PREFIX="$CONDA_PREFIX/blender" \
    -DPYTHON_NUMPY_INCLUDE_DIRS=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDEST'))")/site-packages/numpy/_core/include \
    -DWITH_PYTHON_INSTALL=OFF
    
make -j10
make install
ln -s ../blender/blender $CONDA_PREFIX/bin/blender
```
