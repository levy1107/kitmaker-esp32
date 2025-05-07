
#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define FW_VERSION "202505071333"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET   -1

#define OTA_BUTTON    15

const char* ssid = "PoloTics";
const char* pass = "P4L4T3cs";

const char* MANIFEST_BASE =
  "https://raw.githubusercontent.com/levy1107/kitmaker-esp32/main/firmware/latest.json";

Adafruit_SSD1306 oled(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void show(const char* a,const char* b=nullptr,uint8_t s=2){
  oled.clearDisplay(); oled.setTextSize(s); oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0,0); oled.print(a);
  if(b){ oled.setCursor(0,8*s); oled.print(b); }
  oled.display();
}
inline void show(const char* a,const String& b,uint8_t s=2){ show(a,b.c_str(),s); }

bool flash(String url){
  HTTPClient http; http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  http.begin(url); int c=http.GET(); if(c!=HTTP_CODE_OK) return false;
  int len=http.getSize(); if(len<=0||!Update.begin(len)) return false;
  size_t w=Update.writeStream(*http.getStreamPtr());
  return (w==len && Update.end());
}

void check_ota(){
  String man = String(MANIFEST_BASE)+"?ts="+millis();
  HTTPClient http; http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  http.begin(man); if(http.GET()!=HTTP_CODE_OK){ show("Sin","manifest"); return; }

  DynamicJsonDocument d(384);
  if(deserializeJson(d,http.getStream())){ show("JSON","err"); return; }
  String ver=d["version"]|""; String url=d["url"]|"";

  if(ver.toInt()>String(FW_VERSION).toInt()){
    show("Actualiza","->"+ver);
    if(flash(url)){ show("OTA OK","Reboot"); delay(800); ESP.restart(); }
    else show("Err","update");
  }else show("Ya","al dia");
}

void setup(){
  Serial.begin(115200);
  pinMode(OTA_BUTTON,INPUT_PULLUP);

  oled.begin(SSD1306_SWITCHCAPVCC,0x3C); show("HOLA", nullptr, 2);
  WiFi.begin(ssid,pass); while(WiFi.status()!=WL_CONNECTED){delay(300);}
}

void loop(){
  static bool chk=false; static unsigned long t0=0;
  if(digitalRead(OTA_BUTTON)==LOW){
    if(!chk){ chk=true; t0=millis(); }
    else if(millis()-t0>5000){ check_ota(); chk=false; }
  }else chk=false;

  delay(800);
}