import asyncio
import json
import sys
import time

import cv2
import numpy as np
import pyrealsense2 as rs
import websockets

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.append("/home/dara/fyp/Coding")

from raven_checkers.engine_bridge import get_ai_move_from_camera
from raven_checkers.util.globalconst import BLACK, WHITE


OUT_SIZE = 1000
MARGIN_X = 125
MARGIN_Y = 125

ROBOT_PLAYER = BLACK

locked_H = None
pipeline = None
camera_paused = False

game_board = None


class RobotBridge(Node):
    def __init__(self):
        super().__init__("robot_bridge")
        self.pub = self.create_publisher(String, "/robot_move", 10)

        self.create_subscription(
            String,
            "/camera_control",
            self.camera_control_callback,
            10
        )

    def camera_control_callback(self, msg: String):
        global camera_paused
        camera_paused = (msg.data == "PAUSE")


def start_camera():
    global pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)


def stop_camera():
    global pipeline
    try:
        if pipeline:
            pipeline.stop()
    except Exception:
        pass
    cv2.destroyAllWindows()


def reset_camera():
    global locked_H
    locked_H = None
    stop_camera()
    start_camera()


def detect_board(frame):
    global locked_H

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, (7, 7))
    if not found:
        return False

    corners = cv2.cornerSubPix(
        gray,
        corners,
        (11, 11),
        (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1),
    )

    corners = corners.reshape(7, 7, 2)

    tl, tr, br, bl = corners[0, 0], corners[0, 6], corners[6, 6], corners[6, 0]

    src = np.array([tl, tr, br, bl], dtype=np.float32)
    dst = np.array([
        [MARGIN_X, MARGIN_Y],
        [OUT_SIZE - MARGIN_X, MARGIN_Y],
        [OUT_SIZE - MARGIN_X, OUT_SIZE - MARGIN_Y],
        [MARGIN_X, OUT_SIZE - MARGIN_Y],
    ], dtype=np.float32)

    locked_H = cv2.getPerspectiveTransform(src, dst)
    return True


class PieceDetector:
    def __init__(self):
        self.red_lower1 = np.array([0, 80, 60])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([150, 100, 60])
        self.red_upper2 = np.array([180, 255, 255])

        self.gold_lower = np.array([10, 70, 90])
        self.gold_upper = np.array([35, 255, 255])

        self.blue_lower = np.array([95, 80, 80])
        self.blue_upper = np.array([135, 255, 255])

        self.green_lower = np.array([40, 80, 50])
        self.green_upper = np.array([90, 255, 255])

    def detect(self, warped):
        board = np.zeros((8, 8), dtype=int)

        h, w = warped.shape[:2]
        step_x = w / 8
        step_y = h / 8

        for r in range(8):
            for c in range(8):
                cx = int((c + 0.5) * step_x)
                cy = int((r + 0.5) * step_y)

                roi = warped[cy - 25:cy + 25, cx - 25:cx + 25]
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

                if hsv.size == 0:
                    continue

                mean_s = hsv[:, :, 1].mean()
                mean_v = hsv[:, :, 2].mean()

                if mean_v < 60 or mean_s < 50:
                    continue

                red = cv2.bitwise_or(
                    cv2.inRange(hsv, self.red_lower1, self.red_upper1),
                    cv2.inRange(hsv, self.red_lower2, self.red_upper2),
                )

                gold = cv2.inRange(hsv, self.gold_lower, self.gold_upper)
                blue = cv2.inRange(hsv, self.blue_lower, self.blue_upper)
                green = cv2.inRange(hsv, self.green_lower, self.green_upper)

                if (blue > 0).mean() > 0.06:
                    board[r, c] = 3
                elif (green > 0).mean() > 0.06:
                    board[r, c] = 4
                elif (red > 0).mean() > 0.06:
                    board[r, c] = 1
                elif (gold > 0).mean() > 0.06:
                    board[r, c] = 2

        return board


detector = PieceDetector()

start_camera()

async def send_board(websocket):
    global pipeline, locked_H, camera_paused, game_board

    try:
        while True:

            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=0.001)

                if msg == "RESET_CAMERA":
                    reset_camera()

                elif msg.startswith("ROBOT_MOVE_REQUEST|"): 

                    parts = msg.split("|", 3)

                    if len(parts) == 4:
                        _, mode, player, board_json = parts
                    elif len(parts) == 3:
                        _, mode, board_json = parts
                        player = "black"  
                    else:
                        print("⚠ Invalid ROBOT_MOVE_REQUEST:", msg)
                        
                        continue
                    print("ROBOT_MOVE_REQUEST:", repr(mode), repr(player))
                    board_json = board_json.strip()

                    if not board_json or board_json in ("undefined", "null", "None"):
                        print("⚠ Ignoring empty/invalid board_json:", repr(board_json))
                        continue

                    try:
                        board = np.array(json.loads(board_json))
                    except json.JSONDecodeError:
                        print("⚠ JSON decode failed for board_json:", repr(board_json))
                        continue

                
                    if mode == "self":
                        engine_player = BLACK if player == "red" else WHITE
                        print("ENGINE PLAYER:", "BLACK" if engine_player == BLACK else "WHITE")
                        print("BOARD UNIQUE VALUES:", np.unique(board))
                        ai_result = get_ai_move_from_camera(board, engine_player)
                        print("ENGINE MOVE:", ai_result["move"], "CAPTURES:", ai_result["captured"])
                        print("FULL BOARD LAYOUT:")
                        for row in board:
                            print(" ".join(str(x) for x in row))
                        print("----")
                    else:
                        engine_player = BLACK
                        print("ENGINE PLAYER: BLACK (human mode)")
                        print("BOARD UNIQUE VALUES:", np.unique(board))
                        ai_result = get_ai_move_from_camera(board, BLACK)
                        print("ENGINE MOVE:", ai_result["move"], "CAPTURES:", ai_result["captured"])
                        for row in board:
                            print(" ".join(str(x) for x in row))
                        print("----")



                    move = ai_result["move"]
                    caps = ai_result["captured"]

                    await websocket.send(json.dumps({
                        "type": "AI_MOVE",
                        "move": move,
                        "captured": caps
                    }))

                    if move:
                        ros_msg = ",".join(move)
                        if caps:
                            ros_msg += "|" + ",".join(caps)
                        bridge.pub.publish(String(data=ros_msg))

            except asyncio.TimeoutError:
                pass
            except websockets.exceptions.ConnectionClosed:
                break

            if camera_paused:
                await asyncio.sleep(0.03)
                continue

            frames = pipeline.wait_for_frames()
            frame = frames.get_color_frame()
            if not frame:
                continue

            color = np.asanyarray(frame.get_data())

            if locked_H is None:
                detect_board(color)
                await asyncio.sleep(0.05)
                continue

            warped = cv2.warpPerspective(color, locked_H, (OUT_SIZE, OUT_SIZE))

            board = detector.detect(warped)
            rotated = np.rot90(board, 3)

            game_board = rotated.copy()

            await websocket.send(json.dumps(rotated.tolist()))
            await asyncio.sleep(0.03)

    except websockets.exceptions.ConnectionClosed:
        pass


async def main():
    async with websockets.serve(send_board, "localhost", 6789):
        await asyncio.Future()


try:
    rclpy.init()
    bridge = RobotBridge()

    import threading
    threading.Thread(target=rclpy.spin, args=(bridge,), daemon=True).start()

    asyncio.run(main())

finally:
    stop_camera()
    bridge.destroy_node()
    rclpy.shutdown()
