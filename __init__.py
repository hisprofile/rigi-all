bl_info = {
    "name": "Rigi-All",
    "description": "Helps convert a humanoid rig to a Rigify rig",
    "author": "hisanimations",
    "version": (1, 1),
    "blender": (3, 4, 0),
    "location": "View3D > Rigi-All",
    "warning": "", # used for warning icon and text in addons panel
    "doc_url": "https://github.com/hisprofile/rigi-all/tree/main",
    "support": "COMMUNITY",
    "category": "Rigging",
}

import bpy
from bpy.types import Operator as ot
from bpy.props import BoolProperty as boolprop
from bpy.props import *
from math import degrees

mode = bpy.ops.object.mode_set

mod_bones = []

'''

To anyone who cares, bfl means Ball Flicker Licker, 
the original name of the addon.

'''

class bfl_OT_makeArm(ot):
    
    bl_idname = 'bfl.makearm'
    bl_label = 'Make Arm'
    bl_description = 'Select a chain of bones to make them a Rigify arm'
    isLeft: boolprop(name='isLeft', default=False)
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.scene.rigiall_props
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        obj.data.layers = [True]*32
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            for keyword in props.keywords.split(','):
                bone.name = bone.name.replace(keyword, '')
            if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')) and props.fix_symmetry:
                bone.name +='.L' if self.isLeft else '.R'
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
    
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        
        for n, bone in enumerate(bone_list):
            if not bone in mod_bones: mod_bones.append(bone)
            edits[bone].layers = [False if i != (7 if self.isLeft else 10) else True for i in range(32)]
            if n == 0: continue
            edits[bone].use_connect = True
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
                
        mode(mode='POSE')
        
        bones[0].rigify_type = 'limbs.arm'
        
        param = bones[0].rigify_parameters
        
        param.ik_local_location = False
        param.fk_layers = [False]*32
        param.tweak_layers = [False]*32
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Arm generated!')
        if self.isLeft:
            param.fk_layers[8] = True
            param.tweak_layers[9] = True
            return {'FINISHED'}
        
        param.fk_layers[11] = True
        param.tweak_layers[12] = True
        return {'FINISHED'}
    
class bfl_OT_makeLeg(ot):
    
    bl_idname = 'bfl.makeleg'
    bl_label = 'Make leg'
    bl_description = 'Select a chain of bones to make them a Rigify leg'
    isLeft: boolprop(name='Is Left', default=False)
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = bpy.context.object
        obj.data.layers = [True]*32
        props = context.scene.rigiall_props
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            for keyword in props.keywords.split(','):
                bone.name = bone.name.replace(keyword, '')
            if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')) and props.fix_symmetry:
                bone.name +='.L' if self.isLeft else '.R'
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        
        for n, bone in enumerate(bone_list):
            if not bone in mod_bones: mod_bones.append(bone)
            edits[bone].layers = [False if i != (13 if self.isLeft else 16) else True for i in range(32)]
              
            if n == 0: continue
            
            edits[bone].use_connect = True
            
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
                
        heel = edits.new('heel.L' if self.isLeft else 'heel.R')
        mod_bones.append('heel.L' if self.isLeft else 'heel.R')
        heel.parent = edits[bone_list[-2]]
        heel.head[0] = edits[bone_list[-2]].head[0]
        heel.tail[0] = heel.head[0]+0.1
        heel.head[2] = 0
        heel.tail[2] = 0
        heel.layers = [False if i != (13 if self.isLeft else 16) else True for i in range(32)]
        
        mode(mode='POSE')
        
        bones[0].rigify_type = 'limbs.leg'
        
        param = bones[0].rigify_parameters
        
        param.ik_local_location = False
        param.fk_layers = [False]*32
        param.tweak_layers = [False]*32
        param.extra_ik_toe = True
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Leg generated! Adjust the heel bone in edit mode!')
        if self.isLeft:
            param.fk_layers[14] = True
            param.tweak_layers[15] = True
            
            return {'FINISHED'}
        
        param.fk_layers[17] = True
        param.tweak_layers[18] = True
        
        return {'FINISHED'}
        
