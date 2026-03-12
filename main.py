import bpy
from bpy.types import PropertyGroup, AddonPreferences
from bpy.utils import register_classes_factory
from bpy.props import (BoolProperty, StringProperty, PointerProperty, EnumProperty, FloatProperty, CollectionProperty, IntProperty)
from .panel import RIGIALL_PT_panel

symmetries = [
    ('left', 'right'),
    ('Left', 'Right'),
    ('LEFT', 'RIGHT'),
    ('l', 'r'),
    ('L', 'R')
]
symmetry_swap = {a: b for a, b in symmetries for a, b in [(a, b), (b, a)]}
symmetries_unraveled = [side for pair in symmetries for side in pair]

def swap_name(name: str):
    for symmetry in symmetries_unraveled:
        if name.endswith(symmetry):
            return name.rstrip(symmetry) + symmetry_swap[symmetry]
        if name.startswith(symmetry):
            return symmetry_swap[symmetry] + name.lstrip(symmetry)
    return ''

def get_bone_chains(context: bpy.types.Context, get_symmetry: bool = True) -> list[list[bpy.types.PoseBone]]:
    props = context.window_manager.rigiall_props
    all_chains = []
    current_chain = []
    all_chains.append(current_chain)

    bones = list(context.selected_pose_bones)
    additional = []
    pose_bones = context.object.pose.bones

    if get_symmetry:
        def get_symmetrical_bone(name: str):
            for symmetry in symmetries_unraveled:
                if name.endswith(symmetry) and (symmetrical_bone := pose_bones.get(name.rstrip(symmetry) + symmetry_swap[symmetry])):
                    return symmetrical_bone
                if name.startswith(symmetry) and (symmetrical_bone := pose_bones.get(symmetry_swap[symmetry] + name.lstrip(symmetry))):
                    return symmetrical_bone
            return None

        for bone in bones:
            if (sym_bone := get_symmetrical_bone(bone.name)):
                if sym_bone in bones: continue
                additional.append(sym_bone)
                
        bones.extend(additional)

    prior_bone = bones.pop(0)
    current_chain.append(prior_bone)

    while bones:
        current_bone = bones.pop(0)
        if current_bone.parent != prior_bone:
            current_chain = []
            all_chains.append(current_chain)
        current_chain.append(current_bone)
        prior_bone = current_bone

    return all_chains

def is_armature(self, a):
    return a.type == 'ARMATURE'

def iter_two(iter):
    iter = list(iter)
    prior = iter.pop(0)
    while iter:
        new = iter.pop(0)
        yield prior, new
        prior = new

def connect_chains(chains, edits):
    for chain in chains:
        chain = tuple((bone.name for bone in chain))
        for prior, next in iter_two(chain):
            edits[prior].tail = edits[next].head
            edits[next].use_connect = True

def initialize_finalize_script(context: bpy.types.Context):
    import os
    root = os.path.dirname(__file__)
    finalize_script_path = os.path.join(root, 'assets', 'FINALIZE_SCRIPT.py')
    data = context.blend_data
    finalize_name = 'RIGI-ALL_FINALIZE_SCRIPT'
    if not (finalize_script := data.texts.get(finalize_name)):
        finalize_script = data.texts.new(finalize_name)
        with open(finalize_script_path, 'r') as file:
            finalize_script.write(file.read())
    return finalize_script

def initialize_wire_to_curve(context: bpy.types.Context):
    import os
    root = os.path.dirname(__file__)
    blend_data = context.blend_data
    if bpy.app.version >= (4, 5, 0):
        if (ng := blend_data.node_groups.get('Rigi-All Wire to Curve')):
            return ng
        with bpy.data.libraries.load(os.path.join(root, 'assets', 'make_bones_renderable_wire_to_curve.blend')) as (src, dst):
            dst.node_groups = ['Rigi-All Wire to Curve']
    else:
        if (ng := blend_data.node_groups.get('Rigi-All Wire to Curve -4.5')):
            return ng
        with bpy.data.libraries.load(os.path.join(root, 'assets', 'make_bones_renderable_wire_to_curve.blend')) as (src, dst):
            dst.node_groups = ['Rigi-All Wire to Curve -4.5']

    ng: bpy.types.GeometryNodeTree = dst.node_groups[0]
    ng.nodes['CURVE_THICKNESS'].inputs[1].default_value = context.window_manager.rigiall_props.wire_thickness

    return dst.node_groups[0]

class null:
    weight = 0.0
    def __getattr__(self, _):
        return self
    def __bool__(self):
        return False
    def __int__(self):
        return 0
    def __eq__(self, _):
        return False
    def __repr__(self):
        return 'None'

null = null()

