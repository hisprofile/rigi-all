bl_info = {
    "name": "Rigi-All",
    "description": "Helps convert a humanoid rig to a Rigify rig",
    "author": "hisanimations",
    "version": (1, 3),
    "blender": (4, 0, 0),
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


'''

To anyone who cares, bfl means Ball Flicker Licker, 
the original name of the addon.

'''

def mark(bone):
    bone['marked'] = True

class bfl_OT_makeArm(ot):
    
    bl_idname = 'bfl.makearm'
    bl_label = 'Make Arm'
    bl_description = 'Select a chain of bones to make them a Rigify arm'
    isLeft: boolprop(name='isLeft', default=False)
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(bpy.context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.scene.rigiall_props
        col = context.object.data.collections
        
        if self.isLeft:
            bone_col = col.get('Arm.L (IK)')
        else:
            bone_col = col.get('Arm.R (IK)')
        
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            mark(bone)
            if props.fix_symmetry:
                for keyword in props.keywords.split(','):
                    bone.name = bone.name.replace(keyword, '')
                    
                if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')):
                    bone.name +='.L' if self.isLeft else '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)
                
            bone_col.assign(bone)   
            
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        for n, bone in enumerate(bone_list):
            if n == 0: continue
            edits[bone].use_connect = True
            
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
                
        mode(mode='POSE')
        bones[0].rigify_type = 'limbs.arm'
        param = bones[0].rigify_parameters
        param.ik_local_location = False
        self.report({'INFO'}, 'Arm generated!')
        fk_col = param.fk_coll_refs.add()
        tweak_col = param.tweak_coll_refs.add()
        
        if self.isLeft:
            fk_col.name = 'Arm.L (FK)'
            tweak_col.name = 'Arm.L (Tweak)'
            return {'FINISHED'}
        
        fk_col.name = 'Arm.R (FK)'
        tweak_col.name = 'Arm.R (Tweak)'
        return {'FINISHED'}
    
class bfl_OT_makeLeg(ot):
    
    bl_idname = 'bfl.makeleg'
    bl_label = 'Make leg'
    bl_description = 'Select a chain of bones to make them a Rigify leg'
    isLeft: boolprop(name='Is Left', default=False)
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.scene.rigiall_props
        col = context.object.data.collections
        bones = context.selected_pose_bones
        
        if self.isLeft:
            bone_col = col.get('Leg.L (IK)')
        else:
            bone_col = col.get('Leg.R (IK)')
        
        for bone in bones:
            mark(bone)
            if props.fix_symmetry:
                for keyword in props.keywords.split(','):
                    bone.name = bone.name.replace(keyword, '')
                if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')):
                    bone.name +='.L' if self.isLeft else '.R'
            for col in bone.bone.collections:
                col.unassign(bone)  
            bone_col.assign(bone)
            
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        
        for n, bone in enumerate(bone_list):
            if n == 0: continue
            
            edits[bone].use_connect = True    
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
                
        heel = edits.new('heel.L' if self.isLeft else 'heel.R')
        heel.parent = edits[bone_list[-2]]
        heel.head[0] = edits[bone_list[-2]].head[0]
        heel.tail[0] = heel.head[0]+ (0.1 if self.isLeft else -0.1)
        heel.head[2] = 0
        heel.tail[2] = 0
        for col in heel.collections:
            col.unassign(heel)
                
        bone_col.assign(heel)
        
        mode(mode='POSE')
        heel_pose = context.object.pose.bones['heel.L' if self.isLeft else 'heel.R']
        heel_pose['marked'] = True
        
        bones[0].rigify_type = 'limbs.leg'
        
        param = bones[0].rigify_parameters
        fk_col = param.fk_coll_refs.add()
        tweak_col = param.tweak_coll_refs.add()
        
        param.ik_local_location = False
        param.extra_ik_toe = True
        self.report({'INFO'}, 'Leg generated! Adjust the heel bone in edit mode!')
        if self.isLeft:
            fk_col.name = 'Leg.L (FK)'
            tweak_col.name = 'Leg.L (Tweak)'
            return {'FINISHED'}
        
        fk_col.name = 'Leg.R (FK)'
        tweak_col.name = 'Leg.R (Tweak)'
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
        if context.object == None: return False
        return len(bpy.context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.scene.rigiall_props
        bone_col = context.object.data.collections
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            mark(bone)
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col['Torso'].assign(bone.bone)
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        for n, bone in enumerate(bone_list):
            if n == 0: continue
            edits[bone].use_connect = True
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
        
        mode(mode='POSE')
        bones[0].rigify_type = 'spines.basic_spine'
        param = bones[0].rigify_parameters
        param.pivot_pos = 1
        fk_col = param.fk_coll_refs.add()
        tweak_col = param.tweak_coll_refs.add()
        fk_col.name = 'Torso (Tweak)'
        tweak_col.name = 'Torso (Tweak)'
        self.report({'INFO'}, 'Spine generated!')
        return {'FINISHED'}
    
class bfl_OT_makeNeck(ot):
    
    bl_idname = 'bfl.makeneck'
    bl_label = 'Make Neck/Head'
    bl_description = 'Select a chain of bones to make them a Rigify Head'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(bpy.context.selected_pose_bones) > 1

    def execute(self, context):    
        obj = context.object
        props = context.scene.rigiall_props
        bone_col = context.object.data.collections
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            mark(bone)
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col['Torso'].assign(bone.bone)
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        edits[bone_list[0]].tail = edits[bone_list[1]].head
        edits[bone_list[0]].parent.tail = edits[bone_list[0]].head
        
        for n, bone in enumerate(bone_list):
            if n == 0: continue
            edits[bone].use_connect = True      
            if bone_list[-1] != bone:
                edits[bone].tail = edits[bone_list[n+1]].head
        
        mode(mode='POSE')
        bones[0].rigify_type = 'spines.super_head'
        param = bones[0].rigify_parameters
        tweak_col = param.tweak_coll_refs.add()
        tweak_col.name = 'Torso (Tweak)'
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
        if context.object == None: return False
        return len(bpy.context.selected_pose_bones) > 1

    def execute(self, context):
        obj = context.object
        props = context.scene.rigiall_props
        bone_col = context.object.data.collections
        bones = bpy.context.selected_pose_bones
        for bone in bones:
            if props.fix_symmetry:
                for keyword in props.keywords.split(','):
                    bone.name = bone.name.replace(keyword, '')
                if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')):
                    bone.name +='.L' if self.isLeft else '.R'
            for col in bone.bone.collections:
                col.unassign(bone)  
            bone_col['Fingers'].assign(bone)
            
        fingers = []
        current = []
        boneLast = None
        for bone in bones:
            mark(bone)
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
                if n == 0: continue
                edits[bone].use_connect = True
                if chain[-1] != bone:
                    edits[bone].tail = edits[chain[n+1]].head
                    
        mode(mode='POSE')
        for chain in fingers:
            bone = bpy.context.object.pose.bones.get(chain[0])
            bone.rigify_type = 'limbs.super_finger'
            param = bone.rigify_parameters
            tweak_col = param.tweak_coll_refs.add()
            tweak_col.name = 'Fingers (Detail)'
            param.make_extra_ik_control = props.ik_fingers
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
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) == 1
    
    def execute(self, context):
        obj = bpy.context.object
        props = context.scene.rigiall_props
        bone = bpy.context.active_pose_bone
        if props.fix_symmetry:
            for keyword in props.keywords.split(','):
                bone.name = bone.name.replace(keyword, '')
            if (not bone.name.endswith('.L' if self.isLeft else '.R') or not bone.name.endswith('_L' if self.isLeft else '_R')):
                bone.name +='.L' if self.isLeft else '.R'
        for col in bone.bone.collections:
            col.unassign(bone.bone)
        obj.data.collections['Torso'].assign(bone.bone)
        mark(bone)
        bone.rigify_type = 'basic.super_copy'
        param = bone.rigify_parameters
        param.make_control = True
        param.make_widget = True
        param.super_copy_widget_type = 'shoulder'
        param.make_deform = True
        self.report({'INFO'}, 'Shoulder generated!')
        return {'FINISHED'}
    
class bfl_OT_makeExtras(ot):
    bl_idname = 'bfl.extras'
    bl_label = 'Make Extras (Do This Last!)'
    bl_description = 'Preserve all unmodified bones when generating the rig. Do this last'
    bl_options = {'UNDO'}
    
    widgets: bpy.props.EnumProperty(
        items = (
            ("bone", "bone", "", "", 0),
            ("circle", "circle", "", "", 1),
            ("cube", "cube", "", "", 2),
            ("cube_truncated", "cube_truncated", "", "", 3),
            ("cuboctahedron", "cuboctahedron", "", "", 4),
            ("diamond", "diamond", "", "", 5),
            ("gear", "gear", "", "", 6),
            ("jaw", "jaw", "", "", 7),
            ("limb", "limb", "", "", 8),
            ("line", "line", "", "", 9),
            ("palm", "palm", "", "", 10),
            ("palm_z", "palm_z", "", "", 11),
            ("pivot", "pivot", "", "", 12),
            ("pivot_cross", "pivot_cross", "", "", 13),
            ("shoulder", "shoulder", "", "", 14),
            ("sphere", "sphere", "", "", 15),
            ("teeth", "teeth", "", "", 16),
        ),
        name = 'Widget', default='cube'
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        bone_col = context.object.data.collections['Extras']
        for bone in context.object.pose.bones:
            if bone.get('marked'): continue
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col.assign(bone.bone)
            bone.rigify_type = 'basic.super_copy'
            bone.rigify_parameters.super_copy_widget_type = self.widgets
        self.report({'INFO'}, 'Extra bones preserved! Select them and assign widgets in the bone tab!')
        return {'FINISHED'}

class bfl_group(bpy.types.PropertyGroup):
    ik_fingers: boolprop(name='IK Fingers', default=False)
    keywords: StringProperty(name='', description="Replaces/deletes symmetry keywords to fit Blender's symmetry naming scheme")
    fix_symmetry: boolprop(name='Fix Symmetry', description='Disable if bones already end in ".L/_L" or ".R/_R"', default=False)

def textBox(self, sentence, icon='NONE', line=56):
    layout = self
    sentence = sentence.split(' ')
    mix = sentence[0]
    sentence.pop(0)
    broken = False
    while True:
        add = ' ' + sentence[0]
        if len(mix + add) < line:
            mix += add
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix, icon='NONE' if broken else icon)
                return None

        else:
            layout.row().label(text=mix, icon='NONE' if broken else icon)
            broken = True
            mix = sentence[0]
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix)
                return None

class HISANIM_OT_genericText(bpy.types.Operator):
    bl_idname = 'generic.textbox'
    bl_label = 'Hints'
    bl_description = 'A window will display any possible questions you have'

    text: StringProperty(default='')
    icons: StringProperty()
    size: StringProperty()
    width: IntProperty(default=400)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    
    def draw(self, context):
        sentences = self.text.split('\n')
        icons = self.icons.split(',')
        sizes = self.size.split(',')
        for sentence, icon, size in zip(sentences, icons, sizes):
            textBox(self.layout, sentence, icon, int(size))

    def execute(self, context):
        return {'FINISHED'}

class bfl_OT_initialize(ot):
    bl_idname = 'bfl.init'
    bl_label = 'Initialize Rig'
    bl_description = 'Initialize the rig with bonegroups and assigned layers.'
    bl_options = {'UNDO'}
    
    def execute(self, context):
        try:
            bpy.ops.armature.rigify_add_color_sets()
        except:
            self.report({'ERROR'}, 'Enable Rigify Addon!')
            return {'CANCELLED'}
        for x in range(16):
            bpy.ops.armature.rigify_collection_add_ui_row(row=1, add=True)
            
        layers = (
            ("Torso", "Special", 1, ""),
            ("Torso (Tweak)", "Tweak", 2, "(Tweak)"),
            ("Fingers", "Extra", 4, ""),
            ("Fingers (Detail)", "FK", 5, "(Detail)"),
            ("Arm.L (IK)", "IK", 7, ""),
            ("Arm.L (FK)", "FK", 8, "(FK)"),
            ("Arm.L (Tweak)", "Tweak", 9, "(Tweak)"),
            ("Arm.R (IK)", "IK", 7, ""),
            ("Arm.R (FK)", "FK", 8, "(FK)"),
            ("Arm.R (Tweak)", "Tweak", 9, "(Tweak)"),
            ("Leg.L (IK)", "IK", 11, ""),
            ("Leg.L (FK)", "FK", 12, "(FK)"),
            ("Leg.L (Tweak)", "Tweak", 13, "(Tweak)"),
            ("Leg.R (IK)", "IK", 11, ""),
            ("Leg.R (FK)", "FK", 12, "(FK)"),
            ("Leg.R (Tweak)", "Tweak", 13, "(Tweak)"),
            ('Extras', 'Extra', 17, ''),
            ("Root", "Root", 16, ""),
        )
        for name, color, row, title in layers:
            new = bpy.context.object.data.collections.new(name=name)
            new.rigify_color_set_name = color
            new.rigify_ui_row = row
            new.rigify_ui_title = title

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
        for obj in context.selected_objects:
            if obj.type != 'MESH': continue
            for group in obj.vertex_groups:
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
        
        if context.object == None:
            return None
        
        if bpy.context.object.get('rig_ui'):
             layout.row().label(text='This is a Rigify rig!')
             return None
        
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
        op = row.operator('generic.textbox', text='', icon='QUESTION')
        op.text = 'This helps to format bone names to make them compatible for symmetry posing. For example, if you have a pair of bones named "upper_r_arm.R" and "upper_l_arm.L", symmetry will not be supported. However, if you add "_l_,_r_" in the string field, then the bones will be renamed to "upperarm.R" and "upperarm.L", making them compatible with symmetry.'
        op.size = '56'
        op.icons='NONE'
        op.width = 340
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
    bfl_OT_90roll,
    bfl_OT_0roll,
    HISANIM_OT_genericText
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
