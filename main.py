import bpy
from bpy.types import PropertyGroup, AddonPreferences
from bpy.utils import register_classes_factory
from bpy.props import (BoolProperty, StringProperty, PointerProperty, EnumProperty)
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
    
def get_bone_chains(context: bpy.types.Context, get_symmetry: bool = True):
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
            if props.fix_symmetry:
                if (sym_bone := pose_bones.get(bone.name.replace(props.symmetry_left_keyword, props.symmetry_right_keyword))):
                    if sym_bone in bones: continue
                    additional.append(sym_bone)
                    continue
                if (sym_bone := pose_bones.get(bone.name.replace(props.symmetry_right_keyword, props.symmetry_left_keyword))):
                    if sym_bone in bones: continue
                    additional.append(sym_bone)
                    continue

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
    #new_text = data.texts.new('RIGI-ALL_FINALIZE_SCRIPT')

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

    automatic_symmetry: BoolProperty(default=True, name='Automatic Symmetry', description='Speed up the rigging process by automatically determining which sides are right and left')

    symmetry_mode: EnumProperty(items=[
        ('X_POSITIVE', '+X', 'The right side of the armature is on the positive side of the X axis.'),
        ('X_NEGATIVE', '-X', 'The right side of the armature is on the negative side of the X axis.'),
        ('Y_POSITIVE', '+Y', 'The right side of the armature is on the positive side of the Y axis.'),
        ('Y_NEGATIVE', '-Y', 'The right side of the armature is on the negative side of the Y axis.'),
        ],
        name='Symmetry Mode',
        description='Set the symmetry mode for automatic limb assignments. The right side of the rig should be on this side of this axis',
        default='X_NEGATIVE'
    )

    view: EnumProperty(
        items=(
            ('RIGGING', 'Rigging', 'View the rigging tools'),
            ('CLEAN_UP', 'Clean up', 'View the clean up tools')
        ),
        name='View',
        description='Set the view mode for Rigi-All',
        default='RIGGING'
    )
    
classes = [
    rigiall_prefs,
    rigiall_group
]

r, ur = register_classes_factory(classes)

def register():
    r()
    bpy.types.WindowManager.rigiall_props = bpy.props.PointerProperty(type=rigiall_group)
    bpy.types.PoseBone.rigi_all_mark = bpy.props.BoolProperty()
    #bpy.types.Bone.rigi_all_mark = bpy.props.BoolProperty()

def unregister():
    ur()
    del bpy.types.WindowManager.rigiall_props
    del bpy.types.PoseBone.rigi_all_mark
    #del bpy.types.Bone.rigi_all_mark