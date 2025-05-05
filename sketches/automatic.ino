#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_HTU21DF.h>

#define FW_VERSION "202505051500"

// ─── Hardware ──────────────────────────────
#define SCREEN_WIDTH     128
#define SCREEN_HEIGHT     64
#define OLED_RESET        -1

#define LDR_PIN           39
#define OTA_BUTTON_PIN    15
#define BUZZER_BUTTON_PIN 0
#define BUZZER_PIN        12
// ───────────────────────────────────────────

// Wi‑Fi & OTA
const char* ssid = "PoloTics";
const char* password = "P4L4T3cs";
const char* FIRMWARE_URL =
  "https://raw.githubusercontent.com/levy1107/kitmaker-firmware/main/firmware/latest.bin";

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Adafruit_HTU21DF htu;

// ─── Utils ──────────────────────────────
void show(const char* l1, const char* l2=nullptr,uint8_t s=2){
  display.clearDisplay(); display.setTextSize(s); display.setTextColor(SSD1306_WHITE);
  int y=(SCREEN_HEIGHT-8*s*(l2?2:1))/2;
  display.setCursor(0,y);  display.print(l1);
  if(l2){ display.setCursor(0,y+8*s); display.print(l2); }
  display.display();
}
// ───────────────────────────────────────

void setup() {
  Serial.begin(115200);
  Serial.println(F("FW " FW_VERSION));

  pinMode(OTA_BUTTON_PIN,    INPUT_PULLUP);
  pinMode(BUZZER_BUTTON_PIN, INPUT_PULLUP);

  // buzzer PWM 2 kHz canal 0
  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER_PIN, 0);

  Wire.begin();
  display.begin(SSD1306_SWITCHCAPVCC,0x3C);
  show("Boot…");

  if(!htu.begin()){ show("HTU21D ERR"); while(1); }

  // Wi‑Fi
  WiFi.begin(ssid,password);
  show("Wi‑Fi","conectando");
  while(WiFi.status()!=WL_CONNECTED){delay(500);}

  show("Wi‑Fi OK",WiFi.localIP().toString().c_str());
  delay(800);
}

void loop() {
  /* ── Buzzer 5 s tras pulsar GPIO0 ── */
  static bool buzz=false; static unsigned long tBuzz=0;
  if(digitalRead(BUZZER_BUTTON_PIN)==LOW && !buzz){
    buzz=true; tBuzz=millis();
    ledcWrite(0,128);             // 50 % duty, suena
  }
  if(buzz && millis()-tBuzz>=5000){
    ledcWrite(0,0); buzz=false;   // detener sonido
  }

  /* ── Sensores ── */
  float t=htu.readTemperature();
  int ldr=analogRead(LDR_PIN);
  int ldrPct=map(ldr,0,4095,0,100);

  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(0,0);  display.printf("T:%.1fC",t);
  display.setCursor(0,32); display.printf("L:%d%%",ldrPct);
  display.display();

  /* ── OTA botón 15 ── */
  static bool check=false; static unsigned long tStart=0;
  if(digitalRead(OTA_BUTTON_PIN)==LOW){
    if(!check){ check=true;tStart=millis();}
    else if(millis()-tStart>=5000){
      show("OTA","buscando");
      HTTPClient http;
      http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
      http.begin(FIRMWARE_URL);
      int c=http.GET(); Serial.printf("HTTP %d\n",c);
      if(c==HTTP_CODE_OK){
        int len=http.getSize();
        if(len>0 && Update.begin(len)){
          WiFiClient *s=http.getStreamPtr();
          size_t w=Update.writeStream(*s);
          if(w==len && Update.end()){
            show("OTA OK","Reboot"); delay(800); ESP.restart();
          }
        }
      } else show("Sin","update");
      http.end(); check=false;
    }
  }else check=false;

  delay(200);
}
