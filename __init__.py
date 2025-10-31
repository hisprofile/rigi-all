bl_info = {
    "name": "Rigi-All",
    "description": "Speeds up the Rigify process",
    "author": "hisanimations",
    "version": (1, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Rigi-All",
    "warning": "", # used for warning icon and text in addons panel
    "doc_url": "https://github.com/hisprofile/rigi-all/tree/main",
    "support": "COMMUNITY",
    "category": "Rigging",
}

from . import (
    ambidextrous_operators,
    main,
    operators,
    panel
)

def register():
    ambidextrous_operators.register()
    main.register()
    operators.register()
    panel.register()

def unregister():
    ambidextrous_operators.unregister()
    main.unregister()
    operators.unregister()
    panel.unregister()

if __name__ == '__main__':
    register()