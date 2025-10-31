import bpy

def isolate(context: bpy.types.Context, object):
    [obj.select_set(False) for obj in bpy.data.objects]
    object.select_set(True)
    context.view_layer.objects.active = object

mode = bpy.ops.object.mode_set
old_obj = bpy.context.object
obj = bpy.context.object.data.rigify_target_rig
isolate(bpy.context, obj)
data = obj.data
extra_bones = data.collections['Extras'].bones
overlaying_bone_names = [bone.name for bone in getattr(data.collections.get('overlaying'), 'bones', [])]
extra_bone_names = [bone.name for bone in extra_bones]

mode(mode='EDIT')
edits = data.edit_bones

if overlaying_bone_names:
    for bone in overlaying_bone_names:
        bone = edits[bone]
        bone.use_deform = True
        par_ebone = getattr(bone.parent, 'name', '')
        if not par_ebone.startswith('ORG-'): continue
        new_par_ebone = 'DEF-' + par_ebone.lstrip('ORG-')
        new_par_ebone = edits.get(new_par_ebone)
        if not new_par_ebone: continue
        bone.parent = new_par_ebone

    for bone in extra_bone_names:
        bone = edits[bone]
        par_ebone = getattr(bone.parent, 'name', '')
        if not par_ebone.startswith('ORG-'): continue
        new_par_ebone = 'DEF-' + par_ebone.lstrip('ORG-')
        new_par_ebone = edits.get(new_par_ebone)
        if not new_par_ebone: continue
        bone.parent = new_par_ebone
else:
    for bone in extra_bone_names:
        bone = edits[bone]
        bone.use_deform = True
        par_ebone = getattr(bone.parent, 'name', '')
        if not par_ebone.startswith('ORG-'): continue
        new_par_ebone = 'DEF-' + par_ebone.lstrip('ORG-')
        new_par_ebone = edits.get(new_par_ebone)
        if not new_par_ebone: continue
        bone.parent = new_par_ebone

for bone in extra_bone_names:
    bone = edits[bone]
    bone.name = 'DEF-' + bone.name

mode(mode='OBJECT')

for child in list(old_obj.children):
    child.parent = obj
    for arm in child.modifiers:
        if arm.type != 'ARMATURE': continue
        if arm.object == old_obj:
            arm.object = obj