import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty
from .operators import generictext, isolate, mode
from .main import null

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

class rigiall_ot_remove_def_prefix(generictext):
    bl_idname = 'rigiall.remove_def_prefix'
    bl_label = 'Remove "DEF-" from Bone Names'
    bl_description = 'Change the name of deform bones to be compatible with the mesh. Not recommended'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', None) == 'ARMATURE'
    
    def execute(self, context):
        if context.object.data.collections_all.get('overlaying'):
            self.report({'ERROR'}, "This is not necessary! You already have the original bone names from the merged armature!")
            return {'CANCELLED'}
        
        obj_copy = context.object.copy()
        data_copy = context.object.data.copy()
        obj_copy.data = data_copy

        bones: set[bpy.types.Bone] = set(getattr(data_copy.collections_all.get('DEF', None), 'bones', data_copy.bones))
        bones.update(set(getattr(data_copy.collections_all.get('Extras'), 'bones', bones)))
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

class keep_highest_value(dict):
    def __setitem__(self, key, value: float):
        super().__setitem__(key, max(self[key], value))
    def __getitem__(self, key):
        return super().get(key, 0.0)
    def update(self, dictionary: dict):
        for key, value in dictionary.items():
            self.__setitem__(key, value)

def get_used_groups(data: bpy.types.Mesh) -> set[int]:
    import numpy as np
    used_groups = set()
    for vert in data.vertices:
        groups = np.zeros(len(vert.groups), dtype=int)
        vert.groups.foreach_get('group', groups)
        used_groups.update(set(groups))
    return used_groups

def get_used_groups_and_weights(data: bpy.types.Mesh) -> tuple[set[int], keep_highest_value[int|str, float]]:
    import numpy as np
    used_weights = keep_highest_value()
    used_groups = set()

    for vert in data.vertices:
        weights = np.zeros(len(vert.groups), dtype=np.float32)
        groups = np.zeros(len(vert.groups), dtype=int)
        vert.groups.foreach_get('weight', weights)
        vert.groups.foreach_get('group', groups)
        used_groups.update(set(groups))
        [used_weights.__setitem__(group, weight) for group, weight in zip(groups, weights)]

    return used_groups, used_weights

class RIGIALL_OT_remove_unused_vgroups(Operator):
    bl_idname = 'rigiall.remove_unused_vgroups'
    bl_label = 'Remove Unassigned Vertex Groups'
    bl_description = 'Remove all vertex groups with no vertices assigned'
    bl_options = {'UNDO'}

    only_remove_bone_groups: BoolProperty(name='Only remove bone groups', description='Only remove vertex groups associated with an armature. If disabled, all vertex groups are subject to removal', default=True)
    remove_if_zero_weight: BoolProperty(name='Remove groups with zero vertex weight', description='Instead of just removing groups without any vertices assigned, enabling this will also remove groups if they are absolutely unused', default=False)

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', '') == 'MESH'
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        self.layout.prop(self, 'only_remove_bone_groups')
        self.layout.prop(self, 'remove_if_zero_weight')

    def remove_groups(self, context: bpy.types.Context, objs: list[bpy.types.Object], remove_zero_weight: bool, only_remove_bone_groups: bool = True):
        for obj in objs:
            if obj.type != 'MESH': continue

            if not only_remove_bone_groups:
                pass
            elif (armature := next(filter(lambda a: a.type == 'ARMATURE', obj.modifiers), null).object):
                bones = set(map(lambda a: a.name, armature.data.bones))
            elif (armature := obj.parent) and obj.parent_type == 'ARMATURE':
                bones = set(map(lambda a: a.name, armature.data.bones))
            else:
                self.report({'ERROR'}, f'"Only remove bone groups" was enabled, but "{obj.name}" has no referenced armature!')

            if not remove_zero_weight:
                used_groups = get_used_groups(obj.data)
                used_groups = set(map(lambda a: obj.vertex_groups[a].name, used_groups))
                vgroups = obj.vertex_groups

                for group in list(vgroups):
                    if only_remove_bone_groups and not (group.name in bones):
                        continue
                    if not group.name in used_groups:
                        vgroups.remove(group)
            else:
                used_groups, used_weights = get_used_groups_and_weights(obj.data)
                used_groups = set(map(lambda a: obj.vertex_groups[a].name, used_groups))
                used_weights = set([obj.vertex_groups[key].name for key, value in used_weights.items() if value > 0.0])
                vgroups = obj.vertex_groups
                for group in list(vgroups):
                    if only_remove_bone_groups and not (group.name in bones):
                        continue
                    if not group.name in used_groups:
                        vgroups.remove(group)
                        continue
                    if not group.name in used_weights:
                        vgroups.remove(group)
        return {'FINISHED'}

    def execute(self, context):
        return self.remove_groups(context, context.selected_objects, self.remove_if_zero_weight, self.only_remove_bone_groups)

