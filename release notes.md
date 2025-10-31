# Rigi-All 1.5
Rigi-All has gone through massive changes to further speed-up the process to transform a standard rig to a Rigify rig. Over-all, there is less for the user to do, yet more is done with each action taken.

## New Symmetry Operators
Instead of manually selecting left and right arms/legs/fingers, Rigi-All now automatically detects what side a limb is on.  
- The user must set the symmetry mode, specifying which side of which axis the limbs are on. By default, -X is selected, meaning the right side of the rig is on the negative side of the X axis.   

For example, to generate arms, you may either select both arm chains or just one. Either way, both will be transformed into a Rigify arm chain with one click. This extends to legs, fingers, and generic chains.

## Rig Generation & Clean-up Tools
### Rig Finalizing
Rigi-All now takes advantage of the "Rigify Finalize Script" feature to automatically apply finishing touches on a Rigify rig.

When generating a Rigify rig, it...
- Automatically moves all meshes from the old armature to the new Rigify rig
- Automatically re-parents extra bones from ORG- bones to DEF- bones
- Automatically fixes merged armatures

### Mesh Compatibility
To make meshes compatible with the new Rigify rig, which by default do not work unless the Rigify rig is a merged armature, the user has two options:
- **Add "DEF-" to Vertex Groups**
  - Prepends "DEF-" to vertex groups to allow the mesh to follow the DEFORM bones of the Rigify rig
- **Remove "DEF-" from Bone Names**
  - Removes the "DEF-" prefix for bones to maintain vertex group names. This is not recommended. Despite drivers being re-adjusted for this name change, it disrupts the overall naming scheme of the rig. If your goal is to maintain vertex group name, go ahead.

### De-duplicate Bone Shapes
The user now has the option to minimize the total count of bone shapes, either per-armature or for the whole .blend file.  

Despite bone shapes existing with visually the same shape, they are in fact separate instances. This corrects that.

## General Changes
- Simplified "Fix Symmetry Name" by designating two fields for left and right foreign symmetry keywords.
- Added a feature to mark selected bones as Extra
- Better explains the "Merge Armature" feature, and no longer relies on bone markings.
- Moved bone markings from custom properties to an API defined property
- Users may now re-categorize Rigi-All into a different place within the Viewport