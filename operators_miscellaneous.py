import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty
from .operators import generictext

class node_input_mapper:
    def __init__(self, modifier: bpy.types.NodesModifier):
        self.inp_map = {item.name: item.identifier for item in modifier.node_group.interface.items_tree if getattr(item, 'in_out', '') == 'INPUT'}
        self.mod = modifier
    def __getitem__(self, key):
        return self.mod[self.inp_map[key]]
    def __setitem__(self, key, value):
        self.mod[self.inp_map[key]] = value

class RIGIALL_OT_make_bones_renderable(Operator):
    bl_idname = 'rigiall.make_bones_renderable'
    bl_label = 'Make Bones Renderable'
    bl_description = 'Make mesh copies of custom bone shapes, which are converted to tubes through geometry nodes, allowing them to be rendered'
    bl_options = {'UNDO'}

    exclude_hidden_bones: BoolProperty(name='Exclude Hidden Bones', description='If enabled, hidden bones will not be realized', default=True)

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', '') == 'ARMATURE'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if bpy.app.version < (4, 2, 0):
            self.report({'ERROR'}, 'This feature is for Blender 4.2+')
            return {'CANCELLED'}
        
        from mathutils import Matrix, Vector
        from .main import initialize_wire_to_curve

        blend_data = context.blend_data

        node_group = initialize_wire_to_curve(context)

        obj = context.object
        themes = context.preferences.themes['Default']
        bone_color_sets = themes.bone_color_sets
        bone_themes = {'THEME' + f'{n+1:02d}': set for n, set in enumerate(bone_color_sets)}

        ids_for_deletion = set()

        if self.exclude_hidden_bones:
            bones = set()
            [bones.update(set(bone_col.bones)) for bone_col in context.object.data.collections if bone_col.is_visible]
            [bones.discard(pbone.bone) for pbone in context.object.pose.bones if pbone.bone.hide]
        else:
            bones = set(context.object.data.bones)

        if not (collection := obj.get('real_bone_shapes', None)):
            parent_col = obj.users_collection[0]
            user_map: dict[bpy.types.ID, set[bpy.types.ID]] = blend_data.user_map(key_types={'COLLECTION'}, value_types={'COLLECTION'})

            children_recursive: list = context.scene.collection.children_recursive
            children_recursive = set(children_recursive[:children_recursive.index(parent_col)])

            while (parent_col.override_library) or (parent_col.library):
                parent_col = next(iter(user_map[parent_col].intersection(children_recursive)), context.scene.collection)

            collection = blend_data.collections.new(f'{obj.name} Render Bones')
            parent_col.children.link(collection)

            if obj.library or obj.override_library:
                self.report({'WARNING'}, 'Object is linked or overridden. Bone collection cannot be recycled!')
            else:
                obj['real_bone_shapes'] = collection
        else:

            existing_bones = set(key for key, value in collection.items() if isinstance(value, bpy.types.ID))

            remove_bones = existing_bones.difference(set(map(lambda a: a.name, bones)))
            remove_objs: set[bpy.types.Object] = set(map(lambda a: collection[a], remove_bones))
            [ids_for_deletion.add(obj.data) for obj in remove_objs]

            [collection.__delitem__(bone) for bone in remove_bones]
            blend_data.batch_remove(remove_objs)


        bone_map_data = dict()

        for bone in set(bones):
            pbone: bpy.types.PoseBone = obj.pose.bones[bone.name]
            if not pbone.custom_shape: continue
            if not pbone.custom_shape.type in {'MESH', 'CURVE'}: continue
            if not (mesh_data := bone_map_data.get(pbone.custom_shape.data)):
                mesh_data = pbone.custom_shape.data.copy()
                if  mesh_data.override_library:
                    mesh_data = mesh_data.make_local()

                bone_map_data[pbone.custom_shape.data] = mesh_data
                mesh_data.materials.append(blend_data.materials['Rigi-All Bone Colorer'])

            if (real_shape := collection.get(bone.name)):
                if not isinstance(real_shape.data, type(mesh_data)):
                    ids_for_deletion.add(real_shape.data)
                    bpy.data.objects.remove(real_shape)
                    real_shape = blend_data.objects.new(bone.name, mesh_data)
                    collection.objects.link(real_shape)
                else:
                    ids_for_deletion.add(real_shape.data)
                    real_shape.data = mesh_data
            else:
                real_shape = blend_data.objects.new(bone.name, mesh_data)
                collection.objects.link(real_shape)

            collection[bone.name] = real_shape
            
            if bone.color.palette == 'DEFAULT':
                normal, select, active = themes.view_3d.wire, themes.view_3d.bone_pose, themes.view_3d.bone_pose_active
            elif bone.color.palette == 'CUSTOM':
                palette = bone.color.custom
                normal, select, active = palette.normal, palette.select, palette.active
            else:
                palette = bone_themes[bone.color.palette]
                normal, select, active = palette.normal, palette.select, palette.active
                
            custom_shape_translation = Matrix.Translation(pbone.custom_shape_translation)
            custom_shape_rotation = pbone.custom_shape_rotation_euler.to_matrix().to_4x4()
            scale = pbone.custom_shape_scale_xyz
            custom_shape_scale = Matrix([
                [scale[0], 0, 0, 0],
                [0, scale[1], 0, 0],
                [0, 0, scale[2], 0],
                [0, 0, 0, 1]
            ])
            custom_shape_matrix = custom_shape_translation @ custom_shape_rotation @ custom_shape_scale
            matrix = (pbone.custom_shape_transform or pbone).matrix
            matrix = obj.matrix_world @ matrix @ custom_shape_matrix @ (Matrix.Scale(pbone.bone.length, 4) if pbone.use_custom_shape_bone_size else Matrix())
            real_shape.parent = obj
            real_shape.parent_bone = (pbone.custom_shape_transform or pbone).name
            real_shape.parent_type = 'BONE'
            real_shape.matrix_world = matrix

            mod: bpy.types.NodesModifier = (real_shape.modifiers.get('Wire to Curve') or real_shape.modifiers.new('Wire to Curve', 'NODES'))
            mod.node_group = node_group

            mod = node_input_mapper(mod)

            normal = Vector(normal).to_4d()
            select = Vector(select).to_4d()
            active = Vector(active).to_4d()
            mod['Normal'], mod['Select'], mod['Active'] = normal, select, active
            
            if bone.collections:
                real_shape.driver_remove('hide_viewport')
                view_curve = real_shape.driver_add('hide_viewport')
                view_driver = view_curve.driver
                
                real_shape.driver_remove('hide_render')
                render_curve = real_shape.driver_add('hide_render')
                render_driver = render_curve.driver
                
                expr = f'not ({" or ".join(["V" + str(n) for n in range(len(bone.collections))])}) or bone'
                view_driver.expression = expr
                render_driver.expression = expr
                # not (V0 or V1 or V2 or...)
                
                var = view_driver.variables.new()
                var.name = 'bone'
                t = var.targets[0]
                t.id_type = 'ARMATURE'
                t.id = obj.data
                path = bone.path_from_id('hide')
                t.data_path = path

                var = render_driver.variables.new()
                var.name = 'bone'
                t = var.targets[0]
                t.id_type = 'ARMATURE'
                t.id = obj.data
                path = bone.path_from_id('hide')
                t.data_path = path

                for n, bone_col in enumerate(bone.collections):
                    var = view_driver.variables.new()
                    var.name = f'V{n}'
                    t = var.targets[0]
                    t.id_type = 'ARMATURE'
                    t.id = obj.data
                    path = bone_col.path_from_id('is_visible')
                    t.data_path = path
                    
                    var = render_driver.variables.new()
                    var.name = f'V{n}'
                    t = var.targets[0]
                    t.id_type = 'ARMATURE'
                    t.id = obj.data
                    path = bone_col.path_from_id('is_visible')
                    t.data_path = path
        
        ids_for_deletion.discard(None)
        ids_for_deletion = set(filter(lambda id: id.users == 0, ids_for_deletion))
        blend_data.batch_remove(ids_for_deletion)

        return {'FINISHED'}

