#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from influxdb import InfluxDBClient
import datetime
import dateutil.parser
import io
import matplotlib
import numpy as np

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
SELECT mean("ph"),mean("tds"),mean("do"),mean("flow") FROM "sensor.raspberrypi" WHERE ("hostname" = \'rasp-aqua\') AND time >= now() - 3d GROUP BY time(5m) fill(previous) ORDER by time desc
"""

FONT_REGULAR_PATH = 'font/OptimaLTStd-Medium.otf'
FONT_BOLD_PATH = 'font/OptimaLTStd-Bold.otf'
IMAGE_DPI = 100.0

APP_PATH = '/aqua-monitor'

aqua_monitor = Blueprint('aqua-monitor', __name__, url_prefix=APP_PATH)


def fetch_data():
    client = InfluxDBClient(host=INFLUXDB_ADDR, port=INFLUXDB_PORT, database=INFLUXDB_DB)
    result = client.query(INFLUXDB_QUERY)

    ph = list(map(lambda x: x['mean'], result.get_points()))
    tds = list(map(lambda x: x['mean_1'], result.get_points()))
    do = list(map(lambda x: x['mean_2'], result.get_points()))
    flow = list(map(lambda x: x['mean_3'], result.get_points()))

    localtime_offset = datetime.timedelta(hours=9)
    time = list(map(lambda x: dateutil.parser.parse(x['time'])+localtime_offset, result.get_points()))

    return {
        'ph': ph,
        'tds': tds,
        'do': do,
        'flow': flow,
        'time': time,
    }


def plot_font():
    return {
        'sup_title': FontProperties(fname=FONT_BOLD_PATH, size=30),
        'title': FontProperties(fname=FONT_REGULAR_PATH, size=18),
        'value': FontProperties(fname=FONT_BOLD_PATH, size=60),
        'axis': FontProperties(fname=FONT_REGULAR_PATH, size=14),
    }


def plot_data(ax, font, title, x, y, ylabel, ylim, fmt, xaxis_visible=False):
    ax.set_title(title, fontproperties=font['title'])
    ax.set_ylim(ylim)
    ax.set_xlim([x[-1], x[0] + datetime.timedelta(hours=1.5)])

    ax.plot(x, y, '.', color='#666666', markersize=10,  linewidth = 3.0,
             markerfacecolor='#ffffff',
             markeredgewidth=3,
             markeredgecolor='#666666',
             linestyle='solid',             marker="o", markevery=[0])
    ax.axes.xaxis.set_visible(xaxis_visible)
    ax.text(0.98,0.05, fmt.format(y[0]),
             transform=ax.transAxes, horizontalalignment="right",
             color='#cccccc', zorder=0,
             fontproperties=font['value']
    )
    ax.set_ylabel(ylabel)
    for label in (ax.get_yticklabels() + ax.get_xticklabels() ):
        label.set_font_properties(font['axis'])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%-m/%-d\n%-H:%M'))


def create_plot(data):
    PLOT_CONFIG = [
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
          'ylim': [3, 7],
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

    font = plot_font()

    fig = plt.figure(1)
    fig.set_size_inches(540/IMAGE_DPI, 960/IMAGE_DPI)
    fig.suptitle("Aquarium monitor", fontproperties=font['sup_title'])

    for i in range(0, 4):
        ax = fig.add_subplot(4, 1, i+1)
        plot_data(ax, font,
                  PLOT_CONFIG[i]['title'], data['time'], data[PLOT_CONFIG[i]['param']],
                  PLOT_CONFIG[i]['unit'], PLOT_CONFIG[i]['ylim'], PLOT_CONFIG[i]['fmt'])

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=IMAGE_DPI)
    png_data = buf.getvalue()
    buf.close()

    return png_data


@aqua_monitor.route('/', methods=['GET'])
def api_event():
    res = Response(create_plot(fetch_data()), mimetype='image/png')
    res.headers.add('Cache-Control', 'no-cache')

    return res
