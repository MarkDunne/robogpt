#include "WiFi.h"
#include "ESPAsyncWebServer.h"
#include "esp_camera.h"

// WiFi credentials
const char *ssid = "Marks Pixel";
const char *password = "aijzdipzkafaumi";

// Motor control pins (motor1 = left, motor2 = right)
const int motor1_forward = 21;
const int motor1_reverse = 48;
const int motor2_forward = 35;
const int motor2_reverse = 37;
const int motor_pwr = 150;
const int movement_duration = 500;

// Camera pins for ESP32-S3-CAM
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5
#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM       8
#define Y3_GPIO_NUM       9
#define Y2_GPIO_NUM       11
#define VSYNC_GPIO_NUM    6
#define HREF_GPIO_NUM     7
#define PCLK_GPIO_NUM     13

// Global objects
AsyncWebServer server(80);
bool camera_initialized = false;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================");
  Serial.println("ESP32-S3-CAM Robot Control");
  Serial.println("========================================");

  // Initialize motors
  pinMode(motor1_forward, OUTPUT);
  pinMode(motor1_reverse, OUTPUT);
  pinMode(motor2_forward, OUTPUT);
  pinMode(motor2_reverse, OUTPUT);
  stopMotors();
  Serial.println("Motors initialized");

  // CRITICAL: Camera MUST be initialized before WiFi
  // Do NOT call WiFi.mode() - it causes crashes with QSPI PSRAM
  Serial.println("Initializing camera...");
  camera_initialized = initCamera();
  if (camera_initialized) {
    Serial.println("Camera OK");
  } else {
    Serial.println("Camera FAILED");
  }

  // Connect to WiFi (only WiFi.begin, nothing else)
  Serial.printf("Connecting to %s...", ssid);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWiFi connected: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nWiFi FAILED");
  }

  // Setup web server
  setupRestEndpoints();
  server.begin();

  Serial.println("========================================");
  Serial.printf("Camera: %s | WiFi: %s\n",
    camera_initialized ? "ON" : "OFF",
    WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "DISCONNECTED"
  );
  Serial.println("System ready");
  Serial.println("========================================\n");

  // Wiggle to indicate ready!
  wiggle();
}

void loop() {
  // All handled by async server
}

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;  // 640x480
  config.jpeg_quality = 10;  // Lower number = better quality (range 0-63)
  config.fb_count = 2;  // Use 2 buffers for smoother capture at higher resolution
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init error: 0x%x\n", err);
    return false;
  }

  return true;
}

void stopMotors() {
  analogWrite(motor1_forward, 0);
  analogWrite(motor1_reverse, 0);
  analogWrite(motor2_forward, 0);
  analogWrite(motor2_reverse, 0);
}

void wiggle() {
  for (int i = 0; i < 3; i++) {
    analogWrite(motor1_forward, 100);
    analogWrite(motor2_reverse, 100);
    delay(150);
    stopMotors();
    delay(100);
    analogWrite(motor1_reverse, 100);
    analogWrite(motor2_forward, 100);
    delay(150);
    stopMotors();
    delay(100);
  }
}

void moveForward(int duration) {
  stopMotors();
  delay(10);
  analogWrite(motor1_forward, motor_pwr);
  analogWrite(motor2_forward, motor_pwr);
  delay(duration);
  stopMotors();
}

void moveBackward(int duration) {
  stopMotors();
  delay(10);
  analogWrite(motor1_reverse, motor_pwr);
  analogWrite(motor2_reverse, motor_pwr);
  delay(duration);
  stopMotors();
}

void turnLeft(int duration) {
  stopMotors();
  delay(10);
  analogWrite(motor1_reverse, motor_pwr);
  analogWrite(motor2_forward, motor_pwr);
  delay(duration);
  stopMotors();
}

void turnRight(int duration) {
  stopMotors();
  delay(10);
  analogWrite(motor1_forward, motor_pwr);
  analogWrite(motor2_reverse, motor_pwr);
  delay(duration);
  stopMotors();
}

camera_fb_t* capturePhoto() {
  if (!camera_initialized) return NULL;
  return esp_camera_fb_get();
}

void sendJson(AsyncWebServerRequest *request, int code, const char* json) {
  AsyncWebServerResponse *response = request->beginResponse(code, "application/json", json);
  response->addHeader("Access-Control-Allow-Origin", "*");
  request->send(response);
}

