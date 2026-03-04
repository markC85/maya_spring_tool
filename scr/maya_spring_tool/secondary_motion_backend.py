import maya.cmds as cmds
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


def delete_anim_layer_by_name(target_name: str) -> bool:
    """
    Delete the animation layer with the specified name.
    If the layer is found, it will be set to 0 weight and then deleted.

    Args:
        target_name (str): The name of the animation layer to delete.

    Returns:
        bool: True if the layer was found and deleted, False otherwise.
    """
    # Get all animation layers
    anim_layers = cmds.ls(type="animLayer")

    if target_name not in anim_layers:
        LOG.info(f"We did not find the animation layer {target_name}")
        return False

    for layer in anim_layers:
        if layer == target_name:
            # Set the layer's weight/strength to 0
            cmds.animLayer(layer, edit=True, weight=0.0)
            # Delete the animation layer
            cmds.delete(layer)
            LOG.info(f"Deleted animation layer: {layer}")
            return True

def apply_secondary_motion_additive(
    joints: list = [],
    lag_frames: int = 2,
    spring_strength: float = 0.3,
    damping: float = 0.85,
    max_rotation_clamp: float = 45.0,
    layer_name: str = "Secondary_Motion_LYR",
) -> None:
    """
    Create a secondary motion simulation on an additive animation layer for a joint chain.
     - The first joint is the driver (root), and the rest are followers.
     - Each follower simulates spring dynamics based on the rotation of its parent joint with a lag.
     - The resulting motion is applied as an additive delta on a separate animation layer, preserving the original animation.

    If it looks too stiff:
    Lower damping

    If it jitters:
    Increase damping

    If it feels weak:
    Increase spring_strength

    If it explodes:
    Lower clamp or increase damping

     Args:
        joints (list): List of joint names in chain order (root → tip).
        lag_frames (int): Number of frames to lag the parent rotation sampling.
        spring_strength (float): Strength of the spring force (higher = stiffer).
        damping (float): Damping factor to reduce oscillation (0 < damping < 1).
        max_rotation_clamp (float): Maximum rotation change per frame to prevent instability.
        layer_name (str): Name of the additive animation layer to create/use.
    """
    if not joints or len(joints) < 2:
        LOG.error("Select at least 2 joints in chain order: root → tip")
        return None

    # set thef rame range for the simulation
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))

    # Split root and followers
    driver = joints[0]
    followers = joints[1:]

    # Create additive animation layer
    if not cmds.objExists(layer_name):
        layer = cmds.animLayer(layer_name, override=False)
    else:
        layer = layer_name

    # Add followers to the layer
    cmds.select(followers)
    cmds.animLayer(layer, edit=True, addSelectedObjects=True)

    # Cache base rotations for all followers per frame
    base_rot_cache = {j: {} for j in followers}
    for frame in range(start, end + 1):
        cmds.currentTime(frame)
        for j in followers:
            base_rot_cache[j][frame] = cmds.getAttr(j + ".rotate")[0]

    # Initialize simulation state
    sim_rot = {j: cmds.getAttr(j + ".rotate")[0] for j in joints}
    sim_vel = {j: [0.0, 0.0, 0.0] for j in joints}

    # Loop through frames
    for frame in range(start, end + 1):
        cmds.currentTime(frame)

        for i, child in enumerate(followers):
            parent = joints[i]  # previous joint

            # Sample parent rotation with lag
            sample_frame = max(start, frame - lag_frames)
            if parent == driver:
                # Root always sampled from actual animation
                cmds.currentTime(sample_frame)
                parent_rot = cmds.getAttr(parent + ".rotate")[0]
                cmds.currentTime(frame)
            else:
                # Followers use simulated rotation
                parent_rot = sim_rot[parent]

            current_rot = sim_rot[child]
            velocity = sim_vel[child]

            new_rot = [0.0, 0.0, 0.0]
            new_vel = [0.0, 0.0, 0.0]

            for axis in range(3):
                delta = parent_rot[axis] - current_rot[axis]

                # Spring force
                force = delta * spring_strength

                # Apply to velocity
                velocity[axis] += force

                # Damping
                velocity[axis] *= damping

                # Clamp velocity
                velocity[axis] = max(
                    -max_rotation_clamp, min(max_rotation_clamp, velocity[axis])
                )

                # Integrate velocity
                new_rot[axis] = current_rot[axis] + velocity[axis]
                new_vel[axis] = velocity[axis]

            sim_rot[child] = new_rot
            sim_vel[child] = new_vel

            # Compute additive delta vs cached base rotation
            base_rot = base_rot_cache[child][frame]
            delta_rot = [new_rot[axis] - base_rot[axis] for axis in range(3)]

            # Apply delta on additive animation layer
            cmds.setAttr(child + ".rotate", *delta_rot)
            cmds.setKeyframe(child, attribute="rotate", animLayer=layer)

    # Reset timeline to start
    cmds.currentTime(start)
    LOG.info(f"Secondary motion bake complete on additive layer: {layer_name}")


if __name__ == "__main__":
    apply_secondary_motion_additive(
        joints=cmds.ls(selection=True),
        lag_frames=2,
        spring_strength=0.80,
        damping=0.9,
        max_rotation_clamp=20,
        layer_name="secondaryMotion_LYR",
    )