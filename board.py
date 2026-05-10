import cv2
import numpy as np
import pyrealsense2 as rs

from raven_checkers.engine_bridge import get_ai_move_from_camera
from raven_checkers.util.globalconst import BLACK

OUT_SIZE = 1000
GRID_THICKNESS = 2

locked_H = None
locked_cells = None

# hardcoded fudge margins inside the rectified image
MARGIN_X = 120   # tweak this
MARGIN_Y = 120   # and this


# ---------------------------
# BOARD DETECTION (CHESSBOARD + SCUFFED MARGINS)
# ---------------------------

def detect_board(frame):
    global locked_H, locked_cells

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 8x8 squares → 7x7 inner corners
    pattern_size = (7, 7)
    found, corners = cv2.findChessboardCorners(gray, pattern_size)

    if not found:
        return False

    # Subpixel refinement
    corners = cv2.cornerSubPix(
        gray,
        corners,
        (11, 11),
        (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
    )

    # reshape to 7x7 grid
    corners = corners.reshape(7, 7, 2)

    # use inner grid corners directly (no fancy border math)
    tl = corners[0, 0]
    tr = corners[0, 6]
    br = corners[6, 6]
    bl = corners[6, 0]

    src = np.array([tl, tr, br, bl], dtype=np.float32)

    # we map the inner 7x7 area into an inner rectangle with margins
    dst = np.array([
        [MARGIN_X, MARGIN_Y],
        [OUT_SIZE - 1 - MARGIN_X, MARGIN_Y],
        [OUT_SIZE - 1 - MARGIN_X, OUT_SIZE - 1 - MARGIN_Y],
        [MARGIN_X, OUT_SIZE - 1 - MARGIN_Y]
    ], dtype=np.float32)

    locked_H = cv2.getPerspectiveTransform(src, dst)

    # Build 8×8 grid cell map over the full OUT_SIZE
    step_x_out = OUT_SIZE / 8
    step_y_out = OUT_SIZE / 8
    files = "ABCDEFGH"

    locked_cells = {
        f"{files[c]}{8 - r}": (
            int(c * step_x_out), int(r * step_y_out),
            int((c + 1) * step_x_out), int((r + 1) * step_y_out)
        )
        for r in range(8) for c in range(8)
    }

    return True


# ---------------------------
# PIECE DETECTOR (HSV)
# ---------------------------

class PieceDetector:
    def __init__(self, cell_thresh=0.06, roi_frac=0.5):
        self.cell_thresh = cell_thresh
        self.roi_frac = roi_frac

        self.red_lower1 = np.array([0, 100, 60])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 100, 60])
        self.red_upper2 = np.array([180, 255, 255])

        self.gold_lower = np.array([10, 70, 90])
        self.gold_upper = np.array([35, 255, 255])

        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    def detect(self, warped):
        h, w = warped.shape[:2]
        board_state = np.zeros((8, 8), dtype=int)
        debug_img = warped.copy()

        step_x = w / 8
        step_y = h / 8

        hsv_whole = cv2.cvtColor(
            cv2.GaussianBlur(warped, (5, 5), 0),
            cv2.COLOR_BGR2HSV
        )

        mask_red_whole = cv2.bitwise_or(
            cv2.inRange(hsv_whole, self.red_lower1, self.red_upper1),
            cv2.inRange(hsv_whole, self.red_lower2, self.red_upper2)
        )
        mask_gold_whole = cv2.inRange(hsv_whole, self.gold_lower, self.gold_upper)

        cv2.imshow("Mask Red", mask_red_whole)
        cv2.imshow("Mask Gold", mask_gold_whole)

        for r in range(8):
            for c in range(8):
                cx = int((c + 0.5) * step_x)
                cy = int((r + 0.5) * step_y)

                side = int(min(step_x, step_y) * self.roi_frac)
                half = max(3, side // 2)

                x0, y0 = max(0, cx - half), max(0, cy - half)
                x1, y1 = min(w, cx + half), min(h, cy + half)

                roi = warped[y0:y1, x0:x1]
                if roi.size == 0:
                    continue

                hsv = cv2.cvtColor(
                    cv2.GaussianBlur(roi, (5, 5), 0),
                    cv2.COLOR_BGR2HSV
                )

                mask_red = cv2.bitwise_or(
                    cv2.inRange(hsv, self.red_lower1, self.red_upper1),
                    cv2.inRange(hsv, self.red_lower2, self.red_upper2)
                )
                mask_gold = cv2.inRange(hsv, self.gold_lower, self.gold_upper)

                mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, self.kernel)
                mask_gold = cv2.morphologyEx(mask_gold, cv2.MORPH_OPEN, self.kernel)

                frac_red = (mask_red > 0).sum() / mask_red.size
                frac_gold = (mask_gold > 0).sum() / mask_gold.size

                if frac_red >= self.cell_thresh and frac_red > frac_gold:
                    board_state[r, c] = 1
                    cv2.circle(debug_img, (cx, cy), 6, (0, 0, 255), -1)

                elif frac_gold >= self.cell_thresh and frac_gold > frac_red:
                    board_state[r, c] = 2
                    cv2.circle(debug_img, (cx, cy), 6, (0, 215, 255), -1)

        return board_state, debug_img


# ---------------------------
# REALSENSE INIT
# ---------------------------

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

detector = PieceDetector()


# ---------------------------
# MAIN LOOP
# ---------------------------

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        color = np.asanyarray(color_frame.get_data())
        display = color.copy()

        if locked_H is None:
            if detect_board(color):
                cv2.putText(
                    display,
                    "Board locked!",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )
            else:
                cv2.putText(
                    display,
                    "Detecting board...",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )

        else:
            rectified = cv2.warpPerspective(color, locked_H, (OUT_SIZE, OUT_SIZE))
            cv2.imshow("Rectified Board", rectified)

            board_state, debug_img = detector.detect(rectified)

            try:
                ai_move = get_ai_move_from_camera(board_state, BLACK)
                print("AI move:", ai_move)
            except Exception as e:
                print("AI error:", e)

            grid_view = debug_img.copy()
            step_x_out = OUT_SIZE / 8
            step_y_out = OUT_SIZE / 8

            for i in range(1, 8):
                cv2.line(
                    grid_view,
                    (int(i * step_x_out), 0),
                    (int(i * step_x_out), OUT_SIZE),
                    (0, 255, 0),
                    GRID_THICKNESS,
                )
                cv2.line(
                    grid_view,
                    (0, int(i * step_y_out)),
                    (OUT_SIZE, int(i * step_y_out)),
                    (0, 255, 0),
                    GRID_THICKNESS,
                )

            cv2.imshow("Locked Board View + Pieces", grid_view)

            print("Board state:")
            for r in range(8):
                print(" ".join(str(board_state[r, c]) for c in range(8)))
            print("-" * 40)

        cv2.imshow("Original Camera Feed", display)

        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
