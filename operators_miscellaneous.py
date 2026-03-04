import bpy
from bpy.types import Operator
from bpy.props import BoolProperty

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
        from mathutils import Matrix, Vector
        from .main import initialize_wire_to_curve

        blend_data = context.blend_data

        node_group = initialize_wire_to_curve(context)

        obj = context.object
        themes = context.preferences.themes['Default']
        bone_color_sets = themes.bone_color_sets
        bone_themes = {'THEME' + f'{n+1:02d}': set for n, set in enumerate(bone_color_sets)}

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

            [collection.__delitem__(bone) for bone in remove_bones]
            blend_data.batch_remove(remove_objs)


        bone_map_data = dict()

        for bone in set(bones):
            pbone: bpy.types.PoseBone = obj.pose.bones[bone.name]
            if not pbone.custom_shape: continue
            if not (mesh_data := bone_map_data.get(pbone.custom_shape.data)):

                mesh_data = pbone.custom_shape.data.copy()
                if  mesh_data.override_library:
                    mesh_data = mesh_data.make_local()

                bone_map_data[pbone.custom_shape.data] = mesh_data
                mesh_data.materials.append(blend_data.materials['Rigi-All Bone Colorer'])

            if (real_shape := collection.get(bone.name)):
                if not isinstance(real_shape.data, type(mesh_data)):
                    bpy.data.objects.remove(real_shape)
                    real_shape = blend_data.objects.new(bone.name, mesh_data)
                    collection.objects.link(real_shape)
                else:
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
        
        return {'FINISHED'}
    
classes = [
    RIGIALL_OT_make_bones_renderable
]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    r()

def unregister():
    ur()