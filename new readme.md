# Rigi-All
## Introduction
Rigging tool for Blender. Speeds up limb generation for existing rigs, leaving as little to do as possible for the user.

## Workflow Example
### Preparing the Rig
First and foremost, ensure the Rigify add-on is enabled in the preferences.  
<img width="45%" alt="image" src="https://github.com/user-attachments/assets/d429f426-5def-4ad9-a53b-2f1f381aa078"/>

We are now ready to use Rigi-All. Start by initializing the rig. This pre-emptively creates bone collections to place future limbs into, and attaches a finalization script for when the rig is generated.  
<img width="55%" alt="image" src="https://github.com/user-attachments/assets/b3af8fbe-650f-4b02-a79d-c70b698ed62e" />  
<img width="55%" alt="image" src="https://github.com/user-attachments/assets/1f9dda7f-452d-460e-9c1a-f936e91353e1" />


### Generating Limbs
Let us now enter Pose Mode to begin generating Rigify Limbs. We will start with the arms. To make this as fast as possible, we will enable "Automatic Symmetry," allowing us to select one arm chain and generate Rigify limbs for both!

> [!IMPORTANT]
> Rigi-All needs to know what side of the armature is on which side of which axis. In this case, the right side of the rig is on -X, therefore the `Symmetry Mode` is -X. Ideally, this is how all rigs should be. If you need to make adjustments, remember to apply rotations.  
  
> [!IMPORTANT]
> Use `Fix Symmetry Name` if your bone names are not compatible with Blender's symmetry posing.  
> For example, bones `upper_l_arm` and `upper_r_arm` will not be recognized for symmetry posing. Therefore, enable `Fix Symmetry Name`, and set the left and right symmetry keywords to `_l_` and `_r_` respectively. When generating bone chains, these bones will be renamed to `upper_arm.L` and `upper_arm.R`. Use `Fix Symmetry` if your situation is similar, and set the symmetry keywords to whatever suits your situation.

After selecting one arm chain, and using `Make Arms`, we get...  
<img width="45%" alt="image" src="https://github.com/user-attachments/assets/0e80e1e9-9682-4b11-b433-5fa9d8fda43e" /> <img width="45%" alt="image" src="https://github.com/user-attachments/assets/e11f2c44-ac5d-48d5-a0c8-e36ee8b6e2b4" />  

Two generated arms! Let's do the same for the fingers and legs. When prompted to set the primary rotation axis, I recommend the (+)X Manual axis.  

Fingers  
<img width="45%" alt="image" src="https://github.com/user-attachments/assets/e6828be2-540c-4a18-a866-352e0b2d9ed9" /> <img width="45%" alt="image" src="https://github.com/user-attachments/assets/6ab4d295-cefe-4728-b091-5ca22c0a61fa" />  

Legs  
<img width="45%" alt="image" src="https://github.com/user-attachments/assets/75ce6fbd-615f-4f39-9e89-21173173d8a4" /> <img width="45%" alt="image" src="https://github.com/user-attachments/assets/857b3c6a-8427-4a20-a33f-0e67fe7eba82" />



When adjusting for bone roll manually, I recommend selecting a chain of bones in Edit Mode, pressing Ctrl+N, then selecting Local +Z Tangent. Then, select the first bone in the chain, then the second, then choose Active Bone.
