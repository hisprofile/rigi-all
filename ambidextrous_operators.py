import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty
from bpy.utils import register_classes_factory
from .operators import mode, mark, rigiall_ot_genericText
from .main import get_bone_chains, connect_chains, iter_two

valids = ()
right = 'RIGHT'
left = 'LEFT'

side = {
    True: right,
    False: left
}

def determine_side(props, bone: bpy.types.PoseBone):
    bone = bone.bone
    pos = bone.matrix_local.to_translation()
    match props.symmetry_mode:
        case 'X_POSITIVE':
            return side[pos[0] >= 0]
        case 'X_NEGATIVE':
            return side[pos[0] <= 0]
        case 'Y_POSITIVE':
            return side[pos[1] >= 0]
        case 'Y_NEGATIVE':
            return side[pos[1] <= 0]


class rigiall_ot_makearms(Operator):
    bl_idname = 'rigiall.makearms'
    bl_label = 'Make Arms'
    bl_description = 'Select multiple bone chains to turn them into Rigify arms'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) > 1
    
    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        col = context.object.data.collections
        
        left_col = col.get('Arm.L (IK)')
        right_col = col.get('Arm.R (IK)')
        bone_chains = get_bone_chains(context)
        all_bones = [bone for chain in bone_chains for bone in chain]

        for chain in bone_chains:
            try:
                assert len(chain) == 3
            except AssertionError:
                self.report({'ERROR'}, f'Chain stemming from {chain[0].name} needs three bones!')
                return {'CANCELLED'}
        
        for bone in all_bones:
            mark(bone)
            side = determine_side(props, bone)
            if props.fix_symmetry:
                if (side is left) and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (side is right) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)

            if side is left:
                left_col.assign(bone)
            if side is right:
                right_col.assign(bone)
        
        for chain in bone_chains:
            side = determine_side(props, chain[0])
            bone_list = tuple((bone.name for bone in chain))
            mode(mode='EDIT')

            edits = obj.data.edit_bones
            for prior, next in iter_two(bone_list):
                edits[prior].tail = edits[next].head
                edits[next].use_connect = True
                    
            mode(mode='POSE')
            chain[0].rigify_type = 'limbs.arm'
            param = chain[0].rigify_parameters
            param.ik_local_location = False
            self.report({'INFO'}, 'Arm generated!')
            fk_col = param.fk_coll_refs.add()
            tweak_col = param.tweak_coll_refs.add()
            
            if side == left:
                fk_col.name = 'Arm.L (FK)'
                tweak_col.name = 'Arm.L (Tweak)'
            if side == right:
                fk_col.name = 'Arm.R (FK)'
                tweak_col.name = 'Arm.R (Tweak)'

        return {'FINISHED'}

class rigiall_ot_makelegs(rigiall_ot_genericText):
    
    bl_idname = 'rigiall.makelegs'
    bl_label = 'Make Legs'
    bl_description = 'Select a chain of bones to make them a Rigify leg'
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
        from mathutils import Vector
        obj = context.object
        props = context.window_manager.rigiall_props
        col = context.object.data.collections
        bone_chains = get_bone_chains(context)

        for chain in bone_chains:
            try:
                assert len(chain) == 4
            except AssertionError:
                self.report({'ERROR'}, f'Chain stemming from {chain[0].name} to needs four bones!')
                return {'CANCELLED'}

        left_col = col.get('Leg.L (IK)')
        right_col = col.get('Leg.R (IK)')
        all_bones = [bone for chain in bone_chains for bone in chain]

        for bone in all_bones:
            mark(bone)
            side = determine_side(props, bone)
            if props.fix_symmetry:
                if (side is left) and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (side is right) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)

            if side is left:
                left_col.assign(bone)
            if side is right:
                right_col.assign(bone)

        for chain in bone_chains:
            side = determine_side(props, chain[0])
            bone_list = tuple((bone.name for bone in chain))
            mode(mode='EDIT')

            edits = obj.data.edit_bones
            for prior, next in iter_two(bone_list):
                edits[prior].tail = edits[next].head
                edits[next].use_connect = True

            X = 0
            Y = 0
            if props.symmetry_mode == 'X_NEGATIVE':
                X = -1
            elif props.symmetry_mode == 'X_POSITIVE':
                X = 1
            if props.symmetry_mode == 'Y_NEGATIVE':
                Y = -1
            elif props.symmetry_mode == 'Y_POSITIVE':
                Y = 1
            X *= 1 if side is right else -1
            Y *= 1 if side is right else -1

            offset = Vector((X, Y, 0))
            
            foot = edits[bone_list[-2]]
            foot_length = (foot.head - foot.tail).length
            heel: bpy.types.EditBone = edits.new('heel.R' if side is right else 'heel.L')
            heel_name = heel.name
            heel.parent = foot
            heel.head = foot.head - offset*(foot_length*.5)
            heel.tail = foot.head + offset*(foot_length*.5)
            
            for col in heel.collections:
                col.unassign(heel)
            if side is left:
                left_col.assign(bone)
            if side is right:
                right_col.assign(bone)
            
            mode(mode='POSE')
            mark(obj.pose.bones[heel_name])
            
            chain[0].rigify_type = 'limbs.leg'
            param = chain[0].rigify_parameters
            param.rotation_axis = self.rotation_axis
            fk_col = param.fk_coll_refs.add()
            tweak_col = param.tweak_coll_refs.add()
            
            param.ik_local_location = False
            param.extra_ik_toe = True
            self.report({'INFO'}, 'Leg generated! Adjust the heel bone(s) in edit mode!')

            if side is left:
                fk_col.name = 'Leg.L (FK)'
                tweak_col.name = 'Leg.L (Tweak)'
            if side is right:
                fk_col.name = 'Leg.R (FK)'
                tweak_col.name = 'Leg.R (Tweak)'
        return {'FINISHED'}    

