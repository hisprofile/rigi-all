bl_info = {
    "name": "Rigi-All",
    "description": "Helps convert a humanoid rig to a Rigify rig",
    "author": "hisanimations",
    "version": (1, 4),
    "blender": (4, 0, 0),
    "location": "View3D > Rigi-All",
    "warning": "", # used for warning icon and text in addons panel
    "doc_url": "https://github.com/hisprofile/rigi-all/tree/main",
    "support": "COMMUNITY",
    "category": "Rigging",
}

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty as boolprop
from bpy.props import *
from math import degrees    

mode = bpy.ops.object.mode_set

#def edit_mode():
#

class ot(Operator):
    mode: BoolProperty(default=False)

    def invoke(self, context, event: bpy.types.Event):
        if event.shift:
            self.mode = True
        else:
            self.mode = False
        return self.execute(context)

'''

To anyone who cares, bfl means Ball Flicker Licker, 
the original name of the addon.

'''

def mark(pbone):
    pbone['marked'] = True
    if isinstance(pbone, bpy.types.PoseBone):
        pbone.bone['marked'] = True

def isolate(context: bpy.types.Context, object):
    [obj.select_set(False) for obj in bpy.data.objects]
    object.select_set(True)
    context.view_layer.objects.active = object

class bfl_OT_genericText(bpy.types.Operator):
    bl_idname = 'bfl.textbox'
    bl_label = 'Hints'
    bl_description = 'A window will display any possible questions you have'

    text: StringProperty(default='')
    icons: StringProperty()
    size: StringProperty()
    width: IntProperty(default=400)
    url: StringProperty(default='')
    mode: BoolProperty()

    def invoke(self, context, event):
        if not getattr(self, 'prompt', True):
            return self.execute(context)
        self.mode = False
        if event.shift and self.url != '':
            self.mode = True
            bpy.ops.wm.url_open(url=self.url)
            return {'FINISHED'}
        self.invoke_extra(context, event)
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    
    def invoke_extra(self, context, event):
        pass
    
    def draw(self, context):
        sentences = self.text.split('\n')
        icons = self.icons.split(',')
        sizes = self.size.split(',')
        if self.text != '':
            for sentence, icon, size in zip(sentences, icons, sizes):
                textBox(self.layout, sentence, icon, int(size))
        self.draw_extra(context)

    def draw_extra(self, context):
        pass

    def execute(self, context):
        return {'FINISHED'}

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
        if self.mode:
            bpy.ops.armature.calculate_roll()
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
    
class bfl_OT_makeLeg(bfl_OT_genericText):
    
    bl_idname = 'bfl.makeleg'
    bl_label = 'Make leg'
    bl_description = 'Select a chain of bones to make them a Rigify leg'
    isLeft: boolprop(name='Is Left', default=False)
    bl_options = {'UNDO'}

    rotation_axis: EnumProperty(
        items = [
            ('x', 'X manual', ''),
            ('z', 'Z manual', ''),
            ('automatic', 'Automatic', '')
            ],
        name="Primary Rotation Axis", default='x'
        )
    
    def draw_extra(self, context):
        row = self.layout.row()
        row.alignment = 'CENTER'
        row.prop(self, 'rotation_axis')

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
        if self.mode:
            bpy.ops.armature.calculate_roll()
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
        param.rotation_axis = self.rotation_axis
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
        
class bfl_OT_makeSpine(bfl_OT_genericText):
    
    bl_idname = 'bfl.makespine'
    bl_label = 'Make Spine'
    bl_description = 'Select a chain of bones to make them a Rigify Spine'
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
        if self.mode:
            bpy.ops.armature.calculate_roll()
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
        if self.mode:
            bpy.ops.armature.calculate_roll()
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
    
