#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from influxdb import InfluxDBClient
import datetime
import dateutil.parser
import io
import matplotlib
import numpy as np
import struct
import cv2

from flask import (
    request, jsonify, current_app, Response, send_from_directory,
    after_this_request,
    Blueprint
)

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
from matplotlib.font_manager import FontProperties

INFLUXDB_ADDR = '192.168.0.10'
INFLUXDB_PORT = 8086
INFLUXDB_DB = 'sensor'

INFLUXDB_QUERY = """
SELECT mean("temp"),mean("ph"),mean("tds"),mean("do"),mean("flow") FROM "sensor.raspberrypi" WHERE ("hostname" = \'rasp-aqua\') AND time >= now() - 3d GROUP BY time(5m) fill(previous) ORDER by time asc
"""

FONT_REGULAR_PATH = 'font/OptimaLTStd-Medium.otf'
FONT_BOLD_PATH = 'font/OptimaLTStd-Bold.otf'
IMAGE_DPI = 100.0

APP_PATH = '/aqua-monitor'

aqua_monitor = Blueprint('aqua-monitor', __name__, url_prefix=APP_PATH)


def fetch_data():
    VAL_DEF = {
        'temp': 'mean',
        'ph': 'mean_1',
        'tds': 'mean_2',
        'do': 'mean_3',
        'flow': 'mean_4',
    }
    val_map = {}

    client = InfluxDBClient(host=INFLUXDB_ADDR, port=INFLUXDB_PORT, database=INFLUXDB_DB)
    result = client.query(INFLUXDB_QUERY)

    for k,v in VAL_DEF.items():
        val_map[k] = list(map(lambda x: x[v], result.get_points()))

    localtime_offset = datetime.timedelta(hours=9)
    val_map['time'] = list(map(lambda x: dateutil.parser.parse(x['time'])+localtime_offset, result.get_points()))

    return val_map


def plot_font():
    return {
        'sup_title': FontProperties(fname=FONT_BOLD_PATH, size=30),
        'title': FontProperties(fname=FONT_REGULAR_PATH, size=18),
        'value': FontProperties(fname=FONT_BOLD_PATH, size=60),
        'axis': FontProperties(fname=FONT_REGULAR_PATH, size=14),
        'date': FontProperties(fname=FONT_REGULAR_PATH, size=12),
    }


def plot_data(fig, ax, font, title, x, y, ylabel, ylim, fmt, is_last=False):
    ax.set_title(title, fontproperties=font['title'])
    ax.set_ylim(ylim)
    ax.set_xlim([x[0], x[-1] + datetime.timedelta(hours=1)])

    ax.plot(x, y, '.', color='#AAAAAA',
            marker='o', markevery=[len(y)-1],
            markersize=5, markerfacecolor='#cccccc', markeredgewidth=3, markeredgecolor='#999999',
            linewidth=3.0, linestyle='solid')

    ax.text(0.98, 0.05, fmt.format(y[-1]),
            transform=ax.transAxes, horizontalalignment='right',
            color='#000000', alpha=0.9,
            fontproperties=font['value']
    )
    ax.set_ylabel(ylabel)
    for label in (ax.get_yticklabels() + ax.get_xticklabels() ):
        label.set_font_properties(font['axis'])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d\n%-H:%M'))

    ax.grid(axis='x', color='#000000', alpha=0.1,
            linestyle='-', linewidth=1)

    # ax.axes.xaxis.set_visible(xaxis_visible)
    if is_last:
        ax_pos = ax.get_position()
        fig.text(ax_pos.x1 - 0.17, ax_pos.y0 - 0.1,
                 datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                 fontproperties=font['date'])
    else:
        ax.set_xticklabels([])


def create_plot(data):
    PLOT_CONFIG = [
        { 'title':'Temperature',
          'param': 'temp',
          'unit': 'Celsius',
          'ylim': [23, 26],
          'fmt': '{:.1f}'
        },
        { 'title':'pH',
          'param': 'ph',
          'unit': 'pH',
          'ylim': [6, 8],
          'fmt': '{:.1f}'
        },
        { 'title':'Total Dissolved Solids',
          'param': 'tds',
          'unit': 'ppm',
          'ylim': [100, 400],
          'fmt': '{:.0f}'
        },
        { 'title':'Dissolved Oxygen',
          'param': 'do',
          'unit': 'mg/L',
          'ylim': [3, 8],
          'fmt': '{:.1f}'
        },
        { 'title':'Water flow',
          'param': 'flow',
          'unit': 'L/min',
          'ylim': [2, 5],
          'fmt': '{:.1f}'
        },
    ]

    plt.style.use('grayscale')
    plt.subplots_adjust(hspace=0.35)

    font = plot_font()

    fig = plt.figure(1)
    fig.set_size_inches(540/IMAGE_DPI, 960/IMAGE_DPI)
    fig.suptitle('Aquarium monitor', fontproperties=font['sup_title'])

    for i in range(0, len(PLOT_CONFIG)):
        ax = fig.add_subplot(len(PLOT_CONFIG), 1, i+1)
        plot_data(fig, ax, font,
                  PLOT_CONFIG[i]['title'], data['time'], data[PLOT_CONFIG[i]['param']],
                  PLOT_CONFIG[i]['unit'], PLOT_CONFIG[i]['ylim'], PLOT_CONFIG[i]['fmt'],
                  i == (len(PLOT_CONFIG)-1)
        )

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=IMAGE_DPI)
    png_data = buf.getvalue()
    buf.close()

    plt.clf()
    plt.close(fig)

    return png_data


def png2raw4(png_data):
    # NOTE: 力業...
    img = cv2.imdecode(np.frombuffer(png_data, np.uint8), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    raw4_buf = []
    for y in range(0, h):
        for x in range(0, w, 2):
            # NOTE: 輝度を反転した上で 4bit に変換し，隣接画素を 1Byte にパッキング
            c = int((0xFF-img[y][x]) / 16) << 4 | int((0xFF-img[y][x+1]) / 16)
            raw4_buf.append(c)

    return struct.pack('B'*len(raw4_buf), *raw4_buf)


@aqua_monitor.route('/', methods=['GET'])
@aqua_monitor.route('/png', methods=['GET'])
def img_png():
    res = Response(create_plot(fetch_data()), mimetype='image/png')
    res.headers.add('Cache-Control', 'no-cache')

    return res


@aqua_monitor.route('/raw4', methods=['GET'])
def img_raw4():
    res = Response(png2raw4(create_plot(fetch_data())), mimetype='application/octet-stream')
    res.headers.add('Cache-Control', 'no-cache')

    return res
