# nibablender

Import a 3D medical image with Nibabel and use it as a 3D texture for any mesh.

## Introduction

This project is in very early development stage. It relies on Python language and
combines several thirdparty libraries and technologies related to Python or Blender :

## Installation

This installation process is just a list to remember all the steps used to configure 
Blender to make it support Nibabel and Cython.

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

3. Download and setup NibaBlender

It is necessary for the compilation of cython modules to add Python include files that are not included in Blender's Python distribution.
Then Cython modules can be compiled. Be sure that required compilation tools are installed on your system.

```
"$BLPIP" install git+https://github.com/sapetnioc/nibablender
wget https://www.python.org/ftp/python/$BLPYTHON_VERSION/Python-$BLPYTHON_VERSION.tar.xz
tar xf Python-$BLPYTHON_VERSION.tar.xz
mv Python-$BLPYTHON_VERSION/Include/* "$BLPYTHON_DIR/include/python$BLPYTHON_SHORT_VERSION"
rm -r Python-$BLPYTHON_VERSION Python-$BLPYTHON_VERSION.tar.xz
"$BLPYTHON_DIR/bin/cythonize" -i "$BLPYTHON_DIR/lib/python3.10/site-packages/nibablender/optimized.pyx"
```

4. Create scene

To date there is a single proof of concept command that loads a NIFTI image provided by Nibabel and setup a material on the cube of the default Blender scene. This command must be launched from Python within Blender:

```
import nibablender
nibablender.create_material()
```