class bfl_OT_makeSpine(ot):
    
    bl_idname = 'bfl.makespine'
    bl_label = 'Make Spine'
    bl_description = 'Select a chain of bones to make them a Rigify Spine'
    bl_options = {'UNDO'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text='Make sure that the pelvis is the beginning of the spine chain,')
        layout.label(text='AND that the pelvis is the absolue root of the rig.')
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = bpy.context.object
        obj.data.layers = [True]*32
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        bones = bpy.context.selected_pose_bones
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        for n, bone in enumerate(bone_list):
            if not bone in mod_bones: mod_bones.append(bone)
            edits[bone].layers = [False if i != 3 else True for i in range(32)]
            if n == 0: continue
            edits[bone].use_connect = True
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
        
        mode(mode='POSE')
        bones[0].rigify_type = 'spines.basic_spine'
        param = bones[0].rigify_parameters
        param.fk_layers = [False]*32
        param.tweak_layers = [False]*32
        param.fk_layers[4] = True
        param.tweak_layers[4] = True
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Spine generated!')
        return {'FINISHED'}
    
class bfl_OT_makeNeck(ot):
    
    bl_idname = 'bfl.makeneck'
    bl_label = 'Make Neck/Head'
    bl_description = 'Select a chain of bones to make them a Rigify Head'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_pose_bones) > 1

    def execute(self, context):    
        obj = bpy.context.object
        obj.data.layers = [True]*32
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        bones = bpy.context.selected_pose_bones
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        edits[bone_list[0]].parent.tail = edits[bone_list[0]].head
        
        for n, bone in enumerate(bone_list):
            if not bone in mod_bones: mod_bones.append(bone)
            edits[bone].layers = [False if i != 3 else True for i in range(32)]
            if n == 0: continue
            edits[bone].use_connect = True      
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
        
        mode(mode='POSE')
        bones[0].rigify_type = 'spines.super_head'
        param = bones[0].rigify_parameters
        param.tweak_layers = [False]*32
        param.tweak_layers[4] = True
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Neck and head generated!')
        return {'FINISHED'}
    
class bfl_OT_makeFingers(ot):
    
    bl_idname = 'bfl.makefingers'
    bl_label = 'Make Fingers'
    bl_description = 'Select a chain of bones to make Rigify fingers'
    bl_options = {'UNDO'}
    isLeft: boolprop(name='isLeft', default=False)
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.selected_pose_bones) > 1

    def execute(self, context):
        obj = bpy.context.object
        props = context.scene.rigiall_props
        obj.data.layers = [True]*32
        props = context.scene.rigiall_props
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            for keyword in props.keywords.split(','):
                bone.name = bone.name.replace(keyword, '')
            if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')) and props.fix_symmetry:
                bone.name +='.L' if self.isLeft else '.R'
        fingers = []
        current = []
        boneLast = None
        for bone in bones:
            if boneLast != None:
                if bone.parent != boneLast:
                    fingers.append(list(current))
                    current = []
            current.append(bone.name)
            if bone == bones[-1]:
                fingers.append(current)
                break
            boneLast = bone
            
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        for chain in fingers:
            edits[chain[0]].tail = edits[chain[1]].head
            for n, bone in enumerate(chain):
                if not bone in mod_bones: mod_bones.append(bone)
                edits[bone].layers = [False if i != 5 else True for i in range(32)]
                if n == 0: continue
            
                edits[bone].use_connect = True
            
                if chain[-1] != bone:
                    edits[bone].tail = edits[chain[n+1]].head
                    
        mode(mode='POSE')
        for chain in fingers:
            bone = bpy.context.object.pose.bones.get(chain[0])
            bone.rigify_type = 'limbs.super_finger'
            param = bone.rigify_parameters
            param.make_extra_ik_control = props.ik_fingers
            param.tweak_layers = [False]*32
            param.tweak_layers[6] = True
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Fingers generated!')
        return {'FINISHED'}
    
class bfl_OT_90roll(ot):
    bl_idname = 'bfl.adjustroll'
    bl_label = 'Adjust Roll by 90°'
    bl_description = 'Adjust roll by 90° or -90°'
    bl_options = {'UNDO'}
    
    roll: FloatProperty(default=0)
    
    def execute(self, context):
        import math
        bones = [i.name for i in context.selected_pose_bones]
        mode(mode='EDIT')
        edits = bpy.context.object.data.edit_bones
        for bone in bones:
            edits[bone].roll += math.radians(self.roll)
        mode(mode='POSE')
        return {'FINISHED'}
        
class bfl_OT_0roll(ot):
    bl_idname = 'bfl.noroll'
    bl_label = 'Set Roll to 0°'
    bl_description = "Sets a bone's roll to 0°"
    bl_options = {'UNDO'}

    def execute(self, context):
        import math
        bones = [i.name for i in context.selected_pose_bones]
        mode(mode='EDIT')
        edits = bpy.context.object.data.edit_bones
        for bone in bones:
            edits[bone].roll = 0
        mode(mode='POSE')
        return {'FINISHED'}        
        