class bfl_OT_makeFingers(bfl_OT_genericText):
    
    bl_idname = 'bfl.makefingers'
    bl_label = 'Make Fingers'
    bl_description = 'Select a chain of bones to make Rigify fingers'
    bl_options = {'UNDO'}
    isLeft: boolprop(name='isLeft', default=False)


    primary_rotation_axis: EnumProperty(
        items = [
            ('automatic', 'Automatic', ''),
            ('X', '+X manual', ''), ('Y', '+Y manual', ''), ('Z', '+Z manual', ''),
            ('-X', '-X manual', ''), ('-Y', '-Y manual', ''), ('-Z', '-Z manual', '')
            ],
        name="Primary Rotation Axis", default='X'
        )
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(bpy.context.selected_pose_bones) > 1
    
    def draw_extra(self, context):
        row = self.layout.row()
        row.alignment = 'CENTER'
        row.prop(self, 'primary_rotation_axis')

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
        if self.mode:
            bpy.ops.armature.calculate_roll()
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
            param.primary_rotation_axis = self.primary_rotation_axis
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
            bone['extra'] = True
            bone.bone['extra'] = True
            bone.rigify_parameters.super_copy_widget_type = self.widgets
        self.report({'INFO'}, 'Extra bones preserved! Select them and assign widgets in the bone tab!')
        return {'FINISHED'}


def isArmature(self, a):
    return a.type == 'ARMATURE'

def textBox(self, sentence, icon='NONE', line=56):
    layout = self.box().column()
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

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', None) == 'MESH'
    
    def execute(self, context):
        if context.object.parent != None:
            if context.object.parent.type == 'ARMATURE':
                par = context.object.parent
                if par.data.collections.get('underlying'):
                    self.report({'ERROR'}, "You do not have to Fix Mesh if the rig you are attaching to has been merged!")
                    return {'CANCELLED'}
        for obj in context.selected_objects:
            if obj.type != 'MESH': continue
            for group in obj.vertex_groups:
                if group.name.startswith('DEF-'): continue
                group.name = 'DEF-'+group.name
        return {'FINISHED'}
    
class bfl_OT_tweakArmature(ot):
    bl_idname = 'bfl.tweakarmature'
    bl_label = 'Fix Merged Armature'
    bl_description = 'Change the name of bones to be compatible with the mesh. Use only on merged armatures'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', None) == 'ARMATURE'
    
    def execute(self, context):
        if context.object.get('rig_ui') == None:
            self.report({'ERROR'}, 'Use on a rigify rig!')
            return {'CANCELLED'}
        if context.object.data.collections.get('underlying') == None:
            self.report({'ERROR'}, 'Use on a merged Rigify rig!')
        for bone in context.object.pose.bones:
            if not bone.get('needs_fix', False): continue
            bone.bone.use_deform = True

        bone_list = map(lambda a: a.name, context.object.data.collections['underlying'].bones)
        mode(mode='EDIT')
        ebones = context.object.data.edit_bones
        for bone in bone_list:
            ebone = ebones[bone]
            par_ebone_name = getattr(ebone.parent, 'name', '')
            if par_ebone_name.startswith('ORG-'):
                new_bone_name = par_ebone_name.replace('ORG-', 'DEF-')
                if (new_par := ebones.get(new_bone_name)):
                    ebone.parent = new_par
        mode(mode='OBJECT')
        return {'FINISHED'}
    
