import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty
from math import degrees, pi
from mathutils import Quaternion

QUAT_IDENTITY = Quaternion()
icons = bpy.types.UILayout.bl_rna.functions['label'].parameters['icon']

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
        blend_data = context.blend_data
        data_groups = blend_data.node_groups
        data_materials = blend_data.materials
        
        layout.row().label(text='View Mode:')
        row = layout.row()
        row.scale_y = 1.6
        row.prop(props, 'view', expand=True)
        layout.separator()

        if props.view == 'RIGGING':
            
            if getattr(context.object, 'type', None) != 'ARMATURE':
                layout.row().label(text='Select an armature!')
                return None
            elif getattr(context.object.data, 'rigify_colors', []): #getattr(context.object, 'data', {}).get('RIGI-ALL_INITIALIZED'):
                pass
            elif context.object.get('rig_ui'):
                layout.row().label(text='This is a Rigify rig!')
                return None
            else:
                box = layout.box()
                row = box.row()
                row.label(text='', icon='STYLUS_PRESSURE')
                row.operator('rigiall.init')
                #layout.row().label(text='Initialize the rig!')
                return None
            
            if context.object.mode in {'POSE', 'EDIT'}:
                row = layout.row(align=True)
                row.prop(context.object.pose, 'use_mirror_x', toggle=True, icon='MOD_MIRROR', text='Pose Mirror')
                row.prop(context.object.data, 'use_mirror_x', toggle=True, icon='MOD_MIRROR', text='Edit Mode Mirror')
            
            if context.object.mode != 'POSE':
                layout.row().label(text='Enter pose mode!')
                return None
            
            if not getattr(context.object.data, 'rigify_colors', []): #context.object.data.get('RIGI-ALL_INITIALIZED'):
                return None
            # force rigify to build rig types
            bone = context.active_pose_bone
            if (not context.window_manager.rigify_types) and bone:
                bpy.types.BONE_PT_rigify_buttons.draw(self, context)
            
            row = layout.row()
            row.prop(props, 'automatic_symmetry')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = 'Set the property to what side of which axis the right side of the rig is. For best results, make sure the right side of the rig is on -X, and the symmetry mode is -X'
            op.size = '58'
            op.icons = 'QUESTION'
            op.width=350
            if props.automatic_symmetry:
                box = layout.box()
                row = box.row()
                r = row.row()
                r.alignment = 'LEFT'
                r.label(text='Right side is on...')
                r = row.row()
                r.prop(props, 'symmetry_mode', text='', icon='OUTLINER_DATA_EMPTY')
                
                if context.object.matrix_basis.to_quaternion() != QUAT_IDENTITY:
                    box.row().label(text="Don't forget to apply rotation on the armature!")

            row = layout.row()
            row.prop(props, 'fix_symmetry', toggle=True, emboss=False, icon='DOWNARROW_HLT' if props.fix_symmetry else 'RIGHTARROW')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = 'This helps to format bone names to make them compatible for symmetry posing. For example, a pair of bones named "upper_r_arm" and "upper_l_arm" will not support symmetry. However, if you set the left and right symmetry keywords to "_l_" and "_r_" respectively, they will be formatted to "upper_arm.R" "upper_arm.L"'
            op.size = '56'
            op.icons='QUESTION'
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
                
                col.row().operator('rigiall.fix_symmetry_name', text='Format Names')

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

            layout.separator()
            layout.box().row().operator('rigiall.make_generic_chain')

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
                row = box_arms.row()
                row.operator('rigiall.makearms')

                row = box_legs.row()
                op = row.operator('rigiall.makelegs')
                op.text = 'The bones should rotate around this axis. X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'

                row = box_arms.row()
                op = row.operator('rigiall.makefingers_ambi', text='Make Fingers')
                op.text = 'Rotating towards the selected axis should curl the fingers inward. +X Manual by default.'
                op.size = '56'
                op.icons = 'BLANK1'

                box_torso.row().operator('rigiall.makeshoulders', text='Make Shoulders')
            else:
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


            row = box_misc.row(align=True)
            row.alignment = 'EXPAND'
            r = row.row()
            r.operator('rigiall.extras')
            r = row.row()
            r.alignment = 'RIGHT'
            r.operator('rigiall.extras_manual', text='Only Selected')
            for roll, sign in [(pi/2, '+'), (-pi/2, '-')]:
                col = box_misc.column()
                row = col.row()
                row.label(text=f'Roll by {int(degrees(roll))}°')
                row = col.row(align=True)
                for axis in ['X', 'Y', 'Z']:
                    op = row.operator('rigiall.adjustroll', text=sign+axis)
                    op.roll = roll
                    op.axis = axis
            
            box_misc.row().operator('rigiall.noroll')
            row = box_misc.row()
            row.operator('rigiall.extend_to_child')
        elif props.view == 'CLEAN_UP':
            col = layout.column()
            row = col.row()
            row.label(text='Make Mesh Compatible')
            op = row.operator('rigiall.textbox', icon='QUESTION', text='')
            op.text = '''Unless original bones were preserved, meshes will not automatically follow the armature. You may either force the mesh to adapt to the skeleton, or force the skeleton to adapt to the mesh.'''
            op.icons = 'QUESTION'
            op.size = '64'
            op.width = 340

            box = col.box()
            row = box.row()
            r = row.row(align=True)
            r.label(text='', icon='MESH_DATA')
            r.label(text='', icon='RIGHTARROW')
            r.label(text='', icon='ARMATURE_DATA')
            row.operator('rigiall.tweakmesh')
            row = box.row()
            r = row.row(align=True)
            r.label(text='', icon='ARMATURE_DATA')
            r.label(text='', icon='RIGHTARROW')
            r.label(text='', icon='MESH_DATA')
            op = row.operator('rigiall.remove_def_prefix')
            op.text = 'This is destructive to the rig, and is recommended if you add the "DEF-" prefix to vertex groups instead.\nContinue anyways?'
            op.icons = 'ERROR,QUESTION'
            op.size = '56,56'
            op.width=360

            col = layout.column()
            col.label(text='Bone Shapes')
            box = col.box()
            row = box.row()
            row.label(text='', icon='GROUP_BONE')
            row.operator('rigiall.deduplicate_boneshapes')

            col = layout.column()
            row = col.row()
            row.label(text='Remove Unused Bones, Vertex Groups')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = '''This helps trim away unnecessary vertex groups or bones.'''
            op.icons = 'QUESTION'
            op.size = '56'
            op.width = 315
            box = col.box()
            row = box.row()
            row.label(text='', icon='GROUP_VERTEX')
            row.operator('rigiall.remove_unused_vgroups')
            row = box.row()
            row.label(text='', icon='BONE_DATA')
            row.operator('rigiall.remove_unused_bones')
            row = box.row()
            #r = row.row(align=True)
            #r.label(text='', icon='GROUP_VERTEX')
            #r.label(text='', icon='BONE_DATA')
            #row.operator('rigiall.remove_unused_bones_and_vgroups')

            box = row.box().row()
            i = box.row().column(align=True)
            i.label(text='', icon='GROUP_VERTEX')
            i.label(text='', icon='BONE_DATA')
            o = box.row()
            o.scale_y = 2
            o.operator('rigiall.remove_unused_bones_and_vgroups')

            col = layout.column()
            row = col.row()
            row.label(text='Fuse Armatures')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = '''This tool joins two selected armatures, but prevents bones from being duplicated. This essentially adds to an armature.'''
            op.size = '64'
            op.icons = 'QUESTION'
            box = col.box()
            main_row = box.row()
            row = main_row.row(align=True)
            row.prop(props, 'parasite', text='', icon='ARMATURE_DATA')
            row.label(text='', icon='RIGHTARROW')
            row.prop(props, 'host', text='', icon='ARMATURE_DATA')
            row = main_row.row()
            row.alignment = 'RIGHT'
            row.operator('rigiall.fuse_armatures', text='Fuse')
        elif props.view == 'MISCELLANEOUS':
            col = layout.column()
            row = col.row()
            row.label(text='Make Bones Renderable')
            op = row.operator('rigiall.textbox', icon='QUESTION', text='')
            op.text = '''This tool realizes custom bone shapes, either by converting wire shapes to a tube or repeating the shape data.'''
            op.icons = 'QUESTION'
            op.size = '64'
            op.width = 375
            
            box = col.box()
            row = box.row()
            row.label(text='', icon='RESTRICT_RENDER_OFF')
            row.operator('rigiall.make_bones_renderable')
            if (ng := (data_groups.get('Rigi-All Wire to Curve') or data_groups.get('Rigi-All Wire to Curve -4.5'))):
                box.row().prop(ng.nodes['CURVE_THICKNESS'].inputs[1], 'default_value', text='Wire Thickness * 0.01')
                box.row().prop(data_groups['.rigiall_bone_params'].nodes[0].inputs[0], 'default_value', text='Wire Transparency')
                main = box.row()
                r = main.row()
                r.alignment = 'LEFT'
                r.label(text='Transparency Method:')
                r = main.row()
                r.alignment = 'EXPAND'
                r.prop(data_materials['Rigi-All Bone Colorer'], 'surface_render_method', text='')
                r = box.row()
                r.alignment = 'CENTER'
                r.prop(data_materials['Rigi-All Bone Colorer'], 'use_transparent_shadow')
            else:
                r = box.row()
                r.active = False
                r.label(text='Properties will be exposed when used.')
                #box.row().prop(context.window_manager.rigiall_props, 'wire_thickness', text='Wire Thickness * 0.01')

            obj = getattr(context, 'object', None)
            helper = getattr(obj, 'rigiall_bodygroup_helper', None)
            active_item = getattr(helper, 'active_item', -1)
            items = getattr(helper, 'bodygroup_menus', None)

            col = layout.column()
            row = col.row()
            row.label(text='Visibility Switch Helper')
            op = row.operator('rigiall.textbox', text='', icon='QUESTION')
            op.text = '''This tool makes it easy to drive the visibility of objects with a custom property menu. Helpful for managing accessories of a model.
Items in a visiblity switch do not require an object. You can leave them empty to help drive another property with the switch.'''
            op.icons = 'QUESTION,OUTLINER_DATA_LIGHT'
            op.size = '68,66'
            op.width=385

            box = col.box()
            if active_item == -1:
                box.operator('rigiall.bodygroup_menu_add', icon='ADD')
            else:
                box.operator('rigiall.bodygroup_menu_back', icon='BACK')
            
            if items:
                if helper.active_item != -1:
                    menu = items[helper.active_item]
                    menu_items_count = len(menu.menu_items)
                    allow_build = menu_items_count > 0
                    row = box.row(align=True)
                    r = row.row()
                    r.alignment = 'LEFT'
                    r.label(text='Property Name:')
                    r = row.row()
                    r.prop(menu, 'name', text='')
                    for n, item in enumerate(menu.menu_items):
                        subbox = box.box()
                        top_row = subbox.row()
                        properties = top_row.row()
                        operators = top_row.row(align=True)
                        operators1 = operators.row().column(align=True)
                        operators2 = operators.row().column(align=True)
                        operators2.scale_y = 2
                        col = properties.column(align=True)
                        row1 = col.row().split(factor=.6)
                        row2 = col.row().split(factor=.6)
                        row11 = row1.row()
                        row12 = row1.row()
                        row21 = row2.row()
                        row22 = row2.row()

                        if menu_items_count == 1:
                            pass
                        elif n == 0:
                            op_col = operators1.row()
                            op = op_col.operator('rigiall.bodygroup_item_move', icon='TRIA_DOWN', text='')
                            op.index = n
                            op.move = 1
                            op_col.scale_y = 2
                        elif n == menu_items_count-1:
                            op_col = operators1.row()
                            op = op_col.operator('rigiall.bodygroup_item_move', icon='TRIA_UP', text='')
                            op.index = n
                            op.move = -1
                            op_col.scale_y = 2
                        else:
                            op_col = operators1.row()
                            op = op_col.operator('rigiall.bodygroup_item_move', icon='TRIA_UP', text='')
                            op.index = n
                            op.move = -1
                            op_col.enabled = n != 0

                            op_col = operators1.row()
                            op = op_col.operator('rigiall.bodygroup_item_move', icon='TRIA_DOWN', text='')
                            op.index = n
                            op.move = 1
                            op_col.enabled = n != menu_items_count-1

                        operators2.operator('rigiall.bodygroup_item_remove', icon='REMOVE', text='').index = n
                        operators2.scale_x = 2.0 if menu_items_count == 1 else 1.0

                        row = row11.row()
                        r = row.row(align=True)
                        r.alignment = 'LEFT'
                        r.label(text='Object:')
                        r = row.row()
                        r.prop(item, 'object', text='')
                        
                        row = row12.row()
                        r = row.row(align=True)
                        r.alignment = 'LEFT'
                        r.label(text='Name:')
                        r = row.row()
                        r.prop(item, 'name', text='')

                        row = row21.row()
                        r = row.row(align=True)
                        r.alignment = 'LEFT'
                        r.label(text='Desc.:')
                        r = row.row()
                        r.prop(item, 'description', text='')

                        row = row22.row()
                        r = row.row(align=True)
                        r.alignment = 'LEFT'
                        r.label(text='Icon:')
                        r = row.row()
                        r.prop_search(item, 'icon', icons, 'enum_items', icon='NONE' if not item.icon else item.icon, text='')
                    
                    box.operator('rigiall.bodygroup_item_add', icon='ADD')
                    row = box.row()
                    row.enabled = allow_build
                    row.operator('rigiall.bodygroup_single_menu_build')
                else:
                    row = box.row()
                    row.template_list('RIGIALL_UL_bodygroup_entries',
                                    'Rigi-All Bodygroup Menus',
                                    helper, 'bodygroup_menus',
                                    helper, 'index'
                    )
                    row.operator('rigiall.bodygroup_menu_remove', text='', icon='REMOVE')
                    box.operator('rigiall.bodygroup_menus_build')
            

class RIGIALL_UL_bodygroup_entries(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index = 0, flt_flag = 0):
        #clamp_index = min(data.index, len(data.bodygroup_menus)-1)
        #active_item = data.bodygroup_menus[clamp_index]
        if index == data.index:
            row = layout.row()
            split = row.split(factor=.66)
            split.prop(item, 'name', text='', emboss=False)
            split.operator('rigiall.bodygroup_menu_edit', text='Edit')
        else:
            row = layout.row()
            split = row.split(factor=.66)
            split.label(text=item.name)
            #split.operator('rigiall.bodygroup_menu_edit', text='', icon='FORWARD')
            r = split.row()
            r.alignment = 'CENTER'
            r.label(text='Edit')
            r.active = False
            #split.enabled = False
        pass

classes = [
    RIGIALL_PT_panel,
    rigiall_OT_change_category,
    RIGIALL_UL_bodygroup_entries
]

def register():
    RIGIALL_PT_panel.bl_category = bpy.context.preferences.addons[__package__].preferences.category
    
    for i in classes:
        bpy.utils.register_class(i)
    
def unregister():
    for i in classes:
        bpy.utils.unregister_class(i)