class rigiall_prefs(AddonPreferences):
    bl_idname = __package__

    def category_update(self, context):
        panel = RIGIALL_PT_panel
        if 'bl_rna' in panel.__dict__:
            bpy.utils.unregister_class(panel)
        panel.bl_category = self.category
        bpy.utils.register_class(panel)

    category: StringProperty(name='Category', description="Rigi-All's category placement in the viewport", default='Rigi-All', update=category_update)

    def draw(self, context):
        layout = self.layout
        layout.label(text='Change Category:')
        layout.prop(self, 'category', text='')

class rigiall_group(PropertyGroup):
    ik_fingers: BoolProperty(name='IK Fingers', default=False)
    keywords: StringProperty(name='', description="Replaces/deletes symmetry keywords to fit Blender's symmetry naming scheme")
    symmetry_left_keyword: StringProperty(name='Symmetry Left Keyword', description='Fixes left symmetry keywords to ensure they are compatible with Blender\'s naming scheme')
    symmetry_right_keyword: StringProperty(name='Symmetry Right Keyword', description='Fixes right symmetry keywords to ensure they are compatible with Blender\'s naming scheme')
    fix_symmetry: BoolProperty(name='Fix Symmetry Name', description='Disable if bones already end in ".L/_L" or ".R/_R"', default=False)

    parasite: PointerProperty(type=bpy.types.Object, poll=is_armature)
    host: PointerProperty(type=bpy.types.Object, poll=is_armature)

    automatic_symmetry: BoolProperty(default=True, name='Auto-complete Other Side', description='Speed up the rigging process by automatically determining which sides are  ')

    symmetry_mode: EnumProperty(items=[
        ('X_POSITIVE', '+X', 'The right side of the armature is on the positive side of the X axis.'),
        ('X_NEGATIVE', '-X', 'The right side of the armature is on the negative side of the X axis.'),
        #('Y_POSITIVE', '+Y', 'The right side of the armature is on the positive side of the Y axis.'),
        #('Y_NEGATIVE', '-Y', 'The right side of the armature is on the negative side of the Y axis.'),
        ],
        name='Right side of the rig is on...',
        description='The right side of the rig should be on this side of this axis',
        default='X_NEGATIVE'
    )

    view: EnumProperty(
        items=(
            ('RIGGING', 'Rigging', 'View the rigging tools', 'ARMATURE_DATA', 0),
            ('CLEAN_UP', 'Clean up', 'View the clean up tools', 'BRUSH_DATA', 1),
            ('MISCELLANEOUS', 'Misc.', 'View miscellaneous tools', 'DISC', 2),
            #None,
            #('SETTINGS', '', 'Settings', 'TOOL_SETTINGS', 3)
        ),
        name='View',
        description='Set the view mode for Rigi-All',
        default='RIGGING'
    )

    wire_thickness: FloatProperty(name='Wire Thickness', default=0.05)

class rigiall_bodygroup_item(PropertyGroup):
    object: PointerProperty(
        type=bpy.types.Object,
        name='Object',
        description="The object who's visibility will be controlled"
    )
    name: StringProperty(
        name='Name',
        description="Name of the visibility switch item. Object's name if empty",
        default=''
    )
    description: StringProperty(
        name='Description',
        description='Description of the visibility switch item',
        default=''
    )
    icon: StringProperty(
        name='Icon',
        description='Icon for the visibility switch item',
        default=''
    )


class rigiall_bodygroup_menu(PropertyGroup):
    name: StringProperty(
        name='Property Name',
        description='Name of the custom property to store this visibility switch on',
        default='Visibility Switch'
    )
    menu_items: CollectionProperty(
        type=rigiall_bodygroup_item,
        name='Menu Items',
        description='Menu items'
    )

class rigiall_bodygroup_helper(PropertyGroup):
    bodygroup_menus: CollectionProperty(
        type=rigiall_bodygroup_menu,
        name='Bodygroup Menus',
        description='Bodygroup menus'
    )
    index: IntProperty(options=set(), min=0)
    active_item: IntProperty(default=-1, min=-1)

    # for controller subjects
    visibility_controller: PointerProperty(type=bpy.types.Object)
    switch_name: StringProperty()

    @classmethod
    def register(cls):
        bpy.types.Object.rigiall_bodygroup_helper = PointerProperty(
            type=cls,
            name='Rigi-All Bodygroup Helper',
            description='Top-level container for all bodygroup menus & items'
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Object.rigiall_bodygroup_helper

classes = [
    rigiall_prefs,
    rigiall_group,
    rigiall_bodygroup_item,
    rigiall_bodygroup_menu,
    rigiall_bodygroup_helper,
]

r, ur = register_classes_factory(classes)

def register():
    r()
    bpy.types.WindowManager.rigiall_props = bpy.props.PointerProperty(type=rigiall_group)
    bpy.types.PoseBone.rigi_all_mark = bpy.props.BoolProperty()
def unregister():
    ur()
    del bpy.types.WindowManager.rigiall_props
    del bpy.types.PoseBone.rigi_all_mark