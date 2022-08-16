#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import pathlib
import matplotlib
import numpy as np
import datetime
import PIL.Image
import PIL.ImageFont
import logging

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()
from matplotlib.font_manager import FontProperties

from sensor_data import fetch_data


def get_plot_font(config, font_type, size):
    return FontProperties(
        fname=str(
            pathlib.Path(
                os.path.dirname(__file__),
                "..",
                config["PATH"],
                config["MAP"][font_type],
            )
        ),
        size=size,
    )


def plot_font(config):
    return {
        "sup_title": get_plot_font(config, "EN_BOLD", 30),
        "title": get_plot_font(config, "EN_MEDIUM", 24),
        "value": get_plot_font(config, "EN_BOLD", 80),
        "axis_major": get_plot_font(config, "EN_MEDIUM", 28),
        "axis_minor": get_plot_font(config, "EN_MEDIUM", 20),
        "alert": get_plot_font(config, "EN_BOLD", 140),
    }


def plot_data(fig, ax, font, title, x, y, ylabel, yticks, fmt, normal, is_last=False):
    logging.info("plot graph: {title}".format(title=title))
    ax.set_title(title, fontproperties=font["title"])
    ax.set_ylim(yticks[0:2])
    ax.set_yticks(np.arange(*yticks))
    ax.set_xlim([x[0], x[-1] + datetime.timedelta(hours=1)])

    ax.plot(
        x,
        y,
        color="#999999",
        marker="o",
        markevery=[len(y) - 1],
        markersize=5,
        markerfacecolor="#cccccc",
        markeredgewidth=3,
        markeredgecolor="#666666",
        linewidth=3.0,
        linestyle="solid",
    )

    ax.text(
        0.98,
        0.05,
        fmt.format(y[-1]),
        transform=ax.transAxes,
        horizontalalignment="right",
        color="#000000",
        alpha=0.9,
        fontproperties=font["value"],
    )

    if (y[-1] < normal[0]) or (y[-1] > normal[1]):
        ax.text(
            0.25,
            0.05,
            "!",
            transform=ax.transAxes,
            horizontalalignment="right",
            color="#000000",
            alpha=0.9,
            fontproperties=font["alert"],
        )

    ax.set_ylabel(ylabel)

    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=range(0, 24, 6)))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("\n%-H"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-d"))

    for label in ax.get_xticklabels():
        label.set_fontproperties(font["axis_major"])
    for label in ax.get_xminorticklabels():
        label.set_fontproperties(font["axis_minor"])

    ax.grid(axis="x", color="#000000", alpha=0.1, linestyle="-", linewidth=1)
    ax.label_outer()


def get_graph_data(config):
    logging.info("fetch data")

    val_map = {}
    for param in config["GRAPH"]["PARAM_LIST"]:
        data = fetch_data(
            config["INFLUXDB"],
            config["SENSOR"]["TYPE"],
            config["SENSOR"]["HOSTNAME"],
            param["NAME"],
            period="60h",
        )
        val_map[param["NAME"]] = data

    return val_map


def create_graph(config):
    logging.info("draw graph")

    data = get_graph_data(config)

    plt.style.use("grayscale")
    plt.subplots_adjust(hspace=0.35)

    font = plot_font(config["FONT"])

    fig = plt.figure(1)
    fig.set_size_inches(
        config["PANEL"]["DEVICE"]["WIDTH"] / config["PANEL"]["DEVICE"]["DPI"],
        (config["PANEL"]["DEVICE"]["HEIGHT"] - 20) / config["PANEL"]["DEVICE"]["DPI"],
    )

    for i, param in enumerate(config["GRAPH"]["PARAM_LIST"]):
        ax = fig.add_subplot(len(config["GRAPH"]["PARAM_LIST"]), 1, i + 1)

        plot_data(
            fig,
            ax,
            font,
            param["TITLE"],
            data[param["NAME"]]["time"],
            data[param["NAME"]]["value"],
            param["UNIT"],
            [
                param["YTICKS"]["MIN"],
                param["YTICKS"]["MAX"],
                param["YTICKS"]["STEP"],
            ],
            param["FORMAT"],
            [
                param["NORMAL"]["MIN"],
                param["NORMAL"]["MAX"],
            ],
            i == (len(config["GRAPH"]["PARAM_LIST"]) - 1),
        )

    fig.tight_layout()
    plt.subplots_adjust(hspace=0.3, wspace=0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=config["PANEL"]["DEVICE"]["DPI"])
    png_data = buf.getvalue()
    buf.close()

    plt.clf()
    plt.close(fig)

    return png_data


if __name__ == "__main__":
    from config import load_config
    import logger

    logger.init("test")

    create_graph(load_config())
