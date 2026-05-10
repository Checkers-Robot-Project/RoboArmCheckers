import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import GripperCommand
import time

from roboMove.board_poses import *


class MoverNode(Node):
    def __init__(self):
        super().__init__("mover")
        self.get_logger().info("Mover node started.")

        # Track how many kings have been taken from the side
        self.red_kings_used = 0
        self.yellow_kings_used = 0

        self.camera_pub = self.create_publisher(String, "/camera_control", 10)
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

        self.create_subscription(
            String,
            "/robot_move",
            self.execute_robot_move,
            10
        )

        self.get_logger().info("Waiting for robot moves...")

        self.move_arm(default)
        self.move_gripper(open)

        time.sleep(2.2)
        self.camera_pub.publish(String(data="RESUME"))

    # -----------------------------
    # KING PLACEMENT
    # -----------------------------
    def place_king_piece(self, square, colour):
        hover_sq = globals().get(f"{square}_hover")
        down_sq = globals().get(square)

        if hover_sq is None or down_sq is None:
            self.get_logger().error(f"Missing board poses for {square}")
            return

        # Select king source
        if colour == "red":
            if self.red_kings_used == 0:
                king_hover = globals().get("red_king_1_hover")
                king_down = globals().get("red_king_1")
            else:
                king_hover = globals().get("red_king_2_hover")
                king_down = globals().get("red_king_2")
            self.red_kings_used += 1
        else:  # yellow
            if self.yellow_kings_used == 0:
                king_hover = globals().get("yellow_king_1_hover")
                king_down = globals().get("yellow_king_1")
            else:
                king_hover = globals().get("yellow_king_2_hover")
                king_down = globals().get("yellow_king_2")
            self.yellow_kings_used += 1

        if king_hover is None or king_down is None:
            self.get_logger().error(f"Missing king poses for {colour}")
            return

        # Move man off board
        self.pick(hover_sq, down_sq)
        self.place(out, out)

        # Pick king from side and place on square
        self.pick(king_hover, king_down)
        self.place(hover_sq, down_sq)



    # -----------------------------
    # EXECUTE MOVE (SAFE)
    # -----------------------------
    def execute_robot_move(self, msg):
        try:
            raw = msg.data.strip()
            if not raw:
                return

            # -------------------------------------------------
            # PROMOTION COMMAND: PLACE KING, THEN GO DEFAULT
            # -------------------------------------------------
            if raw.startswith("ROBOT_PROMOTE|"):
                _, square, colour = raw.split("|")
                self.get_logger().info(f"Promoting {colour} king at {square}")

                self.camera_pub.publish(String(data="PAUSE"))
                time.sleep(0.5)

                self.place_king_piece(square, colour)

                # AFTER king is placed, NOW go to default
                self.move_arm(default)
                time.sleep(2.2)

                self.camera_pub.publish(String(data="RESUME"))
                return

            # -------------------------------------------------
            # NORMAL MOVE
            # -------------------------------------------------
            if "|" in raw:
                move_part, caps_part = raw.split("|", 1)
                captured = caps_part.split(",") if caps_part else []
            else:
                move_part = raw
                captured = []

            if "," not in move_part:
                self.get_logger().error("Invalid move format")
                return

            start, end = move_part.split(",")

            self.camera_pub.publish(String(data="PAUSE"))
            time.sleep(0.5)

            hover_s = globals().get(f"{start}_hover")
            down_s  = globals().get(start)
            hover_e = globals().get(f"{end}_hover")
            down_e  = globals().get(end)

            if None in (hover_s, down_s, hover_e, down_e):
                self.get_logger().error("Missing pose")
                return

            # Move piece
            self.pick(hover_s, down_s)
            self.place(hover_e, down_e)

            # Captures
            if captured:
                for cap in captured:
                    hover_c = globals().get(f"{cap}_hover")
                    down_c = globals().get(cap)
                    if None in (hover_c, down_c):
                        self.get_logger().error(f"Missing capture pose for {cap}")
                        continue
                    self.pick(hover_c, down_c)
                    time.sleep(0.5)
                    self.place(out, out)

            # -------------------------------------------------
            # CHECK IF THIS MOVE ENDS ON PROMOTION ROW
            # -------------------------------------------------
            end_row = int(end[1])  # e.g. "E8" -> 8
            is_promotion_move = (end_row == 8 or end_row == 1)

            if is_promotion_move:
                # Man just reached last row: DON'T go to default yet.
                time.sleep(1.0)   # give camera time to settle
                self.camera_pub.publish(String(data="RESUME"))
                return

          
            self.move_arm(default)
            time.sleep(2)

            self.camera_pub.publish(String(data="RESUME"))

            return

        except Exception as e:
            self.get_logger().error(f"Move failed: {e}")




    # -----------------------------
    # PICK / PLACE
    # -----------------------------
    def pick(self, hover, down):
        self.move_arm(hover)
        time.sleep(2.2)

        self.move_arm(down)
        time.sleep(2.2)

        self.move_gripper(closed)
        time.sleep(1.0)

        self.move_arm(hover)
        time.sleep(2.2)

    def place(self, hover, down):
        self.move_arm(hover)
        time.sleep(2.2)

        self.move_arm(down)
        time.sleep(2.2)

        self.move_gripper(open)
        time.sleep(1.0)

        self.move_arm(hover)
        time.sleep(2.2)


    # -----------------------------
    # LOW-LEVEL
    # -----------------------------
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

        self.gripper_client.wait_for_server()
        self.gripper_client.send_goal_async(goal)


def main():
    rclpy.init()
    node = MoverNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