class bfl_OT_merge(ot):
    bl_idname = 'bfl.merge'
    bl_label = 'Merge Armatures'
    bl_description = 'Have the original rig underlay the meta-rig'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.rigiall_props
        return bool(props.parasite) & bool(props.host)

    def execute(self, context):
        props = context.scene.rigiall_props
        parasite: bpy.types.Object = props.parasite
        host: bpy.types.Object = props.host

        isolate(context, parasite)
        mode(mode='EDIT')

        for bone in parasite.data.edit_bones:
            bone: bpy.types.EditBone
            if (hbone := host.data.bones.get(bone.name)) == None: continue
            if hbone.get('extra'):
                parasite.data.edit_bones.remove(bone)

        mode(mode='OBJECT')

        for bone in host.data.bones:
            if not bone.get('marked', False): continue
            bone.name = '!' + bone.name

        current_bones = set(map(lambda a: a.name, host.data.bones))

        parasite.matrix_world = host.matrix_world
        isolate(context, host)
        parasite.select_set(True)
        bpy.ops.object.join()

        new_bones = set(map(lambda a: a.name, host.data.bones)) - current_bones
        marked = set(map(lambda a: a.name, filter(lambda a: a.get('marked'), host.data.bones)))
        extras = set(map(lambda a: a.name, filter(lambda a: a.get('extra'), host.data.bones)))

        new_col = host.data.collections.new('underlying')

        mode(mode='EDIT')
        ebones = host.data.edit_bones
        for bone in new_bones:
            ebone = ebones.get(bone)
            if not ebone: continue
            p_ebone = ebones.get('!'+bone)
            if not p_ebone:
                ebones.remove(ebone)
                continue
            ebone.parent = p_ebone
            new_col.assign(host.data.bones[bone])

        for bone in extras:
            ebone = ebones.get(bone)
            if not ebone: continue
            if not getattr(ebone.parent, 'name', '').startswith('!'): continue
            if not (p_ebone := ebones.get(ebone.parent.name[1:])): continue
            ebone.parent = p_ebone
        mode(mode='POSE')

        for bone in new_bones:
            pbone = host.pose.bones.get(bone)
            if not pbone: continue
            pbone.rigify_type = 'basic.raw_copy'
            new_col.assign(pbone.bone)
            pbone['needs_fix'] = True
            pbone.bone['needs_fix'] = True

        for bone in extras:
            pbone = host.pose.bones.get(bone)
            if not pbone: continue
            pbone.rigify_type = 'basic.raw_copy'
            pbone.rigify_parameters.optional_widget_type = pbone.rigify_parameters.super_copy_widget_type
            pbone['needs_fix'] = True
            pbone.bone['needs_fix'] = True

        mode(mode='OBJECT')

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
        
        #if getattr(context.object, 'type', None) != 'ARMATURE':
        #    layout.row().label(text='Select an armature!')
        #    return None
        
        layout.row().operator('bfl.tweakmesh')
        layout.row().operator('bfl.tweakarmature')
        layout.row().operator('bfl.init')

        layout.separator()

        if getattr(context.object, 'mode', 'OBJECT') == 'OBJECT':
            row = layout.row()
            row.label(text='Merge Armature')
            op = row.operator('bfl.textbox', icon='QUESTION', text="What's this?")
