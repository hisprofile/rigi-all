import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty, EnumProperty
from .main import get_bone_chains, iter_two, initialize_finalize_script

mode = bpy.ops.object.mode_set

class ot(Operator):
    mode: BoolProperty(default=False)

    def invoke(self, context, event: bpy.types.Event):
        if event.shift:
            self.mode = True
        else:
            self.mode = False
        return self.execute(context)

def mark(pbone):
    #if isinstance(pbone, bpy.types.PoseBone):
    pbone.rigi_all_mark = True
    if pbone.rigify_type == 'basic.super_copy':
        pbone.rigify_type = ''

def isolate(context: bpy.types.Context, object):
    [obj.select_set(False) for obj in bpy.data.objects]
    object.select_set(True)
    context.view_layer.objects.active = object

class rigiall_ot_genericText(bpy.types.Operator):
    bl_idname = 'rigiall.textbox'
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
        return_val = self.invoke_extra(context, event)
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

class rigiall_ot_makeArm(Operator):
    
    bl_idname = 'rigiall.makearm'
    bl_label = 'Make Arm'
    bl_description = 'Select a chain of bones to make them a Rigify arm'
    isLeft: BoolProperty(name='isLeft', default=False)
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        col = context.object.data.collections
        bones = context.selected_pose_bones

        try:
            assert len(bones) == 3
        except AssertionError:
            self.report({'ERROR'}, f'Chain stemming from {bones[0].name} needs three bones!')
            return {'CANCELLED'}

        if self.isLeft:
            bone_col = col.get('Arm.L (IK)')
        else:
            bone_col = col.get('Arm.R (IK)')

        for bone in bones:
            mark(bone)
            if props.fix_symmetry:
                if self.isLeft and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (not self.isLeft) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)
                
            bone_col.assign(bone)   
            
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        for prior, next in iter_two(bone_list):
            edits[prior].tail = edits[next].head
            edits[next].use_connect = True
                
        mode(mode='POSE')
        if hasattr(bones[0], 'rigify_parameters'):
            bones[0].rigify_type = 'limbs.arm'
            param = bones[0].rigify_parameters
            param.segments = 1
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
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')

        return {'FINISHED'}
    
class rigiall_ot_makeLeg(rigiall_ot_genericText):
    
    bl_idname = 'rigiall.makeleg'
    bl_label = 'Make leg'
    bl_description = 'Select a chain of bones to make them a Rigify leg'
    isLeft: BoolProperty(name='Is Left', default=False)
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
        props = context.window_manager.rigiall_props
        col = context.object.data.collections
        bones = context.selected_pose_bones

        try:
            assert len(bones) == 4
        except AssertionError:
            self.report({'ERROR'}, f'Chain stemming from {bones[0].name} needs four bones!')
            return {'CANCELLED'}
        
        if self.isLeft:
            bone_col = col.get('Leg.L (IK)')
        else:
            bone_col = col.get('Leg.R (IK)')
        
        for bone in bones:
            mark(bone)
            if props.fix_symmetry:
                if self.isLeft and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (not self.isLeft) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)
            bone_col.assign(bone)
            
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        for prior, next in iter_two(bone_list):
            edits[prior].tail = edits[next].head
            edits[next].use_connect = True
                
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
        heel_pose.rigi_all_mark = True

        if hasattr(bones[0], 'rigify_parameters'):
            bones[0].rigify_type = 'limbs.leg'
            
            param = bones[0].rigify_parameters
            param.segments = 1
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
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}
        
