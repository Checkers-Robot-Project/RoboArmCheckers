#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class EnterToPrintJoints(Node):
    def __init__(self):
        super().__init__("enter_to_print_joints")

        self.get_logger().info("Press Enter")

        self.subscription = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_callback,
            10
        )

        self.latest_msg = None

    def joint_callback(self, msg):
        self.latest_msg = msg

    def wait_and_print(self):
        while True:
            input()  

            if self.latest_msg is None:
                print("No joint data received yet...")
                continue

            order = ["joint1", "joint2", "joint3", "joint4",
                     "gripper_left_joint", "gripper_right_joint"]

            values = {name: pos for name, pos in zip(self.latest_msg.name,
                                                     self.latest_msg.position)}

            print(",".join(order))
            print(",".join(f"{values[j]:.4f}" for j in order))


def main():
    rclpy.init()
    node = EnterToPrintJoints()

    try:
        from threading import Thread
        spin_thread = Thread(target=rclpy.spin, args=(node,), daemon=True)
        spin_thread.start()

        node.wait_and_print()

    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
