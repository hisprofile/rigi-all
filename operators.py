import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty, EnumProperty
from .main import get_bone_chains, iter_two, initialize_finalize_script, null

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
    [obj.select_set(False) for obj in context.scene.objects]
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
        col = context.object.data.collections_all
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
        from mathutils import Vector, Matrix
        from collections import defaultdict
        import numpy as np
        Z = Vector((0, 0, 1))
        threshold = 0.8

        obj = context.object
        props = context.window_manager.rigiall_props
        col = context.object.data.collections_all
        bones: list[bpy.types.PoseBone] = context.selected_pose_bones

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

            for col in bone.bone.collections:
                col.unassign(bone)
            bone_col.assign(bone)

        all_verts = np.zeros((0, 4), dtype=np.float32)
        vertex_groups = defaultdict(lambda: np.zeros(0, dtype=np.float32))

        foot_name = (bones[2].bone.get('original_bone') or bones[2].name)
        toe_name = (bones[3].bone.get('original_bone') or bones[3].name)

        for child in obj.children_recursive:
            if not isinstance(child.data, bpy.types.Mesh): continue
            if not any([(mod.type == 'ARMATURE') and (getattr(mod, 'object', None) == obj) for mod in getattr(child, 'modifiers', [])]):
                continue
            current_groups = list()

            foot_vg = getattr(child.vertex_groups.get(foot_name), 'index', -1)
            toe_vg = getattr(child.vertex_groups.get(toe_name), 'index', -1)
            foot_vg_array = np.array([next(filter(lambda a: a.group == foot_vg, v.groups), null).weight for v in child.data.vertices], dtype=np.float32)
            toe_vg_array = np.array([next(filter(lambda a: a.group == toe_vg, v.groups), null).weight for v in child.data.vertices], dtype=np.float32)
            current_groups.extend([(bones[2].name, foot_vg_array), (bones[3].name, toe_vg_array)])

            if not any([array.max() > 0 for name, array in current_groups]):
                continue
        
            for name, array in current_groups:
                vertex_groups[name] = np.append(vertex_groups[name], array)

            verts = np.zeros(len(child.data.vertices)*3, dtype=np.float32)
            child.data.vertices.foreach_get('co', verts)
            verts = verts.reshape((-1, 3))
            verts = np.hstack((
                verts,
                np.ones((verts.shape[0], 1))
            ))

            transform = np.array(obj.matrix_world.inverted() @ child.matrix_world)
            verts = (transform @ verts.T).T

            all_verts = np.append(all_verts, verts)

        all_verts = all_verts.reshape((-1, 4))
            
        bone_list = tuple((bone.name for bone in bones))
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        for prior, later in iter_two(bone_list):
            edits[prior].tail = edits[later].head
            edits[later].use_connect = True
                
        foot = edits[bone_list[2]]

        side = 'R' if not self.isLeft else 'L'
        heel_name = 'heel.' + side
        if edits.get(heel_name):
            tally = 0
            while edits.get(heel_name):
                tally += 1
                heel_name = 'heel.' + f'{tally:03d}.' + side

        heel = edits.new(heel_name)
        heel.parent = foot

        foot_dir: Vector = (foot.tail - foot.head).xy.normalized().to_3d()
        foot_x = foot_dir.cross(Z)
        foot_y = Z.cross(foot_x)
        rotation = Matrix([
            foot_x,
            foot_y,
            Z
        ]).transposed().to_4x4()
        transform = Matrix.Translation(foot.matrix.to_translation()) @ rotation

        if all_verts.size > 0:
            foot_name, toe_name = bone_list[2], bone_list[3]

            transform_inverted = np.array(transform.inverted())

            joined_mask = (vertex_groups[foot_name] + vertex_groups[toe_name])
            valid_mask = (joined_mask > threshold)
            joined_mask = joined_mask[valid_mask].reshape((-1, 1))
            toe_mask = vertex_groups[toe_name][valid_mask]
            valid_points = all_verts[valid_mask]
            transformed_points = (transform_inverted @ valid_points.T).T

            final_points = transformed_points*joined_mask + valid_points * (1-joined_mask)
            final_points = final_points[:, :3]
            final_points_toe_Z_max = final_points[toe_mask > threshold][:, 2].max()

            x_min = final_points[:, 0].min()
            x_max = final_points[:, 0].max()
            y_min = final_points[final_points[:, 2] <= final_points_toe_Z_max][:, 1].min()
            bone_min = (transform @ Vector((x_min if not self.isLeft else x_max, y_min, 0))).xy.to_3d()
            bone_max = (transform @ Vector((x_max if not self.isLeft else x_min, y_min, 0))).xy.to_3d()
            
            heel.head = bone_min
            heel.tail = bone_max
        else:
            foot_length = (foot.head - foot.tail).length
            X = -1 if not self.isLeft else 1
            Y = 0

            offset = Vector((X, Y, 0))
            
            heel.head = (rotation @ offset*(foot_length*.5) + foot.head).xy.to_3d()
            heel.tail = (rotation @ -offset*(foot_length*.5) + foot.head).xy.to_3d()

        for col in heel.collections:
            col.unassign(heel)
                
        bone_col.assign(heel)
        
        mode(mode='POSE')
        mark(obj.pose.bones[heel_name])

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
        bone_col = context.object.data.collections_all
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
        bone_col = context.object.data.collections_all
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
    ik_fingers: BoolProperty(name='IK Fingers', description='Use IK targets at the end of fingers', default=False)
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1
    
    def draw_extra(self, context):
        row = self.layout.row()
        row.alignment = 'CENTER'
        row.prop(self, 'primary_rotation_axis')
        row = self.layout.row()
        row.alignment = 'CENTER'
        row.prop(self, 'ik_fingers')

    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        bone_col = context.object.data.collections_all
        bones = context.selected_pose_bones

        for bone in bones:
            mark(bone)

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
    
    roll: FloatProperty(default=0.0)
    axis: EnumProperty(
        items=(
            ('X', 'X', 'X'),
            ('Y', 'Y', 'Y'),
            ('Z', 'Z', 'Z'),
        ),
        name='Axis',
        description='Which axis to roll on'
    )
    
    def execute(self, context):
        from mathutils import Matrix
        bones = [i.name for i in context.selected_pose_bones]
        mode(mode='EDIT')
        edits = context.object.data.edit_bones
        for bone in bones:
            bone = edits[bone]
            bone.matrix = bone.matrix @ Matrix.Rotation(self.roll, 4, self.axis)
            #edits[bone].roll += math.radians(self.roll)
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

        for col in bone.bone.collections:
            col.unassign(bone.bone)
        obj.data.collections_all['Torso'].assign(bone.bone)
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
        bone_col = context.object.data.collections_all['Extras']
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
        bone_col = context.object.data.collections_all['Extras']
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

    preserve_original_bones: BoolProperty(name='Preserve Original Bones',
                                          description='Make a copy of the original bones, in case they are needed by other armatures. They will remain untouched as you make the meta-rig',
                                          default=False
                                          )

    @classmethod
    def poll(cls, context):
        if getattr(context.object, 'type', None) != 'ARMATURE': return False
        if getattr(context.object, 'data', {}).get('RIGI-ALL_INITIALIZED'): return False
        if context.object.get('rig_ui'): return False
        return True
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)

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

        if self.preserve_original_bones:
            obj = context.object
            #obj_copy = obj.copy()
            obj_data_name = obj.data.name
            obj_data_copy: bpy.types.Armature = obj.data.copy()
            obj.data.name = '!'
            obj_data_copy.name = obj_data_name
            #obj.data = obj_data_copy

            for bone in obj_data_copy.bones:
                original_bone = bone.name
                bone['original_bone'] = original_bone
                bone.name = '!' + original_bone

            obj.data = obj_data_copy

            mode(mode='EDIT')

            ebones = obj.data.edit_bones
            new_bones = list()
            for bone in list(obj.data.edit_bones):
                copy = ebones.new(bone['original_bone'])
                new_bones.append(copy.name)
                copy.head = bone.head
                copy.tail = bone.tail
                copy.roll = bone.roll
                copy.parent = bone

            mode(mode='OBJECT')

            overlaying = obj_data_copy.collections.new('overlaying')
            overlaying.is_visible = False
            [overlaying.assign(obj_data_copy.bones[bone]) for bone in new_bones]
            [[setattr(obj.pose.bones[bone], 'rigi_all_mark', True),
              setattr(obj.pose.bones[bone], 'rigify_type', 'basic.raw_copy')] for bone in new_bones]

        self.report({'INFO'}, 'Original bones have been preserved! Please proceed with limb generation.')

        finalize_script = initialize_finalize_script(context)
        context.object.data.rigify_finalize_script = finalize_script

        mode_bak = context.object.mode
        
        mode(mode='EDIT')

        for bone in context.object.data.edit_bones:
            bone.use_connect = False
            
        mode(mode=mode_bak)
        context.object.data['RIGI-ALL_INITIALIZED'] = True

        return {'FINISHED'}
    