class RIGIALL_OT_bodygroup_menu_add(generictext):
    bl_idname = 'rigiall.bodygroup_menu_add'
    bl_label = 'Add Visibility Switch'
    bl_description = 'A tool that helps make menu switches to hide/show mesh objects. All selected objects will be tied to the active object' 

    bl_options = {'UNDO'}

    conflicting_objects = None

    @classmethod
    def poll(cls, context):
        return bool(getattr(context, 'object', False))
    
    def invoke(self, context, event):
        obj = context.object
        items = set(context.selected_objects).difference(set([obj]))
        conflicting_objects = list()

        for subject in items:
            drivers = getattr(subject.animation_data, 'drivers', None)
            if not drivers:
                continue
            if drivers.find('hide_viewport') or drivers.find('hide_render'):
                conflicting_objects.append(subject)
        
        if conflicting_objects:
            self.conflicting_objects = conflicting_objects
            return context.window_manager.invoke_props_dialog(self, width=350)
        return self.execute(context)
        
    def draw(self, context):
        layout = self.layout
        sentence = ['Warning! The following objects already have their visibility driven:']
        icon = ['ERROR']
        size = ['56']
        self.draw_boxes(layout, sentence, icon, size)

        box = layout.box()
        for obj in self.conflicting_objects:
            box.label(text=obj.name)
        
        sentence = [
            'Continuing will not immediately overwrite their driver data, but building the final visiblity switch will.',
            'Continue anyways?'
        ]
        icon = [
            'NONE',
            'QUESTION'
        ]
        size = [
            '64',
            '56'
        ]

        self.draw_boxes(layout, sentence, icon, size)

    def execute(self, context):
        obj = context.object
        items = set(context.selected_objects).difference(set([obj]))
        helper = obj.rigiall_bodygroup_helper
        menus = helper.bodygroup_menus

        tally = 0
        suffix = ''
        name = 'Visibility Switch'

        while menus.get(name + suffix, False):
            tally += 1
            suffix = ' ' + str(tally)

        new_menu = menus.add()
        new_menu.name = name + suffix

        menu_items = new_menu.menu_items

        for item in items:
            new_item = menu_items.add()
            new_item.name = item.name
            new_item.object = item

        helper.index = len(menus)-1
        helper.active_item = len(menus)-1

        context.area.tag_redraw()

        return {'FINISHED'}
    