class RIGIALL_OT_remove_unused_bones(Operator):
    bl_idname = 'rigiall.remove_unused_bones'
    bl_label = 'Remove Unused Bones'
    bl_description = 'Removes bones unused by mesh(es)'
    bl_options = {'UNDO'}

    remove_if_zero_weight: BoolProperty(name='Remove groups with zero vertex weight', description='Instead of just removing groups without any vertices assigned, enabling this will also remove groups if they are absolutely unused', default=False)

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', '') == 'ARMATURE'
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        self.layout.prop(self, 'remove_if_zero_weight')
    
    def execute(self, context):
        for armature in context.selected_objects:
            isolate(context, armature)
            previous_mode = armature.mode
            children = armature.children
            children = filter(
                lambda a: a.type == 'MESH',
                children
            )
            # if child has an armature modifier targeting the armature, or parented to the armature using the "ARMATURE" parent type
            children = set(filter(
                lambda obj: next(filter(lambda modifier: (modifier.type == 'ARMATURE') and modifier.object, obj.modifiers), null).object == armature or
                ((obj.parent == armature) and (obj.parent_type == 'ARMATURE')),
                children
            ))

            if not children:
                self.report({'ERROR'}, f'Armature "{armature.name}" has no valid children to reference!')
                return {'CANCELLED'}
            
            if not self.remove_if_zero_weight:
                used_bones = set()
                for child in children:
                    used_groups = get_used_groups(child.data)
                    used_groups = set(map(lambda a: child.vertex_groups[a].name, used_groups))
                    used_bones.update(used_groups)
                
                mode(mode='EDIT')
                edit_bones = armature.data.edit_bones
                for bone in edit_bones:
                    if not bone.name in used_bones:
                        edit_bones.remove(bone)

                mode(mode=previous_mode)

            else:
                used_bones = set()
                used_bone_weights = keep_highest_value()
                for child in children:
                    used_groups, used_weights = get_used_groups_and_weights(child.data)
                    used_groups = set(map(lambda a: child.vertex_groups[a].name, used_groups))
                    used_bones.update(used_groups)
                    used_weights = {child.vertex_groups[key].name : value for key, value in used_weights.items()}
                    used_bone_weights.update(used_weights)

                used_bone_weights = set([key for key, value in used_bone_weights.items() if value > 0.0 ])
                mode(mode='EDIT')
                edit_bones = armature.data.edit_bones
                for bone in edit_bones:
                    if not bone.name in used_bones:
                        edit_bones.remove(bone)
                        continue
                    if not bone.name in used_bone_weights:
                        edit_bones.remove(bone)
                mode(mode=previous_mode)

        return {'FINISHED'}

class RIGIALL_OT_remove_unused_bones_and_vgroups(Operator):
    bl_idname = 'rigiall.remove_unused_bones_and_vgroups'
    bl_label = 'Remove Unused Bones & Vertex Groups'
    bl_description = 'Removes bones unused by mesh(es), and the vertex groups associated with those bones'
    bl_options = {'UNDO'}

    remove_if_zero_weight: BoolProperty(name='Remove groups with zero vertex weight', description='Instead of just removing groups without any vertices assigned, enabling this will also remove groups if they are absolutely unused', default=False)

    @classmethod
    def poll(cls, context):
        return getattr(context.object, 'type', '') == 'ARMATURE'
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        self.layout.prop(self, 'remove_if_zero_weight')

    def execute(self, context):
        for armature in context.selected_objects:
            isolate(context, armature)
            previous_mode = armature.mode
            children = armature.children
            children = filter(
                lambda a: a.type == 'MESH',
                children
            )
            # if child has an armature modifier targeting the armature, or parented to the armature using the "ARMATURE" parent type
            children = set(filter(
                lambda obj: next(filter(lambda modifier: (modifier.type == 'ARMATURE') and modifier.object, obj.modifiers), null).object == armature or
                ((obj.parent == armature) and (obj.parent_type == 'ARMATURE')),
                children
            ))

            if not children:
                self.report({'ERROR'}, f'Armature "{armature.name}" has no valid children to reference!')
                return {'CANCELLED'}
            
            if not self.remove_if_zero_weight:
                used_bones = set()
                for child in children:
                    used_groups = get_used_groups(child.data)
                    used_groups = set(map(lambda a: child.vertex_groups[a].name, used_groups))
                    used_bones.update(used_groups)

                    for vgroup in child.vertex_groups:
                        if not vgroup.name in used_groups:
                            child.vertex_groups.remove(vgroup)
                
                mode(mode='EDIT')
                edit_bones = armature.data.edit_bones
                for bone in edit_bones:
                    if not bone.name in used_bones:
                        edit_bones.remove(bone)

                mode(mode=previous_mode)

            else:
                used_bones = set()
                used_bone_weights = keep_highest_value()
                for child in children:
                    used_groups, used_weights = get_used_groups_and_weights(child.data)
                    used_groups = set(map(lambda a: child.vertex_groups[a].name, used_groups))
                    used_bones.update(used_groups)
                    used_weights = {child.vertex_groups[key].name : value for key, value in used_weights.items()}
                    used_bone_weights.update(used_weights)

                    for vgroup in child.vertex_groups:
                        if not vgroup.name in used_groups:
                            child.vertex_groups.remove(vgroup)

                used_bone_weights = set([key for key, value in used_bone_weights.items() if value > 0.0 ])
                mode(mode='EDIT')
                edit_bones = armature.data.edit_bones
                for bone in edit_bones:
                    if not bone.name in used_bones:
                        edit_bones.remove(bone)
                        continue
                    if not bone.name in used_bone_weights:
                        edit_bones.remove(bone)
                mode(mode=previous_mode)

        return {'FINISHED'}

classes = [
    rigiall_ot_tweakmesh,
    rigiall_ot_remove_def_prefix,
    rigiall_ot_deduplicate_boneshapes,
    RIGIALL_OT_remove_unused_vgroups,
    RIGIALL_OT_remove_unused_bones,
    RIGIALL_OT_remove_unused_bones_and_vgroups
]

r, ur = bpy.utils.register_classes_factory(classes)

def register():
    r()
def unregister():
    ur()