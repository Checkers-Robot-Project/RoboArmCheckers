import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import GripperCommand
from board_poses import *


# Gripper positions
closed = -0.010
open = -0.0042

# Main poses
default = [-0.0031, -1.6904, 0.1381, 1.6191]
top     = [-0.0445, -0.2608, 0.0783, 1.6851]


class MoverNode(Node):
    def __init__(self):
        super().__init__("mover")

        self.get_logger().info("Mover node started.")

        # Arm trajectory publisher
        self.arm_pub = self.create_publisher(
            JointTrajectory,
            "/arm_controller/joint_trajectory",
            10
        )

        # Gripper action client
        self.gripper_client = ActionClient(
            self,
            GripperCommand,
            "/gripper_controller/gripper_cmd"
        )

        # Build full sequence using helpers
        self.steps = [
            lambda: self.move_arm(default),

            # -------------------------
            # ROW A: A1 → A3 → A5
            # -------------------------
            *self.pick(a1_hover, a1),

            *self.place(a3_hover, a3),

            *self.pick(a3_hover, a3),

            *self.place(a5_hover, a5),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW B: B2 → B4 → B6
            # -------------------------
            *self.pick(b2_hover, b2),

            *self.place(b4_hover, b4),

            *self.pick(b4_hover, b4),

            *self.place(b6_hover, b6),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW C: C1 → C3 → C5
            # -------------------------
            *self.pick(c1_hover, c1),

            *self.place(c3_hover, c3),

            *self.pick(c3_hover, c3),

            *self.place(c5_hover, c5),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW D: D2 → D4 → D6
            # -------------------------
            *self.pick(d2_hover, d2),

            *self.place(d4_hover, d4),

            *self.pick(d4_hover, d4),

            *self.place(d6_hover, d6),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW E: E1 → E3 → E5
            # -------------------------
            *self.pick(e1_hover, e1),

            *self.place(e3_hover, e3),

            *self.pick(e3_hover, e3),

            *self.place(e5_hover, e5),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW F: F2 → F4 → F6
            # -------------------------
            *self.pick(f2_hover, f2),

            *self.place(f4_hover, f4),

            *self.pick(f4_hover, f4),

            *self.place(f6_hover, f6),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW G: G1 → G3 → G5
            # -------------------------
            *self.pick(g1_hover, g1),

            *self.place(g3_hover, g3),

            *self.pick(g3_hover, g3),

            *self.place(g5_hover, g5),
            lambda: self.move_arm(default),

            # -------------------------
            # ROW H: H2 → H4 → H6
            # -------------------------
            *self.pick(h2_hover, h2),

            *self.place(h4_hover, h4),

            *self.pick(h4_hover, h4),

            *self.place(h6_hover, h6),
            lambda: self.move_arm(default),

            self.finish
        ]

        self.step = 0
        self.timer = self.create_timer(2.0, self.run_sequence)

    # -----------------------------
    # High-level motion helpers
    # -----------------------------
    def pick(self, hover, down):
        return [
            lambda: self.move_gripper(open),
            lambda: self.move_arm(hover),
            lambda: self.move_arm(down),
            lambda: self.move_gripper(closed),
            lambda: self.move_arm(hover),
        ]

    def place(self, hover, down):
        return [
            lambda: self.move_arm(hover),
            lambda: self.move_arm(down),
            lambda: self.move_gripper(open),
            lambda: self.move_arm(hover),
        ]

    # -----------------------------
    # Low-level motion commands
    # -----------------------------
    def run_sequence(self):
        if self.step < len(self.steps):
            self.get_logger().info(f"Running step {self.step}")
            self.steps[self.step]()
            self.step += 1

    def move_arm(self, positions):
        msg = JointTrajectory()
        msg.joint_names = ["joint1", "joint2", "joint3", "joint4"]

        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start.sec = 2

        msg.points.append(point)
        self.arm_pub.publish(msg)

    def move_gripper(self, opening):
        goal = GripperCommand.Goal()
        goal.command.position = opening
        goal.command.max_effort = 1.0

        self.get_logger().info(f"Gripper → {opening}")

        self.gripper_client.wait_for_server()
        self.gripper_client.send_goal_async(goal)

    def finish(self):
        self.get_logger().info("Sequence complete.")
        self.timer.cancel()


def main():
    rclpy.init()
    node = MoverNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