class RIGIALL_OT_bodygroup_menu_remove(Operator):
    bl_idname = 'rigiall.bodygroup_menu_remove'
    bl_label = 'Remove Bodygroup Menu'
    bl_description = 'Remove bodygroup menu' 

    bl_options = {'UNDO'}

    remove_associated_property: BoolProperty(
        name='Remove Custom Property',
        description='If enabled, the custom property switch will be removed along with the visibility menu item',
        default=True
    )

    def invoke(self, context, event):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menus = helper.bodygroup_menus
        menu = menus[helper.index]

        if obj.get(menu.name) != None:
            return context.window_manager.invoke_props_dialog(self)
        
        return self.execute(context)

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menus = helper.bodygroup_menus
        menu = menus[helper.index]

        if (obj.get(menu.name) != None) and self.remove_associated_property:
            del obj[menu.name]

        menus.remove(helper.index)
        helper.index = min(helper.index, len(menus)-1)
        context.area.tag_redraw()
        return {'FINISHED'}

class RIGIALL_OT_bodygroup_menu_edit(Operator):
    bl_idname = 'rigiall.bodygroup_menu_edit'
    bl_label = 'Edit Bodygroup Menu'
    bl_description = 'Edit bodygroup menu' 

    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        helper.active_item = helper.index
        return {'FINISHED'}

class RIGIALL_OT_bodygroup_menu_back(Operator):
    bl_idname = 'rigiall.bodygroup_menu_back'
    bl_label = 'Go Back'
    bl_description = 'Go back to main menu' 

    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        helper.active_item = -1
        return {'FINISHED'}

class RIGIALL_OT_bodygroup_item_add(Operator):
    bl_idname = 'rigiall.bodygroup_item_add'
    bl_label = 'Add Visibility Item'
    bl_description = 'Add a new item to the visibility switch'

    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menu = helper.bodygroup_menus[helper.index]

        menu.menu_items.add()
        return {'FINISHED'}
    
class RIGIALL_OT_bodygroup_item_remove(Operator):
    bl_idname = 'rigiall.bodygroup_item_remove'
    bl_label = 'Remove Visibility Item'
    bl_description = 'Remove an item from the visibility switch'
    index: IntProperty()

    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menu = helper.bodygroup_menus[helper.index]

        menu.menu_items.remove(self.index)
        
        return {'FINISHED'}
    
class RIGIALL_OT_bodygroup_item_move(Operator):
    bl_idname = 'rigiall.bodygroup_item_move'
    bl_label = 'Move Visibility Item'
    bl_description = 'Move an item in the visibility switch'
    index: IntProperty()
    move: IntProperty()

    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menu = helper.bodygroup_menus[helper.index]

        menu.menu_items.move(self.index, self.index + self.move)
        
        return {'FINISHED'}

#def is_obj_controlled_by_other_switch(controller: bpy.types.Object, subject: bpy.types.Object, switch: str):
#    sub_helper = subject.rigiall_bodygroup_helper
#    sub_controller = sub_helper.visibility_controller
#    sub_switch_name = sub_helper.switch_name
#    drivers = getattr(subject.animation_data, 'drivers', None)
#    if not drivers:
#        return False
#    has_vis_drivers = bool(drivers.find('hide_viewport')) or bool(drivers.find('hide_render'))
#    if has_vis_drivers and sub_controller and sub_switch_name:
#        return (sub_controller != controller) or (sub_switch_name != switch)
#    elif has_vis_drivers:
#        return True
#    return False

