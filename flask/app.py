#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging
from flask import Flask
from aqua_monitor import aqua_monitor

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import logger

app = Flask(__name__)

app.register_blueprint(aqua_monitor)

if __name__ == "__main__":
    logger.init("panel.m5paper.aqua", level=logging.INFO)
    app.debug = True
    app.run(host="0.0.0.0", port=5555, threaded=False)
