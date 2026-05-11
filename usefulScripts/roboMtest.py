# Hardcoded movement script for original testing, moves pieces from a1-a3-a5


import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import GripperCommand
from board_poses import *


closed = -0.010
open = -0.0042

default = [-0.0031, -1.6904, 0.1381, 1.6191]
top     = [-0.0445, -0.2608, 0.0783, 1.6851]


class MoverNode(Node):
    def __init__(self):
        super().__init__("mover")

        self.get_logger().info("Mover node started.")

        self.arm_pub = self.create_publisher(
            JointTrajectory,
            "/arm_controller/joint_trajectory",
            10
        )

        self.gripper_client = ActionClient(
            self,
            GripperCommand,
            "/gripper_controller/gripper_cmd"
        )

        self.steps = [
            lambda: self.move_arm(default),

            *self.pick(a1_hover, a1),

            *self.place(a3_hover, a3),

            *self.pick(a3_hover, a3),

            *self.place(a5_hover, a5),
            lambda: self.move_arm(default),

            self.finish
        ]

        self.step = 0
        self.timer = self.create_timer(2.0, self.run_sequence)

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
