#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib
import numpy as np
import struct
import os
import cv2
import sys

from flask import (
    Response,
    Blueprint,
)

matplotlib.use("Agg")

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from config import load_config
import sensor_panel
import logger

APP_PATH = "/aqua-monitor"


def png2raw4(png_data):
    # NOTE: 力業...
    img = cv2.imdecode(np.frombuffer(png_data, np.uint8), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    raw4_buf = []
    for y in range(0, h):
        for x in range(0, w, 2):
            # NOTE: 輝度を反転した上で 4bit に変換し，隣接画素を 1Byte にパッキング
            c = (((0xFF - img[y][x]) >> 4) & 0xF) << 4 | ((0xFF - img[y][x + 1]) >> 4)
            raw4_buf.append(c)

    return struct.pack("B" * len(raw4_buf), *raw4_buf)


aqua_monitor = Blueprint("aqua-monitor", __name__, url_prefix=APP_PATH)


@aqua_monitor.route("/", methods=["GET"])
@aqua_monitor.route("/png", methods=["GET"])
def img_png():
    res = Response(sensor_panel.create_panel(load_config()), mimetype="image/png")
    res.headers.add("Cache-Control", "no-cache")

    return res


@aqua_monitor.route("/raw4", methods=["GET"])
def img_raw4():
    res = Response(
        png2raw4(sensor_panel.create_panel(load_config())),
        mimetype="application/octet-stream",
    )
    res.headers.add("Cache-Control", "no-cache")

    return res
