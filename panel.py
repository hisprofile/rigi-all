import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty
from math import degrees

class rigiall_OT_change_category(Operator):
    bl_idname = 'rigiall.change_category'
    bl_label = 'Change Category'
    bl_description = 'Change the panel category in the viewport'

    category: StringProperty(name='Category')

    def invoke(self, context, event):
        self.category = context.preferences.addons[__package__].preferences.category
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text='Change Category:')
        layout.prop(self, 'category', text='')

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.category = self.category
        return {'FINISHED'}

class RIGIALL_PT_panel(Panel):
    """A Custom Panel in the Viewport Toolbar"""
    bl_label = 'Rigi-All'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Rigi-All'

    def draw_header(self, context):
        self.layout.operator('rigiall.change_category', text='', icon='OPTIONS')
    
    def draw(self, context):
        props = context.window_manager.rigiall_props
        layout = self.layout
        #layout.panel('BONE_PT_rigify_buttons', default_closed=False)
        #bpy.types.BONE_PT_rigify_buttons.draw(self, context)
        #if getattr(context.object, 'type', None) != 'ARMATURE':
        #    layout.row().label(text='Select an armature!')
        #    return None
        layout.row().label(text='View Mode:')
        layout.row().prop(props, 'view', expand=True)
        layout.separator()

        if props.view == 'RIGGING':
            if getattr(context.object, 'type', None) != 'ARMATURE':
                pass
            elif getattr(context.object, 'data', {}).get('RIGI-ALL_INITIALIZED'):
                pass
            elif context.object.get('rig_ui'):
                pass
            else:
                layout.row().operator('rigiall.init')
            if getattr(context.object, 'mode', 'OBJECT') == 'OBJECT':
                row = layout.row()
                row.label(text='Merge Armature')
                op = row.operator('rigiall.textbox', icon='QUESTION', text="What's this?")
    #            op.text = '''This tool merges the meta-rig with the original rig, preserving the original rig. If you are familiar with my TF2 ports and how cosmetics can be attached to mercenaries, this makes that possible.
    #Do not use "Fix Mesh!" It is not required with a merged rig. Instead, use Fix Armature to allow the mesh to follow the armature.'''
                op.text = '''This tool overlays the original rig onto the meta-rig, preserving the original rig's bone orientations without compromising on a Rigify Rig.'''
                op.icons = 'QUESTION'
                op.size = '56'
                op.width=330

                box = layout.box()

                box.prop(props, 'parasite', text='Original Rig')
                box.prop(props, 'host', text='Target Rig')
                if props.host and not bool(getattr(props.host, 'data', {}).get('RIGI-ALL_INITIALIZED')):
                    row = box.row()
                    row.alert = True
                    row.label(text='Target is not a meta-rig!')
                box.operator('rigiall.merge')

            if context.object == None:
                return None

            if context.object.get('rig_ui'):
                layout.row().label(text='This is a Rigify rig!')
                return None
            
            if context.object.mode != 'POSE':
                layout.row().label(text='Enter pose mode!')
                return None
            
            if not context.object.data.get('RIGI-ALL_INITIALIZED'):
                layout.row().label(text='Initialize the rig!')
                return None
            # force rigify to build rig types
            if not context.window_manager.rigify_types:
                bpy.types.BONE_PT_rigify_buttons.draw(self, context)
            
            row = layout.row()
            row.prop(props, 'automatic_symmetry')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = 'Set the property to what side of which axis the right side of the rig is. For best results, make sure the right side of the rig is on -X, and the symmetry mode is -X'
            op.size = '58'
            op.icons = 'BLANK1'
            op.width=350
            if props.automatic_symmetry:
                row = layout.box().row()
                r = row.row()
                r.label(text='Symmetry Mode:')
                r = row.row()
                #row.alignment = 'EXPAND'
                r.prop(props, 'symmetry_mode', text='')
            row = layout.row()
            row.prop(props, 'fix_symmetry')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = 'This helps to format bone names to make them compatible for symmetry posing. For example, a pair of bones named "upper_r_arm" and "upper_l_arm" will not support symmetry. However, if you set the left and right symmetry keywords to "_l_" and "_r_" respectively, they will be formatted to "upper_arm.R" "upper_arm.L"'
            op.size = '56'
            op.icons='BLANK1'
            op.width = 350
            #row.prop(props, 'keywords')
            if props.fix_symmetry:
                box = layout.box()
                col = box.column()
                row = col.row()
                row.label(text='Left Symmetry Keyword')
                row.prop(props, 'symmetry_left_keyword', text='')

                col = box.column()
                row = col.row()
                row.label(text='Right Symmetry Keyword')
                row.prop(props, 'symmetry_right_keyword', text='')

                col = box.column()

                if len(props.symmetry_left_keyword) == 1 or len(props.symmetry_right_keyword) == 1:
                    count = len(props.symmetry_left_keyword) + len(props.symmetry_right_keyword)
                    op = col.row().operator('rigiall.textbox', text='Is this correct?' if count < 2 else 'Are you sure this is correct?', icon='QUESTION')
                    op.text = 'You seem to be using a single character as a keyword. Try making your search more strict. For example, use "_L_" instead of "L". Otherwise, you risk replacing too many characters!'
                    op.size = '58'
                    op.icons = 'ERROR'
                    op.width=350
                
                col.row().operator('rigiall.fix_symmetry_name')


            bone = context.active_pose_bone
            if bone != None:
                axis, roll = bone.bone.AxisRollFromMatrix(bone.bone.matrix_local.to_3x3())
                layout.row().label(text=f'Current Bone Roll: {round(degrees(roll), 3)}')

            if len(context.selected_pose_bones) == 1:
                layout.label(text='Select enough bones to form a chain!')

            col_arms = layout.column()
            col_arms.row().label(text='Arms')
            box_arms = col_arms.box()

            col_legs = layout.column()
            col_legs.row().label(text='Legs')
            box_legs = col_legs.box()

            col_torso = layout.column()
            col_torso.row().label(text='Torso')
            box_torso = col_torso.box()

            op = box_torso.row().operator('rigiall.makespine', text='Make Spine')
            op.text = 'Make sure that the pelvis is the beginning of the spine chain, AND that the pelvis is the absolue root of the rig.'
            op.size = '64'
            op.icons = 'BLANK1'
            op.width = 360
            box_torso.row().operator('rigiall.makeneck', text='Make Neck/Head')

            col_misc = layout.column()
            col_misc.row().label(text='Misc.')
            box_misc = col_misc.box()

            if props.automatic_symmetry:
                #layout.row().label(text='Arms')
                #box = layout.box()
                box_arms.row().operator('rigiall.makearms')
                op = box_legs.row().operator('rigiall.makelegs')
                op.text = 'The bones should rotate around this axis. X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'

                op = box_arms.row().operator('rigiall.makefingers_ambi', text='Make Fingers')
                op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'

                box_torso.row().operator('rigiall.makeshoulders', text='Make Shoulders')
            else:
                #layout.row().label(text='Arms')
                #box = layout.box()
                op = box_arms.row().operator('rigiall.makearm', text='Make Left Arm')
                op.isLeft = True
                op = box_arms.row().operator('rigiall.makearm', text='Make Right Arm')
                op.isLeft = False

                op = box_legs.row().operator('rigiall.makeleg', text='Make Left Leg')
                op.text = 'The bones should rotate around this axis. X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'
                op.isLeft = True
                op = box_legs.row().operator('rigiall.makeleg', text='Make Right Leg')
                op.text = 'The bones should rotate around this axis. X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'
                op.isLeft = False
            
                op = box_arms.row().operator('rigiall.makefingers', text='Make Left Fingers')
                op.isLeft = True
                op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'
                op = box_arms.row().operator('rigiall.makefingers', text='Make Right Fingers')
                op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'
                op.isLeft = False

                op = box_torso.row().operator('rigiall.makeshoulder', text='Make Left Shoulder')
                op.isLeft = True
                op = box_torso.row().operator('rigiall.makeshoulder', text='Make Right Shoulder')
                op.isLeft = False

            box_arms.row().prop(context.window_manager.rigiall_props, 'ik_fingers')
            row = box_misc.row(align=True)
            row.alignment = 'EXPAND'
            r = row.row()
            r.operator('rigiall.extras')
            r = row.row()
            r.alignment = 'RIGHT'
            r.operator('rigiall.extras_manual', text='Only Selected')
            op = box_misc.row().operator('rigiall.adjustroll', text='Roll by 90°')
            op.roll = 90

            op = box_misc.row().operator('rigiall.adjustroll', text='Roll by -90°')
            op.roll = -90
            
            box_misc.row().operator('rigiall.noroll')
            row = box_misc.row()
            row.operator('rigiall.make_generic_chain')
        elif props.view == 'CLEAN_UP':
            layout.label(text='Make Mesh Compatible')
            box = layout.box()
            box.row().operator('rigiall.tweakmesh')
            op = box.row().operator('rigiall.remove_def_prefix')
            op.text = 'This is destructive to the rig, and is recommended if you add the "DEF-" prefix to vertex groups instead.\nContinue anyways?'
            op.icons = 'ERROR,QUESTION'
            op.size = '56,56'
            op.width=360
            #layout.label(text='Finalize Merged Armature')
            #box = layout.box()
            #box.row().operator('rigiall.tweakarmature')
            layout.label(text='Bone Shapes')
            box = layout.box()
            box.row().operator('rigiall.deduplicate_boneshapes')
            

classes = [
    RIGIALL_PT_panel,
    rigiall_OT_change_category
]

def register():
    RIGIALL_PT_panel.bl_category = bpy.context.preferences.addons[__package__].preferences.category
    
    for i in classes:
        bpy.utils.register_class(i)
    
def unregister():
    for i in classes:
        bpy.utils.unregister_class(i)