#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import sys
import pathlib
import textwrap
import traceback
import datetime
import PIL.Image
import PIL.ImageFont
import PIL.ImageDraw
import logging

import sensor_graph


def get_pil_font(config, font_type, size):
    return PIL.ImageFont.truetype(
        str(
            pathlib.Path(
                os.path.dirname(__file__),
                "..",
                config["PATH"],
                config["MAP"][font_type],
            )
        ),
        size,
    )


def pil_font(config):
    return {
        "title": get_pil_font(config, "EN_BOLD", 100),
        "text": get_pil_font(config, "EN_MEDIUM", 20),
        "date": get_pil_font(config, "EN_MEDIUM", 24),
    }


def draw_text(img, text, pos, font, align=True, color="#000"):
    draw = PIL.ImageDraw.Draw(img)
    next_pos_y = pos[1] + font.getsize(text)[1]

    if align:
        # 右寄せ
        None
    else:
        # 左寄せ
        pos = (pos[0] - font.getsize(text)[0], pos[1])

    draw.text(pos, text, color, font, None, font.getsize(text)[1] * 0.4)

    return next_pos_y


def create_error_msg(config, e):
    img = PIL.Image.new(
        "L",
        (config["PANEL"]["DEVICE"]["WIDTH"], config["PANEL"]["DEVICE"]["HEIGHT"]),
        "#FFF",
    )

    draw_text(img, "ERROR", (20, 20), pil_font(config["FONT"])["title"])
    draw_text(
        img,
        "\n".join(textwrap.wrap(traceback.format_exc(), 50)),
        (20, 120),
        pil_font(config["FONT"])["text"],
    )

    bytes_io = io.BytesIO()
    img.save(bytes_io, "PNG")
    bytes_io.seek(0)

    return bytes_io.getvalue()


def create_panel(config):
    logging.info("create panel")
    img = PIL.Image.new(
        "RGBA",
        (config["PANEL"]["DEVICE"]["WIDTH"], config["PANEL"]["DEVICE"]["HEIGHT"]),
        (255, 255, 255, 255),
    )

    try:
        png_data = sensor_graph.create_graph(config)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        png_data = create_error_msg(config, e)

    graph_img = PIL.Image.open(io.BytesIO(png_data))

    img.paste(
        graph_img,
        (0, 0),
    )

    date = datetime.datetime.now().strftime("Update: %H:%M")
    draw_text(
        img,
        date,
        (382, 930),
        pil_font(config["FONT"])["date"],
        align=True,
        color="#555",
    )

    bytes_io = io.BytesIO()
    img.save(bytes_io, "PNG")
    bytes_io.seek(0)

    return bytes_io.getvalue()


if __name__ == "__main__":
    from config import load_config
    import logger

    logger.init("test")

    create_panel(load_config())