class bfl_OT_makeShoulder(ot):
    
    bl_idname = 'bfl.makeshoulder'
    bl_label = 'Make Shoulders'
    bl_description = 'Select bones to make them shoulders'
    bl_options = {'UNDO'}
    isLeft: boolprop(name='isLeft', default=False)
    
    def execute(self, context):
        obj = bpy.context.object
        obj.data.layers = [True]*32
        props = context.scene.rigiall_props
        if obj.data.get('mod_bones') == None:
            obj.data['mod_bones'] = []
        mod_bones = list(obj.data.get('mod_bones'))
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            for keyword in props.keywords.split(','):
                bone.name = bone.name.replace(keyword, '')
            if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')) and props.fix_symmetry:
                bone.name +='.L' if self.isLeft else '.R'
            if not bone.name in mod_bones: mod_bones.append(bone.name)
            bone.rigify_type = 'basic.super_copy'
            bone.bone.layers = [False if i != 3 else True for i in range(32)]
            param = bone.rigify_parameters
            param.make_control = True
            param.make_widget = True
            param.super_copy_widget_type = 'shoulder'
            param.make_deform = True
        obj.data['mod_bones'] = mod_bones
        self.report({'INFO'}, 'Shoulder generated!')
        return {'FINISHED'}
    
class bfl_OT_makeExtras(ot):
    bl_idname = 'bfl.extras'
    bl_label = 'Make Extras (Do This Last!)'
    bl_description = 'Preserve all unmodified bones when generating the rig. Do this last'
    bl_options = {'UNDO'}
    
    def execute(self, context):
        mod_bones = list(context.object.data.get('mod_bones'))
        for bone in context.object.pose.bones:
            if bone.name in mod_bones: continue
            bone.bone.layers = [False if i != 24 else True for i in range(32)]
            bone.rigify_type = 'basic.super_copy'
        self.report({'INFO'}, 'Extra bones preserved! Select them and assign widgets in the bone tab!')
        return {'FINISHED'}

class bfl_group(bpy.types.PropertyGroup):
    ik_fingers: boolprop(name='IK Fingers', default=False)
    keywords: StringProperty(name='', description="Replaces/deletes symmetry keywords to fit Blender's symmetry naming scheme")
    fix_symmetry: boolprop(name='Fix Symmetry', description='Disable if bones already end in ".L/_L" or ".R/_R"', default=True)

class bfl_OT_help(ot):
    bl_idname = 'bfl.symmetryhelp'
    bl_label = 'Symmetry Help'
    bl_description = 'Displays a menu showing what the symmetry keywords are meant for'
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.row().label(text='This helps to format bone names to make them compatible')
        layout.row().label(text='for symmetry posing. For example, if you have a pair of')
        layout.row().label(text='bones named "upper_r_arm.R" and "upper_l_arm.L",')
        layout.row().label(text='symmetry will not be supported. However, if you add')
        layout.row().label(text='"_l_,_r_" in the string field, then the bones will')
        layout.row().label(text='be renamed to "upperarm.R" and "upperarm.L",')
        layout.row().label(text='making them compatible with symmetry.')
        
class bfl_OT_initialize(ot):
    bl_idname = 'bfl.init'
    bl_label = 'Initialize Rig'
    bl_description = 'Initialize the rig with bonegroups and assigned layers.'
    bl_options = {'UNDO'}
    
    def execute(self, context):
        bpy.ops.pose.rigify_layer_init()
        bpy.ops.armature.rigify_add_bone_groups()
        layers = {
            0: ("Face", 1, 5),
            1: ("Face (Primary)", 2, 2),
            2: ("Face (Secondary)", 2, 3),
            3: ("Torso", 3, 3),
            4: ("Torso (Tweak)", 4, 4),
            5: ("Fingers", 5, 6),
            6: ("Fingers (Detail)", 6, 5),
            7: ("Arm.L (IK)", 7, 2),
            8: ("Arm.L (FK)", 8, 5),
            9: ("Arm.L (Tweak)", 9, 4),
            10: ("Arm.R (IK)", 7, 2),
            11: ("Arm.R (FK)", 8, 5),
            12: ("Arm.R (Tweak)", 9, 4),
            13: ("Leg.L (IK)", 10, 2),
            14: ("Leg.L (FK)", 11, 5),
            15: ("Leg.L (Tweak)", 12, 4),
            16: ("Leg.R (IK)", 10, 2),
            17: ("Leg.R (FK)", 11, 5),
            18: ("Leg.R (Tweak)", 12, 4),
            24: ("Extras", 1, 6),
            28: ("Root", 14, 1),
        }
        rLayers = bpy.context.object.data.rigify_layers
        for ind, items in layers.items():
            rLayers[ind].name = items[0]
            rLayers[ind].row = items[1]
            rLayers[ind].group = items[2]

        mode_bak = bpy.context.object.mode
        
        mode(mode='EDIT')

        for bone in bpy.context.object.data.edit_bones:
            bone.use_connect = False
            
        mode(mode=mode_bak)
        bpy.context.object.data['INITIALIZED'] = True

        return {'FINISHED'}
    
