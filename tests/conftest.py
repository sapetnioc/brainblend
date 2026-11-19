"""Tests run with the `bpy` Python module (pip install bpy nibabel pytest)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

bpy = pytest.importorskip("bpy")


@pytest.fixture(scope="session", autouse=True)
def addon():
    import brainblend

    brainblend.register()
    yield brainblend
    brainblend.unregister()


@pytest.fixture
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    yield bpy.context.scene
