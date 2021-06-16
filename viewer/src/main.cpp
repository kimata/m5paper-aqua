#pragma GCC optimize("O3")

#include <Arduino.h>
#include <HTTPClient.h>
#include <M5EPD.h>
#include <WiFi.h>
#include <driver/gpio.h>
#include <string.h>

#include "wifi_config.h"

#define IMAGE_URL "http://192.168.0.10:5555/aqua-monitor/raw4"

M5EPD_Canvas canvas(&M5.EPD);

static const int DISP_WIDTH = 540;
static const int DISP_HEIGHT = 960;
static const int BUF_HEIGHT = 20;

RTC_DATA_ATTR int draw_count = 0;

int drawRaw4(const char *url) {
    int filled;
    int len;
    int block;
    uint8_t buf[DISP_WIDTH / 2 * BUF_HEIGHT];

    HTTPClient http;

    http.begin(url);
    int httpCode = http.GET();
    if (httpCode != HTTP_CODE_OK) {
        log_e("HTTP ERROR: %d", httpCode);
        http.end();
        return -1;
    }

    WiFiClient *stream = http.getStreamPtr();

    filled = 0;
    block = 0;
    while (http.connected()) {
        size_t size = stream->available();
        if (!size) {
            delay(1);
            continue;
        }
        if (size > sizeof(buf) - filled) {
            size = sizeof(buf) - filled;
        }
        if ((len = stream->readBytes(buf + filled, size)) > 0) {
            filled += len;
            if (filled == sizeof(buf)) {
                canvas.pushImage(0, BUF_HEIGHT * block, DISP_WIDTH, BUF_HEIGHT,
                                 buf);
                block++;
                filled = 0;
            }
        }
    }
    if (block != (DISP_HEIGHT / BUF_HEIGHT)) {
        return -1;
    }

    canvas.pushCanvas(0, 0, UPDATE_MODE_GC16);

    http.end();

    return 0;
}

void setup() {
    uint32_t i = 0;
    log_i("START");

    M5.begin(); // NOTE: この中で Serial.begin(115200) が実行される
    M5.EPD.SetRotation(90);

    log_i("CONNECT WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);

        if (i++ == 60) {
            log_e("Faile to connect WiFi");
            delay(10);
            esp_deep_sleep(1 * 60 * 1000 * 1000); // NOTE: 1分後に起きる
        }
    }
    log_i("SETUP Done");
}

void loop() {
    log_i("DISPLAY Update");
    if ((draw_count++ % 60) == 0) {
        M5.EPD.Clear(true);
    }

    canvas.createCanvas(540, 960);
    if (drawRaw4(IMAGE_URL) != 0) {
        log_e("Failed to fetch image");
        delay(10);
        esp_deep_sleep(1 * 60 * 1000 * 1000); // NOTE: 1分後に起きる
    }
    canvas.pushCanvas(0, 0, UPDATE_MODE_GC16);

    log_i("Go to sleep...(%d)", draw_count);
    delay(10);
    esp_deep_sleep(30 * 60 * 1000 * 1000); // NOTE: 30分後に起きる
}
