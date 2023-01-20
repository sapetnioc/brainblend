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
export BLPYTHON_DIR="$PWD/blender-3.4.1-linux-x64/3.4/python"
export BLPYTHON="$BLPYTHON_DIR/bin/python3.10"
```

2. Install pip and Nibabel

```
"$BLPYTHON" -m ensurepip
export BLPIP="$BLPYTHON_DIR/bin/pip3"
"$BLPIP" install --upgrade pip
"$BLPIP" install --upgrade nibabel cython
```

3. Download and setup NibaBlender

```
"$BLPIP" install git+https://github.com/sapetnioc/nibablender
"$BLPYTHON_DIR/bin/cythonize" -i "$BLPYTHON_DIR/lib/python3.10/sit...
```


