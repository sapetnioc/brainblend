# brainblend

This project is still a simple proof of concept. Its goal is to make it easy to import a 3D brain image into [Blender](https://www.blender.org/) and use it as dynamic 3D texture allowing to use any mesh to "cut" the volume in animated scenes. To date I just tried with one cropped MRI included in the [Nibabel](https://nipy.org/nibabel/) project and was able to create this animation:


https://user-images.githubusercontent.com/3062350/214160523-7f3689fa-b4cd-4f5a-a149-31f40d9644b6.mp4



With the appropriate settings, the 3D texture can be seen in real time in the Blender modeling interface as one can see in the following video: 


https://user-images.githubusercontent.com/3062350/214160159-f5956081-6f90-408a-bd94-0fee2c68ec38.mp4


## Compile blender with pixi

In order to be able to use a specific Python version compatible with BrainVISA conda packages, I chose to compile Blender. Here is how I compiled Blender 5.0 using Pixi:

```sh
# Create a Pixi environment in current directory
pixi init

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

blender
```