class bfl_OT_tweakMesh(ot):
    bl_idname = 'bfl.tweakmesh'
    bl_label = 'Fix Mesh'
    bl_description = 'Change the name of weight paints to be compatible with the rig.'
    bl_options = {'UNDO'}
    
    def execute(self, context):
        for group in context.object.vertex_groups:
            if not group.name.startswith('DEF-'):
                group.name = 'DEF-'+group.name
        return {'FINISHED'}
    
class BFL_PT_panel(bpy.types.Panel):
    """A Custom Panel in the Viewport Toolbar"""
    bl_label = 'Rigi-All'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Rigi-All'
    
    def draw(self, context):
        props = context.scene.rigiall_props
        layout = self.layout
        
        layout.row().operator('bfl.tweakmesh')
        
        layout.row().operator('bfl.init')
        
        if bpy.context.object.mode != 'POSE':
            layout.row().label(text='Enter pose mode!')
            return None
        
        if not bpy.context.object.data.get('INITIALIZED'):
             layout.row().label(text='Initialize the rig!')
             return None
        
        layout.row().label(text='Symmetry Keywords, separate with ","')
        row = layout.row()
        row.prop(props, 'keywords')
        row.operator('bfl.symmetryhelp', text='', icon='QUESTION')
        layout.row().prop(props, 'fix_symmetry')
        bone = context.active_pose_bone
        if bone != None:
            axis, roll = bone.bone.AxisRollFromMatrix(bone.matrix.to_3x3(), axis=bone.y_axis)
            layout.row().label(text=f'Current Bone Roll: {round(degrees(roll), 3)}')

        if len(bpy.context.selected_pose_bones) == 1:
            layout.label(text='Selected enough bones to form a chain!')
        
        layout.row().label(text='Arms:')
        op = layout.row().operator('bfl.makearm', text='Make Left Arm')
        op.isLeft = True
        op = layout.row().operator('bfl.makearm', text='Make Right Arm')
        op.isLeft = False
        
        op = layout.row().operator('bfl.makefingers', text='Make Left Fingers')
        op.isLeft = True
        op = layout.row().operator('bfl.makefingers', text='Make Right Fingers')
        op.isLeft = False
        layout.row().prop(context.scene.rigiall_props, 'ik_fingers')
        
        layout.row().label(text='Legs:')
        op = layout.row().operator('bfl.makeleg', text='Make Left Leg')
        op.isLeft = True
        op = layout.row().operator('bfl.makeleg', text='Make Right Leg')
        op.isLeft = False
        
        layout.row().label(text='Torso:')
        layout.row().operator('bfl.makespine', text='Make Spine')
        
        layout.row().operator('bfl.makeneck', text='Make Neck/Head')
        
        op = layout.row().operator('bfl.makeshoulder', text='Make Left Shoulder')
        op.isLeft = True
        op = layout.row().operator('bfl.makeshoulder', text='Make Right Shoulder')
        op.isLeft = False
        
        layout.row().label(text='Misc.')
        layout.row().operator('bfl.extras')
        op = layout.row().operator('bfl.adjustroll', text='Roll by 90°')
        op.roll = 90

        op = layout.row().operator('bfl.adjustroll', text='Roll by -90°')
        op.roll = -90
        
        layout.row().operator('bfl.noroll')

        #row.label(text='', icon='CHECKMARK' if bpy.context.object.data.get('bfl_LEFT') else 'CANCEL')
        
        
classes = [bfl_OT_makeArm,
    bfl_OT_makeFingers,
    bfl_OT_makeNeck,
    bfl_OT_makeShoulder,
    bfl_OT_makeSpine,
    bfl_OT_makeLeg,
    BFL_PT_panel,
    bfl_OT_makeExtras,
    bfl_OT_initialize,
    bfl_OT_tweakMesh,
    bfl_group,
    bfl_OT_help,
    bfl_OT_90roll,
    bfl_OT_0roll
    ]        

def register():
    for i in classes:
        bpy.utils.register_class(i)
    bpy.types.Scene.rigiall_props = bpy.props.PointerProperty(type=bfl_group)

def unregister():
    for i in reversed(classes):
        bpy.utils.unregister_class(i)
        
if __name__ == '__main__':
    register()
