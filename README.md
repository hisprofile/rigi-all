# Rigi-All
![banner_1080](https://github.com/user-attachments/assets/2197bc45-6e27-4901-a246-387728a970a0)

## Introduction
Rigging tool for Blender. Speeds up limb generation for existing rigs, leaving as little to do as possible for the user.  

This add-on is intended for humanoid rigs. E.g., two arms and two legs. However, it has a tool for making generic chains, where you can set the limb type before making the chain.

Make sure the Rigify add-on is enabled!
## Before You Try
There are things to know about how the add-on works. Please read this to give yourself a head start on the add-on!

### Placement
Everything is placed in a side-panel in the 3D viewport. The default category for this panel is "Rigi-All", but the panel can be recategorized.

### Initializing a Rig
To use Rigi-All on a rig, you must use its "Initialize" feature. It will create bone collections that future limbs will be placed in, as well as assign a post-generation script to clean up the final rig.

### Automatic Symmetry Feature
The limb generation tools can make two Rigify limbs from one or two selected chains, acting as a shortcut for the user. However, you are required to set the "Symmetry Mode" to what best suits the rig. Settings this correctly allows Rigi-All to correctly sort the bones. If the *Right* side of the rig is on the *negative side of the X axis*, you must set the Symmetry Mode to `-X`. This appears to be the default and safest option to use. Set the Symmetry Mode to whatever suits your rig. If you feel you need to make corrections, don't forget to apply rotation.

If you do not wish to use the Automatic Symmetry feature, simply turn it off in the Rigi-All panel, and use the left/right limb generation tools.

### Fix Symmetry Name Feature
This feature attempts to fix bone names to make them compatible with Blender's symmetry posing. Please set this up if required before generating limbs.

For example, a pair of bones named "upper_l_arm" and "upper_r_arm" will *not* be compatible with symmetry posing. Therefore, setting the `Left Symmetry Keyword` to `_l_` and `Right Symmetry Keyword` to `_r_` will format the bones to be named "upper\_arm.L" and "upper\_arm.R" respectively.

Symmetry posing is supported if a bone starts or ends with `l/r`, `L/R`, and `left/right`, followed or preceded with a period, underscore, or space. If your bones do not follow this naming scheme, please correct this with the "Fix Symmetry Name" tool.

## Rigging Tools
### Make Arms
- Requires 3 selected bones per chain

Creates a Rigify Arm out of the selected chain of bones.

### Make Fingers
- Requires at least 2 bones per chain. Select however many chains as you'd like.
- Primary Rotation Axis (Parameter)
  - Automatic
  - -/+X manual (+X default)
  - -/+Y manual
  - -/+Z manual
- IK Fingers (Parameter, True or False)

Creates Rigiy Fingers out of multiple selected chains.

### Make Legs
- Requires 4 selected bones per chain

Creates a Rigify Leg out of the selected chain of bones.

For simple legs that only consist of three bones with no toe bone, simply extrude a bone to act as a toe. 

### Make Spine
- Requires a chain of at least 3 selected bones.

Creates a Rigify Spine out of the selected chain of bones. By default, the pivot position is set at its lowest.

### Make Neck/Head
- Requires a chain of at least 2 selected bones.

Creates a Rigify Super_Head out of the selected chain of bones.

### Make Shoulders
- Requires 1 selected bone. No chain.

Creates a Rigify Shoulder out of the selected bone.

### Make Generic Chain
- No limit on selection
- Rigify Type (Parameter)
  - Choose any Rigify type to apply on the selected chains.

Automatically connects the selected chains of bones, and applies a Rigify Type if the parameter is set.

### Make Extras (Automatic)
- Widget Shape (Parameter)

This should be done last. It will mark any bone that was not a part of any limb generation as an Extra bone. These bones will carry over into the generated Rigify Rig.

### Make Extras (Only Selected)
- Widget Shape (Parameter)

Marks the selected bones as Extra bones. These bones will carry over into the generated Rigify Rig.

### Bone Rolling
Rolls any selected bone by -90° or 90°, or sets the roll to 0°

### Merge Armature
This should be done **absolutely** last!
- Original Rig (Parameter)
  - The original, unmodified rig
- Target Rig (Parameter)
  - The meta-rig used by Rigi-All

Overlays the original rig onto the meta-rig to preserve the original bone rotations without compromising on a Rigify Rig.

If you are familiar with the TF2-Trifecta, this is what allows cosmetics to seamlessly attach to the rigs. The Rigify Rigs have the original bones hidden, which are an exact match for the cosmetics, allowing them to attach.

## Clean Up Tools (Post Rig Generation)
### Add "DEF-" to Vertex Groups
- Not required on a merged armature

By default, the mesh will not follow the generated Rigify Rig due to having mismatched vertex group and bone names. 

Therefore, using this on all selected mesh objects will prepend "DEF-" to the required vertex groups, aligning the vertex groups with the armature.

### Remove "DEF-" from Bone Names
- Not required on a merged armature

By default, the mesh will not follow the generated Rigify Rig due to having mismatched vertex group and bone names.

Therefore, using this on the Rigify Rig will remove the "DEF-" prefix on the required bones, aligning the bones to the vertex groups. While it works, this option is *extremely* destructive to the rig and is not recommended. Use the former tool if possible.

### De-Duplicate Boneshapes
- De-duplicate Type (Parameter)
  - Only Clean Up Armature (default)
  - Clean Up ALL Shapes in Project

Every bone on a Rigify Rig has a unique bone shape object. While they are visually similar to other objects, they are indeed their own. This tool de-duplicates these bone shapes, so those that are visually similar are then made the same object.