#            op.text = '''This tool merges the meta-rig with the original rig, preserving the original rig. If you are familiar with my TF2 ports and how cosmetics can be attached to mercenaries, this makes that possible.
#Do not use "Fix Mesh!" It is not required with a merged rig. Instead, use Fix Armature to allow the mesh to follow the armature.'''
            op.text = '''This tool overlays the original rig onto the meta-rig, preserving the original rig's bone orientations without compromising on a Rigify Rig.
Do not use "Fix Mesh"! Instead, use "Fix Armature" on the generated Rigify rig to ensure the mesh follows the armature.'''
            op.icons = 'QUESTION,ERROR'
            op.size = '56,56'
            op.width=330

            box = layout.box()

            box.prop(props, 'parasite', text='Original Rig')
            box.prop(props, 'host', text='Target Rig')
            if props.host and not bool(getattr(props.host, 'data', {}).get('INITIALIZED')):
                row = box.row()
                row.alert = True
                row.label(text='Target is not a meta-rig!')
            box.operator('bfl.merge')

        if context.object == None:
            return None

        if context.object.get('rig_ui'):
            layout.row().label(text='This is a Rigify rig!')
            return None
        
        if context.object.mode != 'POSE':
            layout.row().label(text='Enter pose mode!')
            return None
        
        if not context.object.data.get('INITIALIZED'):
            layout.row().label(text='Initialize the rig!')
            return None

        layout.row().label(text='Symmetry Keywords, separate with ","')
        row = layout.row()
        row.prop(props, 'keywords')
        op = row.operator('bfl.textbox', text='', icon='QUESTION')
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
            layout.label(text='Select enough bones to form a chain!')
        
        layout.row().label(text='Arms')
        box = layout.box()
        op = box.row().operator('bfl.makearm', text='Make Left Arm')
        op.isLeft = True
        op = box.row().operator('bfl.makearm', text='Make Right Arm')
        op.isLeft = False
        
        op = box.row().operator('bfl.makefingers', text='Make Left Fingers')
        op.isLeft = True
        op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
        op.size = '56'
        op.icons = 'BLANK1'
        op = box.row().operator('bfl.makefingers', text='Make Right Fingers')
        op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
        op.size = '56'
        op.icons = 'BLANK1'
        op.isLeft = False
        box.row().prop(context.scene.rigiall_props, 'ik_fingers')
        
        layout.row().label(text='Legs')
        box = layout.box()
        op = box.row().operator('bfl.makeleg', text='Make Left Leg')
        op.text = 'The bones should rotate around this axis. X Manual by default.'
        op.size = '56'
        op.icons = 'BLANK1'
        op.isLeft = True
        op = box.row().operator('bfl.makeleg', text='Make Right Leg')
        op.text = 'The bones should rotate around this axis. X Manual by default.'
        op.size = '56'
        op.icons = 'BLANK1'
        op.isLeft = False
        
        layout.row().label(text='Torso')
        box = layout.box()
        op = box.row().operator('bfl.makespine', text='Make Spine')
        op.text = 'Make sure that the pelvis is the beginning of the spine chain, AND that the pelvis is the absolue root of the rig.'
        op.size = '64'
        op.icons = 'BLANK1'
        op.width = 360
        box.row().operator('bfl.makeneck', text='Make Neck/Head')
        
        op = box.row().operator('bfl.makeshoulder', text='Make Left Shoulder')
        op.isLeft = True
        op = box.row().operator('bfl.makeshoulder', text='Make Right Shoulder')
        op.isLeft = False
        
        layout.row().label(text='Misc.')
        box = layout.box()
        box.row().operator('bfl.extras')
        op = box.row().operator('bfl.adjustroll', text='Roll by 90°')
        op.roll = 90

        op = box.row().operator('bfl.adjustroll', text='Roll by -90°')
        op.roll = -90
        
        box.row().operator('bfl.noroll')

        #row.label(text='', icon='CHECKMARK' if bpy.context.object.data.get('bfl_LEFT') else 'CANCEL')
        
class bfl_group(bpy.types.PropertyGroup):
    ik_fingers: boolprop(name='IK Fingers', default=False)
    keywords: StringProperty(name='', description="Replaces/deletes symmetry keywords to fit Blender's symmetry naming scheme")
    symmetry_left_keyword: StringProperty(name='Symmetry Left Keyword', description='Fixes left symmetry keywords to ensure they are compatible with Blender\'s naming scheme')
    symmetry_right_keyword: StringProperty(name='Symmetry Right Keyword', description='Fixes right symmetry keywords to ensure they are compatible with Blender\'s naming scheme')
    fix_symmetry: boolprop(name='Fix Symmetry Name', description='Disable if bones already end in ".L/_L" or ".R/_R"', default=False)

    parasite: PointerProperty(type=bpy.types.Object, poll=isArmature)
    host: PointerProperty(type=bpy.types.Object, poll=isArmature)

    symmetry_mode: EnumProperty(items=[
        ('X_POSITIVE', '+X', 'The right side of the armature is on the positive side of the X axis.'),
        ('X_NEGATIVE', '-X', 'The right side of the armature is on the negative side of the X axis.'),
        ('Y_POSITIVE', '+Y', 'The right side of the armature is on the positive side of the Y axis.'),
        ('Y_NEGATIVE', '-Y', 'The right side of the armature is on the negative side of the Y axis.'),
        ],
        name='Symmetry Mode',
        description='Set the symmetry mode for automatic limb assignments',
        default='X_POSITIVE')
        
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
    bfl_OT_tweakArmature,
    bfl_OT_merge,
    bfl_group,
    bfl_OT_90roll,
    bfl_OT_0roll,
    bfl_OT_genericText,
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
