#!/usr/bin/env python
# auto_commit.py – genera un .ino con ChatGPT y deja que
# GitHub Actions construya firmware/firmware_<ver>.bin + latest.json

import os, re, openai
from github import Github
from datetime import datetime, UTC

openai.api_key = os.getenv("OPENAI_API_KEY")
gh = Github(os.getenv("GITHUB_TOKEN"))

repo   = gh.get_repo("levy1107/kitmaker-esp32")
SKETCH = "sketches/automatic.ino"
TAG    = "🤖 Auto-update"

# ── helpers ──────────────────────────────────────────
def fetch_current():
    try:
        f = repo.get_contents(SKETCH); return f.decoded_content.decode(), f.sha
    except Exception: return "", None

def bump_version(code:str) -> str:
    ver = datetime.now(UTC).strftime("%Y%m%d%H%M")
    if "#define FW_VERSION" in code:
        code=re.sub(r'#define\s+FW_VERSION\s+"[^"]+"',
                    f'#define FW_VERSION "{ver}"', code)
    else:
        code=f'#define FW_VERSION "{ver}"\n'+code
    return code

def generate(current:str, req:str) -> str:
    system = (
        "Eres un asistente que responde **solo** con código .ino completo "
        "para la placa ESP32 KitMaker 2.0.\n\n"
        "Hardware mapping fijo:\n"
        "  • GPIO39 → LDR TEMT6000 (ADC)\n"
        "  • I2C SDA 21 / SCL 22 → OLED 128×64 + HTU21D\n"
        "  • GPIO14 → sensor vibración BL2500\n"
        "  • GPIO0  → botón izquierdo\n"
        "  • GPIO15 → botón medio (OTA, 5 s)\n"
        "  • GPIO13 → botón derecho\n"
        "  • GPIO36 → medición batería (ADC)\n"
        "  • GPIO27 → 4 NeoPixels\n"
        "  • GPIO12 → buzzer pasivo (PWM 2 kHz, canal 0)\n\n"
        "Requisitos obligatorios de cada sketch generado:\n"
        "  • Wi‑Fi SSID \"PoloTics\" / pass \"P4L4T3cs\".\n"
        "  • OTA basada en manifest `latest.json` + bin único "
        "`firmware_<ver>.bin` (sin latest.bin).\n"
        "  • Define  #define FW_VERSION \"YYYYMMDDHHMM\"  actualizado.\n"
    )

    user = (f"Código actual:\n```cpp\n{current}\n```\n\n"
            f"Aplica esto:\n{req}\n\n"
            "Devuélveme *solo* el archivo .ino dentro de ```")

    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}],
    )
    code = resp.choices[0].message.content.strip("` \n")
    return bump_version(code)

def commit(code:str, sha:str):
    msg = f"{TAG} {datetime.now(UTC).isoformat(timespec='seconds')}"
    if sha: repo.update_file(SKETCH,msg,code,sha)
    else:   repo.create_file(SKETCH,msg,code)

# ── main ────────────────────────────────────────────
def main():
    if not (openai.api_key and os.getenv("GITHUB_TOKEN")):
        print("❌ Falta OPENAI_API_KEY o GITHUB_TOKEN"); return

    current, sha = fetch_current()
    req = input("¿Qué quieres cambiar en el sketch?\n> ").strip()
    if not req: print("Sin cambios."); return

    print("⏳ Generando código…")
    new_code = generate(current, req)

    print("📥 Haciendo commit…")
    commit(new_code, sha)
    print("✅ Push listo — GitHub Actions compilará bin y manifest.")

if __name__ == "__main__":
    main()
