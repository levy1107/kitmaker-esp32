#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define FW_VERSION    "202505051500"

// ─── Hardware ───────────────────────────────────────
#define SCREEN_WIDTH   128
#define SCREEN_HEIGHT   64
#define OLED_RESET      -1

#define LDR_PIN         39   // lectura de luminosidad
#define OTA_BUTTON_PIN  15   // pull-OTA al mantener 5 s
// ────────────────────────────────────────────────────

// Wi-Fi & OTA
const char* ssid         = "PoloTics";
const char* password     = "P4L4T3cs";
const char* FIRMWARE_URL =
  "https://raw.githubusercontent.com/levy1107/kitmaker-esp32/main/firmware/latest.bin";

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Muestra dos líneas centradas
void show(const char* l1, const char* l2 = nullptr, uint8_t s = 2) {
  display.clearDisplay();
  display.setTextSize(s);
  display.setTextColor(SSD1306_WHITE);
  int y = (SCREEN_HEIGHT - 8 * s * (l2 ? 2 : 1)) / 2;
  display.setCursor(0, y);
  display.print(l1);
  if (l2) {
    display.setCursor(0, y + 8 * s);
    display.print(l2);
  }
  display.display();
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("FW " FW_VERSION));

  pinMode(OTA_BUTTON_PIN, INPUT_PULLUP);
  pinMode(LDR_PIN,       INPUT);

  Wire.begin();
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  show("Boot…");

  // Conectar Wi-Fi
  WiFi.begin(ssid, password);
  show("Wi-Fi","conectando");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  show("Wi-Fi OK", WiFi.localIP().toString().c_str());
  delay(800);
}

void loop() {
  // ── Lectura LDR ──
  int raw = analogRead(LDR_PIN);
  int pct = map(raw, 0, 4095, 0, 100);
  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0, 0);
  display.printf("L:%d%%", pct);
  display.display();

  // ── OTA (mantener botón 5 s) ──
  static bool checking = false;
  static unsigned long t0 = 0;

  if (digitalRead(OTA_BUTTON_PIN) == LOW) {
    if (!checking) {
      checking = true;
      t0 = millis();
    } else if (millis() - t0 >= 5000) {
      show("OTA","buscando");
      HTTPClient http;
      http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
      http.begin(FIRMWARE_URL);
      int code = http.GET();
      Serial.printf("HTTP %d\n", code);
      if (code == HTTP_CODE_OK) {
        int len = http.getSize();
        if (len > 0 && Update.begin(len)) {
          WiFiClient *stream = http.getStreamPtr();
          size_t written = Update.writeStream(*stream);
          if (written == len && Update.end()) {
            show("OTA OK","Reboot");
            delay(800);
            ESP.restart();
          }
        }
      } else {
        show("Sin","update");
      }
      http.end();
      checking = false;
    }
  } else {
    checking = false;
  }

  delay(200);
}
