#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask

from aqua_monitor import aqua_monitor


app = Flask(__name__)

app.register_blueprint(aqua_monitor)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=5555, threaded=True)