void setupRestEndpoints() {
  // Motor control
  server.on("/api/motor/forward", HTTP_GET, [](AsyncWebServerRequest *request) {
    int duration = movement_duration;
    if (request->hasParam("duration")) {
      duration = request->getParam("duration")->value().toInt();
      duration = constrain(duration, 50, 5000);  // Limit between 50ms and 5s
    }
    moveForward(duration);
    sendJson(request, 200, "{\"status\":\"ok\",\"action\":\"forward\"}");
  });

  server.on("/api/motor/backward", HTTP_GET, [](AsyncWebServerRequest *request) {
    int duration = movement_duration;
    if (request->hasParam("duration")) {
      duration = request->getParam("duration")->value().toInt();
      duration = constrain(duration, 50, 5000);  // Limit between 50ms and 5s
    }
    moveBackward(duration);
    sendJson(request, 200, "{\"status\":\"ok\",\"action\":\"backward\"}");
  });

  server.on("/api/motor/left", HTTP_GET, [](AsyncWebServerRequest *request) {
    int duration = movement_duration;
    if (request->hasParam("duration")) {
      duration = request->getParam("duration")->value().toInt();
      duration = constrain(duration, 50, 5000);  // Limit between 50ms and 5s
    }
    turnLeft(duration);
    sendJson(request, 200, "{\"status\":\"ok\",\"action\":\"left\"}");
  });

  server.on("/api/motor/right", HTTP_GET, [](AsyncWebServerRequest *request) {
    int duration = movement_duration;
    if (request->hasParam("duration")) {
      duration = request->getParam("duration")->value().toInt();
      duration = constrain(duration, 50, 5000);  // Limit between 50ms and 5s
    }
    turnRight(duration);
    sendJson(request, 200, "{\"status\":\"ok\",\"action\":\"right\"}");
  });

  server.on("/api/motor/stop", HTTP_GET, [](AsyncWebServerRequest *request) {
    stopMotors();
    sendJson(request, 200, "{\"status\":\"ok\",\"action\":\"stop\"}");
  });

  // Camera
  server.on("/api/camera/photo", HTTP_GET, [](AsyncWebServerRequest *request) {
    camera_fb_t *fb = capturePhoto();
    if (fb == NULL) {
      sendJson(request, 500, "{\"status\":\"error\",\"message\":\"Camera failed\"}");
      return;
    }

    // Copy buffer data since AsyncWebServer sends asynchronously
    uint8_t *buffer = (uint8_t *)malloc(fb->len);
    if (buffer == NULL) {
      esp_camera_fb_return(fb);
      sendJson(request, 500, "{\"status\":\"error\",\"message\":\"Out of memory\"}");
      return;
    }

    memcpy(buffer, fb->buf, fb->len);
    size_t len = fb->len;
    esp_camera_fb_return(fb);  // Return frame buffer immediately

    // Send copied buffer and free it after transmission
    AsyncWebServerResponse *response = request->beginResponse(
      "image/jpeg",
      len,
      [buffer, len](uint8_t *out_buffer, size_t maxLen, size_t index) -> size_t {
        size_t remaining = len - index;
        size_t will_copy = (remaining > maxLen) ? maxLen : remaining;
        memcpy(out_buffer, buffer + index, will_copy);
        if (index + will_copy >= len) {
          free((void*)buffer);  // Free when done
        }
        return will_copy;
      }
    );
    response->addHeader("Access-Control-Allow-Origin", "*");
    request->send(response);
  });

  // Status
  server.on("/api/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    char json[200];
    snprintf(json, sizeof(json),
      "{\"camera\":%s,\"wifi\":\"%s\"}",
      camera_initialized ? "true" : "false",
      WiFi.localIP().toString().c_str()
    );
    sendJson(request, 200, json);
  });

  // CORS
  server.onNotFound([](AsyncWebServerRequest *request) {
    if (request->method() == HTTP_OPTIONS) {
      AsyncWebServerResponse *response = request->beginResponse(200);
      response->addHeader("Access-Control-Allow-Origin", "*");
      response->addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      request->send(response);
    } else {
      sendJson(request, 404, "{\"status\":\"error\",\"message\":\"Not found\"}");
    }
  });
}