class RIGIALL_OT_bodygroup_single_menu_build(Operator):
    bl_idname = 'rigiall.bodygroup_single_menu_build'
    bl_label = 'Build Visibility Switch'
    bl_description = 'Build a single visiblity switch'

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        menu = helper.bodygroup_menus[helper.index]
        menu_items = menu.menu_items
        enum_items = []
        obj[menu.name] = 0

        for n, item in enumerate(menu_items):
            enum_items.append(
                (
                    str(n),
                    item.name,
                    item.description,
                    item.icon,
                    n
                )
            )

            if not item.object: continue
            subject = item.object
            for path in ['hide_viewport', 'hide_render']:
                subject.driver_remove(path)
                curve = subject.driver_add(path)
                driver = curve.driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                targs = var.targets[0]
                targs.id_type = 'OBJECT'
                targs.id = obj
                targs.data_path = f'["{menu.name}"]'
                driver.expression = f'var != {n}'
        
        if obj.get(menu.name):
            del obj[menu.name]
        
        ui_settings = obj.id_properties_ui(menu.name)
        ui_settings.update(
            min=0,
            max=len(enum_items)-1,
            items=enum_items
        )

        self.report({'INFO'}, "Access the visiblity switch via the object's custom properties")
        return {'FINISHED'}

class RIGIALL_OT_bodygroup_menus_build(generictext):
    bl_idname = 'rigiall.bodygroup_menus_build'
    bl_label = 'Build All Visibility Switches'
    bl_description = 'Build all visiblity switches'

    conflicting_controllers = None

    def invoke(self, context, event):
        from collections import defaultdict
        subject_controller = defaultdict(list)

        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        for menu in helper.bodygroup_menus:
            for item in menu.menu_items:
                if not item.object:
                    continue
                subject_controller[item.object.name].append(menu.name)

        subject_controller = dict(
            filter(
                lambda kv: len(kv[1]) > 1,
                subject_controller.items()
            )
        )

        if subject_controller:
            self.conflicting_controllers = subject_controller
            return context.window_manager.invoke_props_dialog(self, width=500)
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        sentence = ['Warning! The following objects are used in multiple switches']
        icon = ['ERROR']
        size = ['64']
        self.draw_boxes(layout, sentence, icon, size)

        box = layout.box()
        for subject, controllers in self.conflicting_controllers.items():
            self.draw_boxes(
                box,
                [f'{subject}: {", ".join(controllers)}'],
                ['NONE'],
                ['72']
            )
            #box.label(text=f'{subject}: {", ".join(controllers)}')
        
        sentence = [
            "Only the last switch will drive the object's visibility.",
            'Continue anyways?'
        ]
        icon = [
            'NONE',
            'QUESTION'
        ]
        size = [
            '64',
            '56'
        ]

        self.draw_boxes(layout, sentence, icon, size)

    def execute(self, context):
        obj = context.object
        helper = obj.rigiall_bodygroup_helper
        for menu in helper.bodygroup_menus:
            menu_items = menu.menu_items
            enum_items = []
            obj[menu.name] = 0

            for n, item in enumerate(menu_items):
                enum_items.append(
                    (
                        str(n),
                        item.name,
                        item.description,
                        item.icon,
                        n
                    )
                )

                if not item.object: continue
                subject = item.object
                for path in ['hide_viewport', 'hide_render']:
                    subject.driver_remove(path)
                    curve = subject.driver_add(path)
                    driver = curve.driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    targs = var.targets[0]
                    targs.id_type = 'OBJECT'
                    targs.id = obj
                    targs.data_path = f'["{menu.name}"]'
                    driver.expression = f'var != {n}'
            
            if obj.get(menu.name):
                del obj[menu.name]
            
            ui_settings = obj.id_properties_ui(menu.name)
            ui_settings.update(
                min=0,
                max=len(enum_items)-1,
                items=enum_items
            )

        self.report({'INFO'}, "Access the visiblity switch(es) via the object's custom properties")
        return {'FINISHED'}

classes = [
    RIGIALL_OT_make_bones_renderable,
    RIGIALL_OT_bodygroup_menu_add,
    RIGIALL_OT_bodygroup_menu_remove,
    RIGIALL_OT_bodygroup_menu_edit,
    RIGIALL_OT_bodygroup_menu_back,
    RIGIALL_OT_bodygroup_item_add,
    RIGIALL_OT_bodygroup_item_remove,
    RIGIALL_OT_bodygroup_item_move,
    RIGIALL_OT_bodygroup_single_menu_build,
    RIGIALL_OT_bodygroup_menus_build
]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    r()

def unregister():
    ur()