class rigiall_ot_makefingers(rigiall_ot_genericText):
    
    bl_idname = 'rigiall.makefingers_ambi'
    bl_label = 'Make Fingers'
    bl_description = 'Select a chain of bones to make Rigify fingers'
    bl_options = {'UNDO'}

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

        bone_chains = get_bone_chains(context)
        all_bones = [bone for chain in bone_chains for bone in chain]

        for bone in all_bones:
            mark(bone)
            side = determine_side(props, bone)
            if props.fix_symmetry:
                if (side is left) and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (side is right) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)

            bone_col['Fingers'].assign(bone)
            
        mode(mode='EDIT')
        edits = obj.data.edit_bones
        
        for chain in bone_chains:
            chain = tuple((bone.name for bone in chain))
            edits = obj.data.edit_bones
            for prior, next in iter_two(chain):
                edits[prior].tail = edits[next].head
                edits[next].use_connect = True
                    
        mode(mode='POSE')
        for chain in bone_chains:
            chain = tuple((bone.name for bone in chain))
            bone = context.object.pose.bones.get(chain[0])
            bone.rigify_type = 'limbs.super_finger'
            param = bone.rigify_parameters
            tweak_col = param.tweak_coll_refs.add()
            tweak_col.name = 'Fingers (Detail)'
            param.make_extra_ik_control = props.ik_fingers
            param.primary_rotation_axis = self.primary_rotation_axis
        self.report({'INFO'}, 'Fingers generated!')
        return {'FINISHED'}

class rigiall_ot_makeshoulders(Operator):
    
    bl_idname = 'rigiall.makeshoulders'
    bl_label = 'Make Shoulders'
    bl_description = 'Select bones to make them shoulders'
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.object == None: return False
        return len(context.selected_pose_bones) >= 1
    
    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props
        bone = context.active_pose_bone

        bone_chains = get_bone_chains(context)
        all_bones = [bone for chain in bone_chains for bone in chain]

        for chain in bone_chains:
            try:
                assert len(chain) == 1
            except AssertionError:
                self.report({'ERROR'}, f'Shoulders should only be one bone!')
                return {'CANCELLED'}

        for bone in all_bones:
            mark(bone)
            side = determine_side(props, bone)
            if props.fix_symmetry:
                if (side is left) and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (side is right) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
                    
            for col in bone.bone.collections:
                col.unassign(bone)

        for chain in bone_chains:
            bone = chain[0]
            obj.data.collections['Torso'].assign(bone.bone)
            bone.rigify_type = 'basic.super_copy'
            param = bone.rigify_parameters
            param.make_control = True
            param.make_widget = True
            param.super_copy_widget_type = 'shoulder'
            param.make_deform = True
            self.report({'INFO'}, 'Shoulder generated!')
        return {'FINISHED'}

class rigiall_ot_make_generic_chain(Operator):
    bl_idname = 'rigiall.make_generic_chain'
    bl_label = 'Make Generic Chain'
    bl_description = 'Quickly make a chain of bones with the active selection'

    bl_options = {'UNDO'}

    rigify_type: StringProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, title='Chain Type')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Leave blank for no change')
        layout.prop_search(self, 'rigify_type', context.window_manager, 'rigify_types', text='Rigify Type')

    def execute(self, context):
        obj = context.object
        props = context.window_manager.rigiall_props

        bone_chains = get_bone_chains(context)
        all_bones = [bone for chain in bone_chains for bone in chain]

        for bone in all_bones:
            mark(bone)
            side = determine_side(props, bone)
            if props.fix_symmetry:
                if (side is left) and (props.symmetry_left_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_left_keyword, '_') + '.L'
                    
                if (side is right) and (props.symmetry_right_keyword in bone.name):
                    bone.name = bone.name.replace(props.symmetry_right_keyword, '_') + '.R'
            
        mode(mode='EDIT')

        edits = obj.data.edit_bones

        connect_chains(bone_chains, edits)
                    
        mode(mode='POSE')
        if self.rigify_type == '': return {'FINISHED'}
        for chain in bone_chains:
            bone = chain[0]
            bone.rigify_type = self.rigify_type

        return {'FINISHED'}

classes = [
    rigiall_ot_makearms,
    rigiall_ot_makelegs,
    rigiall_ot_makefingers,
    rigiall_ot_makeshoulders,
    rigiall_ot_make_generic_chain,
]

r, ur = register_classes_factory(classes)

def register():
    r()

def unregister():
    ur()