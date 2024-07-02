#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib
import pathlib
import numpy as np
import struct
import os
import cv2
import sys
import traceback
import logging

from flask import (
    Response,
    Blueprint,
)

matplotlib.use("Agg")

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from config import load_config
import sensor_panel
import notify_slack

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


def create_panel(config):
    try:
        return sensor_panel.create_panel(config)
    except:
        if "SLACK" in config:
            notify_slack.error(
                config["SLACK"]["BOT_TOKEN"],
                config["SLACK"]["ERROR"]["CHANNEL"],
                traceback.format_exc(),
                config["SLACK"]["ERROR"]["INTERVAL_MIN"],
            )
        raise


aqua_monitor = Blueprint("aqua-monitor", __name__, url_prefix=APP_PATH)


@aqua_monitor.route("/", methods=["GET"])
@aqua_monitor.route("/png", methods=["GET"])
def img_png():
    logging.info("request: png")

    config = load_config()
    res = Response(create_panel(config), mimetype="image/png")
    res.headers.add("Cache-Control", "no-cache")

    logging.info("Finish")
    return res


@aqua_monitor.route("/raw4", methods=["GET"])
def img_raw4():
    logging.info("request: raw4")

    config = load_config()
    res = Response(
        png2raw4(create_panel(config)),
        mimetype="application/octet-stream",
    )
    res.headers.add("Cache-Control", "no-cache")

    pathlib.Path(config["LIVENESS"]["FILE"]).touch()

    logging.info("Finish")
    return res
