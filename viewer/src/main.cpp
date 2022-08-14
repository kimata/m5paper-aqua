#pragma GCC optimize("O3")

#include <Arduino.h>
#include <HTTPClient.h>
#include <M5EPD.h>
#include <WiFi.h>
#include <driver/gpio.h>
#include <string.h>

#include "wifi_config.h"

#define IMAGE_URL "http://192.168.0.20:5555/aqua-monitor/raw4"
#define UPDATE_INTERVAL_SEC (60)
#define NTP_SERVER "ntp.nict.jp"
#define UTC_OFFSET (9 * 60 * 60)

M5EPD_Canvas canvas(&M5.EPD);

static const int DISP_WIDTH = 540;
static const int DISP_HEIGHT = 960;
static const int BUF_HEIGHT = 20;
static const int BATTERY_VOL_MAX = 4200; // NOTE: 手持ちの個体での実測値

RTC_DATA_ATTR int draw_count = 0;

// NOTE: バッテリ駆動する場合は，次のコメントアウトを解除する
// #define USE_BATTERY

int draw_raw4(const char *url) {
    int filled;
    int len;
    int block;
    uint8_t buf[DISP_WIDTH / 2 * BUF_HEIGHT];

    HTTPClient http;
    // NOTE:
    // 現状，raw4画像の生成を富豪的に行っており，サーバ側での処理に時間がかかるので
    // 長めにしておく．
    http.setTimeout(60 * 1000);

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
    http.end();

    if (block != (DISP_HEIGHT / BUF_HEIGHT)) {
        log_e("Size unmatch (blocl, filled) = (%d, %d)", block, filled);
        return -1;
    }

    return 0;
}

int draw_battery() {
    char buf[32];
    uint32_t vol = M5.getBatteryVoltage();

    if (vol < 3200) {
        vol = 3200;
    } else if (vol > BATTERY_VOL_MAX) {
        vol = BATTERY_VOL_MAX;
    }
    float rate = (float)(vol - 3200) / (BATTERY_VOL_MAX - 3200);
    if (rate <= 0.01) {
        rate = 0.01;
    }
    if (rate > 1) {
        rate = 1;
    }

    snprintf(buf, sizeof(buf), "%.2fV (%d%%)", vol / 1000.0, (int)(rate * 100));
    canvas.setTextSize(1);
    canvas.drawString(buf, 5, 945);

    return 0;
}

void goto_sleep(int sleeping_sec) {
    if (WiFi.isConnected()) {
        WiFi.disconnect();
    }
#ifdef USE_BATTERY
    // NOTE: shutdown は USB ケーブルが繋がっていると動かない．
    M5.shutdown(sleeping_sec);
#endif
    M5.disableEPDPower();
    M5.disableEXTPower();
    gpio_hold_en((gpio_num_t)M5EPD_MAIN_PWR_PIN);
    gpio_deep_sleep_hold_en();
    esp_deep_sleep(sleeping_sec * 1000 * 1000);
}

void setup_rtc() {
    struct tm time_info;
    rtc_time_t rtc_time;
    rtc_date_t rtc_date;

    log_i("Setup RTC");

    configTime(UTC_OFFSET, 0, NTP_SERVER);
    getLocalTime(&time_info);

    rtc_time.hour = time_info.tm_hour;
    rtc_time.min = time_info.tm_min;
    rtc_time.sec = time_info.tm_sec;
    M5.RTC.setTime(&rtc_time);

    rtc_date.year = time_info.tm_year + 1900;
    rtc_date.mon = time_info.tm_mon + 1;
    rtc_date.day = time_info.tm_mday;
    M5.RTC.setDate(&rtc_date);
}

void setup() {
    uint32_t i = 0;
    log_i("START");

    M5.begin(); // NOTE: この中で Serial.begin(115200) が実行される

    log_i("CONNECT WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        if (i++ == 60) {
            log_e("Faile to connect WiFi");
            goto_sleep(1);
        }
    }
    if ((draw_count % 100) == 0) {
        setup_rtc();
    }

    log_i("SETUP Done");
}

void loop() {
    log_i("Updating...");

    M5.enableEPDPower();
    M5.EPD.SetRotation(90);

    canvas.createCanvas(540, 960);

    log_i("Fetch image");
    if (draw_raw4(IMAGE_URL) != 0) {
        log_e("Failed to fetch image");
        goto_sleep(1);
    }
    draw_battery();

    log_i("Update display");
    M5.EPD.Clear(true);

    canvas.pushCanvas(0, 0, UPDATE_MODE_GC16);
    delay(500); // NOTE: wait for update (UPDATE_MODE_GC16 requires 450ms)

    log_i("Go to sleep ...(%d)", draw_count++);

    goto_sleep(UPDATE_INTERVAL_SEC);
}
