#!/usr/bin/env python3

import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from time import sleep
from typing import Any
from urllib.parse import parse_qs, urlparse

import libcamera  # type: ignore
from picamera2 import Picamera2  # type: ignore

from decorators import timer

DEFAULT_SERVER_PORT: int = 8000
MIN_FOCAL_DISTANCE: int = 0
MAX_FOCAL_DISTANCE: int = 1023
DEFAULT_RESOLUTION: tuple[int, int] = (1920, 1080)
DEFAULT_EXPOSURE_TIME_US: int = 25_000
DEFAULT_FOCAL_DISTANCE: int = 0

print("Camera init...")
CAMERA = Picamera2()
CONFIG = CAMERA.create_preview_configuration({"size": DEFAULT_RESOLUTION})
CONFIG["transform"] = libcamera.Transform(hflip=0, vflip=0)
CAMERA.configure(CONFIG)
CAMERA.set_controls(
    {
        "ExposureTime": DEFAULT_EXPOSURE_TIME_US,  # microseconds
        "AnalogueGain": 1.0,  # gain (range 1.0 to 10.0)
        "Brightness": 0.0,  # brightness (range -1.0 to 1.0)
        "Contrast": 1.0,  # contrast (range 0.0 to 2.0)
        "Saturation": 1.0,  # saturation (range 0.0 to 2.0)
        "Sharpness": 2.0,  # sharpness (range 0.0 to 2.0)
        "ColourGains": [0.0, 0.0],  # Color balance (red, blue)
        "AwbEnable": True,  # Enable auto white balance
    }
)
CAMERA.start()


def get_camera_options(camera) -> None:
    print("camera options:")
    controls: dict[str, Any] = camera.camera_controls
    for control, value in controls.items():
        print(f"- {control}: {value}")


class RequestHandler(BaseHTTPRequestHandler):
    last_focal_distance: int = DEFAULT_FOCAL_DISTANCE
    last_resolution: tuple[int, int] = DEFAULT_RESOLUTION
    last_exposure_time_us: int = DEFAULT_EXPOSURE_TIME_US

    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            focal_distance = int(query_params.get("focal_distance", [0])[0])
            resolution = query_params.get("resolution", ["1920x1080"])[0]
            width, height = tuple(int(val) for val in resolution.split("x"))
            exposure_time_us = int(query_params.get("exposure_time_us", [100000])[0])
            print("query_params received:")
            for key, value in query_params.items():
                print(f"- {key}: {value[0]}")

            response_data = self.handle_request(
                focal_distance, exposure_time_us, width, height
            )
            self.send_response(200)
            self.send_header("Content-type", "image/jpeg")
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_error(500, str(e))

    @timer
    def handle_request(
        self, focal_distance: int, exposure_time_us: int, width: int, height: int
    ) -> bytes:
        global CAMERA
        global CONFIG
        print(
            f"handle_request: {focal_distance=}, {exposure_time_us=}, {width=}, {height=}"
        )
        print(f"{self.last_focal_distance=}")
        if self.last_focal_distance != focal_distance:
            focus_camera(focal_distance)
            sleep(0.5)  # setting the focal distance takes time
            print("focal_distance not implemented yet")
            self.last_focal_distance = focal_distance

        print(f"{self.last_resolution=}")
        if self.last_resolution != (width, height):
            CAMERA.stop()
            CONFIG = CAMERA.create_preview_configuration({"size": (width, height)})
            CONFIG["transform"] = libcamera.Transform(hflip=0, vflip=0)
            CAMERA.configure(CONFIG)
            CAMERA.start()
            self.last_resolution = (width, height)

        print(f"{self.last_exposure_time_us=}")
        if self.last_exposure_time_us != exposure_time_us:
            # FIX: exposure setter does not work
            # CAMERA.set_controls({
            #     'ExposureTime': exposure_time_us, 'AnalogueGain': 1.0,
            #     'Brightness': 0.0, 'Contrast': 1.0, 'Saturation': 1.0,
            #     'Sharpness': 2.0, 'ColourGains': [0.0, 0.0],
            #     'AwbEnable': True
            # })
            self.last_exposure_time_us = exposure_time_us
            print("exposure setter does not work yet")

        img_stream: BytesIO = BytesIO()
        CAMERA.capture_file(img_stream, format="jpeg")
        _ = img_stream.seek(0)
        return img_stream.getvalue()


@timer
def focus_camera(focal_distance: int) -> None:
    """
    Focus camera with value from 0 being the furthest
    and 1023 being the closest
    """

    if not (MIN_FOCAL_DISTANCE <= focal_distance <= MAX_FOCAL_DISTANCE):
        raise ValueError(
            f"Distance value must be between {MIN_FOCAL_DISTANCE} and {MAX_FOCAL_DISTANCE}"
        )

    value: int = (focal_distance << 4) & 0x3FF0
    dat1: int = (value >> 8) & 0x3F
    dat2: int = value & 0xF0

    retries: int = 3
    while retries > 0:
        try:
            _ = subprocess.run(
                ["i2cset", "-y", "10", "0x0c", str(dat1), str(dat2)],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Focus value set: {-focal_distance}")
            break
        except Exception as e:
            print(f"Error: {e}")
            retries -= 1
            print(f"Retrying... {retries} retries left")
    else:
        print("Failed after retries, skipping this iteration")


def main() -> None:
    global CAMERA
    get_camera_options(CAMERA)
    httpd: HTTPServer | None = None
    try:
        server_address: tuple[str, int] = ("", DEFAULT_SERVER_PORT)
        httpd = HTTPServer(server_address, RequestHandler)
        print(f"Server is running on port {DEFAULT_SERVER_PORT}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Interrupt signal received")
    finally:
        if httpd:
            httpd.shutdown()
        CAMERA.close()


if __name__ == "__main__":
    main()