class rigiall_ot_makeSpine(rigiall_ot_genericText):
    
    bl_idname = 'rigiall.makespine'
    bl_label = 'Make Spine'
    bl_description = 'Select a chain of bones to make them a Rigify Spine'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        bone_col = context.object.data.collections
        bones = context.selected_pose_bones

        for bone in bones:
            mark(bone)
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col['Torso'].assign(bone.bone)

        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        for prior, next in iter_two(bone_list):
            edits[prior].tail = edits[next].head
            edits[next].use_connect = True
        
        mode(mode='POSE')
        if hasattr(bones[0], 'rigify_parameters'):
            bones[0].rigify_type = 'spines.basic_spine'
            param = bones[0].rigify_parameters
            param.pivot_pos = 1
            fk_col = param.fk_coll_refs.add()
            tweak_col = param.tweak_coll_refs.add()
            fk_col.name = 'Torso (Tweak)'
            tweak_col.name = 'Torso (Tweak)'
            self.report({'INFO'}, 'Spine generated!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}
    
class rigiall_ot_makeNeck(Operator):
    
    bl_idname = 'rigiall.makeneck'
    bl_label = 'Make Neck/Head'
    bl_description = 'Select a chain of bones to make them a Rigify Head'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1

    def execute(self, context):    
        obj = context.object
        props = context.window_manager.rigiall_props
        bone_col = context.object.data.collections
        bones = context.selected_pose_bones
        for bone in bones:
            mark(bone)
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col['Torso'].assign(bone.bone)
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        edits[bone_list[0]].parent.tail = edits[bone_list[0]].head
        for prior, next in iter_two(bone_list):
            edits[prior].tail = edits[next].head
            edits[next].use_connect = True
        
        mode(mode='POSE')
        if hasattr(bones[0], 'rigify_parameters'):
            bones[0].rigify_type = 'spines.super_head'
            param = bones[0].rigify_parameters
            tweak_col = param.tweak_coll_refs.add()
            tweak_col.name = 'Torso (Tweak)'
            self.report({'INFO'}, 'Neck and head generated!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}
    
class rigiall_ot_makeFingers(rigiall_ot_genericText):
    
    bl_idname = 'rigiall.makefingers'
    bl_label = 'Make Fingers'
    bl_description = 'Select a chain of bones to make Rigify fingers'
    bl_options = {'UNDO'}
    isLeft: BoolProperty(name='isLeft', default=False)


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
        return len(context.selected_pose_bones) > 1
    
    def draw_extra(self, context):
        row = self.layout.row()
        row.alignment = 'CENTER'
        row.prop(self, 'primary_rotation_axis')

    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        bone_col = context.object.data.collections
        bones = context.selected_pose_bones

        for bone in bones:
            mark(bone)
            if props.fix_symmetry:
                if self.isLeft and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (not self.isLeft) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)

            bone_col['Fingers'].assign(bone)
            
        fingers = get_bone_chains(context, False)
            
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        for chain in fingers:
            chain = tuple((bone.name for bone in chain))
            for prior, next in iter_two(chain):
                edits[prior].tail = edits[next].head
                edits[next].use_connect = True
                    
        mode(mode='POSE')
        if hasattr(bpy.types.PoseBone, 'rigify_parameters'):
            for chain in fingers:
                bone = context.object.pose.bones.get(chain[0])
                bone.rigify_type = 'limbs.super_finger'
                param = bone.rigify_parameters
                tweak_col = param.tweak_coll_refs.add()
                tweak_col.name = 'Fingers (Detail)'
                param.make_extra_ik_control = props.ik_fingers
                param.primary_rotation_axis = self.primary_rotation_axis
            self.report({'INFO'}, 'Fingers generated!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}
    
class rigiall_ot_90roll(Operator):
    bl_idname = 'rigiall.adjustroll'
    bl_label = 'Adjust Roll by 90°'
    bl_description = 'Adjust roll by 90° or -90°'
    bl_options = {'UNDO'}
    
    roll: FloatProperty(default=0)
    
    def execute(self, context):
        import math
        bones = [i.name for i in context.selected_pose_bones]
        mode(mode='EDIT')
        edits = context.object.data.edit_bones
        for bone in bones:
            edits[bone].roll += math.radians(self.roll)
        mode(mode='POSE')
        return {'FINISHED'}
        
class rigiall_ot_0roll(Operator):
    bl_idname = 'rigiall.noroll'
    bl_label = 'Set Roll to 0°'
    bl_description = "Sets a bone's roll to 0°"
    bl_options = {'UNDO'}

    def execute(self, context):
        bones = [i.name for i in context.selected_pose_bones]
        mode(mode='EDIT')
        edits = context.object.data.edit_bones
        for bone in bones:
            edits[bone].roll = 0
        mode(mode='POSE')
        return {'FINISHED'}        
        
class rigiall_ot_makeShoulder(Operator):
    
    bl_idname = 'rigiall.makeshoulder'
    bl_label = 'Make Shoulders'
    bl_description = 'Select bones to make them shoulders'
    bl_options = {'UNDO'}
    isLeft: BoolProperty(name='isLeft', default=False)
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) == 1
    
    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        bone = context.active_pose_bone
        if props.fix_symmetry:
            if self.isLeft and (props.symmetry_left_keyword in bone.name):
                bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                
            if (not self.isLeft) and (props.symmetry_right_keyword in bone.name):
                bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
        for col in bone.bone.collections:
            col.unassign(bone.bone)
        obj.data.collections['Torso'].assign(bone.bone)
        mark(bone)
        if hasattr(bone, 'rigify_parameters'):
            bone.rigify_type = 'basic.super_copy'
            param = bone.rigify_parameters
            param.make_control = True
            param.make_widget = True
            param.super_copy_widget_type = 'shoulder'
            param.make_deform = True
            self.report({'INFO'}, 'Shoulder generated!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}


class rigiall_ot_makeExtras(Operator):
    bl_idname = 'rigiall.extras'
    bl_label = 'Make Extras (Do this last!)'
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
    
    def draw(self, context):
        layout = self.layout
        layout.label(text='This marks all other unmodified bones as Extra Bones')
        layout.prop(self, 'widgets')
    
    def execute(self, context):
        bone_col = context.object.data.collections['Extras']
        error = False
        for bone in context.object.pose.bones:
            if getattr(bone, 'rigi_all_mark', False):
                continue
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col.assign(bone.bone)
            if hasattr(bone, 'rigify_parameters'):
                bone.rigify_type = 'basic.raw_copy'
                bone.rigify_parameters.optional_widget_type = self.widgets
            else:
                error = True

        if not error:
            self.report({'INFO'}, 'Extra bones preserved! Select them and assign widgets in the bone tab!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
            
        return {'FINISHED'}

class rigiall_ot_extras_manual(Operator):
    bl_idname = 'rigiall.extras_manual'
    bl_label = 'Make Selected Extras'
    bl_description = 'Preserve all unmodified bones when generating the rig.'
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
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'widgets')
    
    def execute(self, context):
        error = False
        bone_col = context.object.data.collections['Extras']
        for bone in context.selected_pose_bones:
            mark(bone)
            for col in bone.bone.collections:
                col.unassign(bone.bone)
            bone_col.assign(bone.bone)
            if hasattr(bone, 'rigify_parameters'):
                bone.rigify_type = 'basic.super_copy'
                bone.rigify_parameters.super_copy_widget_type = self.widgets
            else:
                error
        if not error:
            self.report({'INFO'}, 'Extra bones preserved!')
        else:
            self.report({'WARNING'}, 'Rigify is not enabled, limb generation could not be completed!')
        return {'FINISHED'}

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

class rigiall_ot_initialize(Operator):
    bl_idname = 'rigiall.init'
    bl_label = 'Initialize Rig'
    bl_description = 'Initialize the rig with bonegroups and assigned layers.'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if getattr(context.object, 'type', None) != 'ARMATURE': return False
        if getattr(context.object, 'data', {}).get('RIGI-ALL_INITIALIZED'): return False
        if context.object.get('rig_ui'): return False
        return True

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
            new = context.object.data.collections.new(name=name)
            new.rigify_color_set_name = color
            new.rigify_ui_row = row
            new.rigify_ui_title = title

        finalize_script = initialize_finalize_script(context)
        context.object.data.rigify_finalize_script = finalize_script

        mode_bak = context.object.mode
        
        mode(mode='EDIT')

        for bone in context.object.data.edit_bones:
            bone.use_connect = False
            
        mode(mode=mode_bak)
        context.object.data['RIGI-ALL_INITIALIZED'] = True

        return {'FINISHED'}
    
class rigiall_ot_tweakmesh(Operator):
    bl_idname = 'rigiall.tweakmesh'
    bl_label = 'Add "DEF-" to Vertex Groups'
    bl_description = 'Change the name of weight paints to be compatible with the rig. Recommended'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', None) == 'MESH'
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH': continue
            armature = None
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    armature = mod.object
                    if armature: break
            else:
                armature = obj.parent

            if not armature: continue

            for group in obj.vertex_groups:
                if not armature.data.bones.get('DEF-' + group.name): continue
                group.name = 'DEF-' + group.name
        return {'FINISHED'}

class rigiall_ot_remove_def_prefix(rigiall_ot_genericText):
    bl_idname = 'rigiall.remove_def_prefix'
    bl_label = 'Remove "DEF-" from Bone Names'
    bl_description = 'Change the name of deform bones to be compatible with the mesh. Not recommended'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', None) == 'ARMATURE'
    
    def execute(self, context):
        if context.object.data.collections.get('overlaying'):
            self.report({'ERROR'}, "This is not necessary! You already have the original bone names from the merged armature!")
            return {'CANCELLED'}
        
        obj_copy = context.object.copy()
        data_copy = context.object.data.copy()
        obj_copy.data = data_copy

        bones: set[bpy.types.Bone] = set(getattr(data_copy.collections.get('DEF', None), 'bones',data_copy.bones))
        bones.update(set(getattr(data_copy.collections.get('Extras'), 'bones', bones)))
        for bone in bones:
            if not bone.name.startswith('DEF-'): continue
            before = bone.path_from_id()
            stripped_name = bone.name.lstrip('DEF-')
            bone.name = stripped_name
            after = f'bones["{stripped_name}"]'
            retrieved_bone = data_copy.path_resolve(after, False)
            if retrieved_bone != bone:
                wanted = retrieved_bone.name
                old = bone.name
                retrieved_bone.name = 'temp'
                bone.name = wanted
                retrieved_bone.name = old
            for driv in data_copy.animation_data.drivers:
                driv.data_path = driv.data_path.replace(before, after)

        old_obj = context.object
        old_data = context.object.data
        wanted_obj = old_obj.name
        wanted_data = old_data.name

        context.object.user_remap(obj_copy)
        context.blend_data.objects.remove(old_obj)
        context.blend_data.armatures.remove(old_data)

        obj_copy.name = wanted_obj
        obj_copy.data.name = wanted_data

        return {'FINISHED'}

class rigiall_ot_deduplicate_boneshapes(Operator):
    bl_idname = 'rigiall.deduplicate_boneshapes'
    bl_label = 'De-duplicate Boneshapes'
    bl_description = 'De-duplicate the bone shapes on the active armature'
    bl_options = {'UNDO'}

    cleanup_type: EnumProperty(
        items=(
            ('ONLY_ARMATURE', 'Only Clean Up Armature', 'De-duplicate bone shapes only on the armature (Safer)'),
            ('BLEND_FILE', 'Clean Up ALL Shapes in Project', 'De-duplicate all bone shapes in the .blend file')
        )
    )
    
    def invoke(self, context: bpy.types.Context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text='De-duplicate Type:')
        layout.prop(self, 'cleanup_type', text='')
        if (self.cleanup_type == 'ONLY_ARMATURE') and (getattr(context.object, 'type', None) != 'ARMATURE'):
            layout.label(text='An armature object needs to be selected!', icon='ERROR')

    def execute(self, context):
        bone_shapes_master = dict()
        if self.cleanup_type == 'ONLY_ARMATURE':
            if getattr(context.object, 'type', None) != 'ARMATURE':
                self.report({'ERROR'}, 'An armature object needs to be selected!')
                return {'CANCELLED'}
            all_bone_shapes = set(bone.custom_shape for bone in context.object.pose.bones)
        elif self.cleanup_type == 'BLEND_FILE':
            user_map = bpy.data.user_map()
            all_bone_shapes = set(obj for obj in bpy.data.objects
                                if (obj.type == 'MESH' and # if the object is a mesh
                                any([getattr(user, 'type', None) == 'ARMATURE' for user in user_map[obj]]) and # if the object is used by at least one armature
                                not bool(obj.data.library or obj.data.override_library) )) # and the object data is local
            
        all_bone_shapes.discard(None)
        bdata = context.blend_data
        existing_bone_shapes = getattr(
            (bdata.collections.get('bone_shapes',) or
             bdata.collections.get('bone_widgets')),
            'objects', []
        )

        for bone_shape in [*existing_bone_shapes, *all_bone_shapes]:
            if not isinstance(getattr(bone_shape, 'data', None), bpy.types.Mesh): continue
            key = hash(tuple((round(axis, 6) for v in bone_shape.data.vertices[:10] for axis in v.co)))
            first = bone_shapes_master.setdefault(key, bone_shape)
            bone_shape.user_remap(first)
        return {'FINISHED'}

class rigiall_ot_fix_symmetry_name(Operator):
    bl_idname = 'rigiall.fix_symmetry_name'
    bl_label = 'Fix Symmetry Name'
    bl_description = 'Formats bone names to be compatible with symmetry posing'

    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.window_manager.rigiall_props
        return props.symmetry_left_keyword and props.symmetry_right_keyword


    def execute(self, context):
        props = context.window_manager.rigiall_props
        bones = context.object.pose.bones

        left_kw = props.symmetry_left_keyword
        right_kw = props.symmetry_right_keyword

        for bone in bones:
            if left_kw in bone.name:
                bone.name = bone.name.replace(left_kw, '_') + '.L'
            elif right_kw in bone.name:
                bone.name = bone.name.replace(right_kw, '_') + '.R'
        
        return {'FINISHED'}

# This is useful if we want a rigify rig, but we also want to keep the original bone orientations and their names.
# An example use case is the TF2-Trifecta. The included mercenary rigs all use Rigify, but the bones
# from the original rig are all kept so we can attach the many cosmetics with no problem, and with nothing more
# than copy location and rotation constraints.

# Another use case is to make re-targeting animations easier!
class rigiall_ot_merge(Operator):
    bl_idname = 'rigiall.merge'
    bl_label = 'Merge Armatures'
    bl_description = 'Overlay the original rig onto the meta-rig'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.window_manager.rigiall_props
        return bool(props.parasite) & bool(props.host)

    def execute(self, context):
        error = False
        props = context.window_manager.rigiall_props
        parasite: bpy.types.Object = props.parasite
        host: bpy.types.Object = props.host

        host_copy = host.copy()
        host_data_copy = host.data.copy()
        host_copy.data = host_data_copy

        parasitic_pairs = []

        [parasite.data.collections.remove(col) for col in parasite.data.collections]
        overlaying_col: bpy.types.BoneCollection = parasite.data.collections.new('overlaying')
        overlaying_col.is_visible = False

        isolate(context, host)

        parasite_bones = (bone for bone in parasite.data.bones)

        for bone in parasite_bones:
            overlaying_col.assign(bone)
            if not (h_bone := host_data_copy.bones.get(bone.name)): continue
            h_bone.name = '!' + h_bone.name
            parasitic_pairs.append((bone.name, h_bone.name))
        
        # we have to do this whole thing to get around the effect that renaming bones has on other properties.
        host.user_remap(host_copy)
        host_name = host.name
        host_data_name = host.data.name
        host.name = '!'
        host.data.name = '!'
        host_copy.name = host_name
        host_data_copy.name = host_data_name
        bpy.data.batch_remove([host, host.data])
        del host, host_name, host_data_name, host_data_copy
        host = host_copy

        parasite.hide_set(False)
        host.hide_set(False)
        parasite.select_set(True)
        parasite.matrix_world = host.matrix_world
        bpy.ops.object.join()
        mode(mode='EDIT')
        ebones: bpy.types.ArmatureEditBones = host.data.edit_bones

        for parasite_bone, host_bone in parasitic_pairs:
            parasite_bone, host_bone = ebones.get(parasite_bone), ebones.get(host_bone)
            parasite_bone.use_connect = False
            parasite_bone.parent = host_bone

        mode(mode='POSE')

        for parasite_bone, _ in parasitic_pairs:
            parasite_bone = host.pose.bones.get(parasite_bone)
            if hasattr(parasite_bone, 'rigify_type'):
                parasite_bone.rigify_type = 'basic.raw_copy'
            else:
                error = True

        mode(mode='OBJECT')

        if error:
            self.report({'WARNING'}, 'Rigify is not enabled, merge operation could not be completed!')

        return {'FINISHED'}
        
classes = [rigiall_ot_makeArm,
    rigiall_ot_makeFingers,
    rigiall_ot_makeNeck,
    rigiall_ot_makeShoulder,
    rigiall_ot_makeSpine,
    rigiall_ot_makeLeg,
    rigiall_ot_makeExtras,
    rigiall_ot_extras_manual,
    rigiall_ot_initialize,
    rigiall_ot_tweakmesh,
    rigiall_ot_remove_def_prefix,
    rigiall_ot_merge,
    rigiall_ot_90roll,
    rigiall_ot_0roll,
    rigiall_ot_genericText,
    rigiall_ot_deduplicate_boneshapes,
    rigiall_ot_fix_symmetry_name,
    ]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    r()

def unregister():
    ur()

if __name__ == '__main__':
    register()