class rigiall_ot_fix_symmetry_name(Operator):
    bl_idname = 'rigiall.fix_symmetry_name'
    bl_label = 'Fix Symmetry Name'
    bl_description = 'Formats bone names to be compatible with symmetry posing'

    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.window_manager.rigiall_props
        return props.symmetry_left_keyword and props.symmetry_right_keyword and (getattr(context.object, 'type', '') == 'ARMATURE')


    def execute(self, context):
        props = context.window_manager.rigiall_props
        data: bpy.types.Armature = context.object.data
        bones = set(data.bones)
        bones.difference_update(set(getattr(data.collections_all.get('overlaying'), 'bones', set())))

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

class RIGIALL_OT_preserve_bones(Operator):
    bl_idname = 'rigiall.preserve_bones'
    bl_label = 'Preserve Original Bones'
    bl_description = 'Keep the original bones under the meta-rig, in case they are needed by other armatures. This should be done first!'

    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (getattr(context.object, 'type', '') == 'ARMATURE') and (context.object.data.collections_all.get('overlaying') == None) and (context.object.data.get('rig_id') == None)

    def execute(self, context):
        obj = context.object
        if obj.data.collections_all.get('overlaying'):
            self.report({'ERROR'}, 'Armature bones have already been preserved!')
        #obj_copy = obj.copy()
        obj_data_name = obj.data.name
        obj_data_copy: bpy.types.Armature = obj.data.copy()
        obj.data.name = '!'
        obj_data_copy.name = obj_data_name
        #obj.data = obj_data_copy

        for bone in obj_data_copy.bones:
            original_bone = bone.name
            bone['original_bone'] = original_bone
            bone.name = '!' + original_bone

        obj.data = obj_data_copy

        mode(mode='EDIT')

        ebones = obj.data.edit_bones
        new_bones = list()
        for bone in list(obj.data.edit_bones):
            copy = ebones.new(bone['original_bone'])
            new_bones.append(copy.name)
            copy.head = bone.head
            copy.tail = bone.tail
            copy.roll = bone.roll
            copy.parent = bone

        mode(mode='OBJECT')

        overlaying = obj_data_copy.collections.new('overlaying')
        overlaying.is_visible = False
        [overlaying.assign(obj_data_copy.bones[bone]) for bone in new_bones]

        self.report({'INFO'}, 'Original bones have been preserved! Please proceed with limb generation.')
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
    rigiall_ot_90roll,
    rigiall_ot_0roll,
    rigiall_ot_genericText,
    rigiall_ot_fix_symmetry_name,
    RIGIALL_OT_preserve_bones,
    ]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    r()

def unregister():
    ur()

if __name__ == '__main__':
    register()