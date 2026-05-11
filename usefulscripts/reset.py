#!/usr/bin/env python3
import pyrealsense2 as rs

def reset_camera():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    profile = pipeline.start(config)

    device = profile.get_device()
    sensors = device.query_sensors()

    print("Found sensors:")
    for sensor in sensors:
        print(" -", sensor.get_info(rs.camera_info.name))

    for sensor in sensors:
        try:
            sensor.set_option(rs.option.reset_to_default, 1)
            print(f" Reset {sensor.get_info(rs.camera_info.name)} to defaults")
        except Exception as e:
            print(f" Could not reset {sensor.get_info(rs.camera_info.name)}: {e}")

    pipeline.stop()
    print("Camera reset complete.")

if __name__ == "__main__":
    reset_camera()
