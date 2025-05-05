#!/usr/bin/env python
# auto_commit.py – genera un .ino con ChatGPT, lo sube y deja que
# GitHub Actions construya firmware/latest.bin

import os
import re
import openai
from github import Github
from datetime import datetime

# Carga las credenciales desde las variables de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")
gh      = Github(os.getenv("GITHUB_TOKEN"))

# Apunta al repo correcto
repo = gh.get_repo("levy1107/kitmaker-esp32")

SKETCH     = "sketches/automatic.ino"
COMMIT_TAG = "🤖 Auto-update"

def fetch_current():
    """Descarga el código actual y su SHA (si existe)."""
    try:
        f = repo.get_contents(SKETCH)
        return f.decoded_content.decode(), f.sha
    except Exception:
        return "", None

def bump_version(code: str) -> str:
    """Actualiza el #define FW_VERSION a la hora UTC actual (YYYYMMDDHHMM)."""
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M")
    if "#define FW_VERSION" in code:
        code = re.sub(
            r'#define FW_VERSION\s*"[^"]+"',
            f'#define FW_VERSION "{stamp}"',
            code
        )
    else:
        code = f'#define FW_VERSION "{stamp}"\n' + code
    return code

def generate_updated_code(current_code: str, user_request: str) -> str:
    """Pide a ChatGPT que modifique el sketch según la petición del usuario."""
    system_msg = (
        "Eres un asistente que responde EXCLUSIVAMENTE con código .ino para la "
        "placa ESP32 KitMaker 2.0, sin texto extra.\n\n"
        "Hardware:\n"
        "  • ESP32 MCU\n"
        "  • GPIO39  → TEMT6000 (ADC)\n"
        "  • I2C SDA 21 / SCL 22 → HTU21D + OLED 128×64\n"
        "  • GPIO14  → sensor vibración BL2500\n"
        "  • GPIO0   → pulsador izquierdo\n"
        "  • GPIO15  → pulsador medio (OTA pull 5 s)\n"
        "  • GPIO13  → pulsador derecho\n"
        "  • GPIO36  → medición batería (ADC)\n"
        "  • GPIO27  → 4 NeoPixels (5 V tolerantes)\n"
        "  • GPIO12  → buzzer **pasivo** (debe excitarse con PWM ~2 kHz).\n\n"
        "En la salida incluye SIEMPRE:\n"
        "  • Configuración Wi-Fi (SSID: Polotics / pass: P4L4T3cs)\n"
        "  • Lógica Pull-OTA con URL HTTPS:\n"
        "    https://raw.githubusercontent.com/levy1107/kitmaker-esp32/main/firmware/latest.bin\n"
        "  • Una línea  #define FW_VERSION \"YYYYMMDDHHMM\"  ¡actualízala cada vez!\n"
    )

    user_msg = (
        "Código actual:\n```cpp\n"
        + current_code
        + "\n```\n\n"
        "Aplica esta modificación:\n"
        + user_request
        + "\n\n"
        "Devuélveme SOLO el archivo .ino completo dentro de ```."
    )

    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
    )

    # Extrae y actualiza la versión
    code = resp.choices[0].message.content
    code = code.strip().strip("```").replace("cpp\n", "")
    return bump_version(code)

def commit_updated_code(code: str, sha: str):
    """Sube el código nuevo al repo, creando o actualizando el archivo."""
    msg = f"{COMMIT_TAG} {datetime.utcnow().isoformat(timespec='seconds')}Z"
    if sha:
        repo.update_file(SKETCH, msg, code, sha)
    else:
        repo.create_file(SKETCH, msg, code)

def main():
    # Validación de credenciales
    if not openai.api_key or not os.getenv("GITHUB_TOKEN"):
        print("❌ Falta OPENAI_API_KEY o GITHUB_TOKEN")
        return

    # Obtiene código actual
    current_code, sha = fetch_current()
    if not current_code:
        print(f"⚠️ {SKETCH} no existe; se creará.")

    # Solicita al usuario la petición de cambio
    req = input("¿Qué quieres cambiar en el sketch?\n> ").strip()
    if not req:
        print("Sin cambios pedidos.")
        return

    # Genera y sube
    print("⏳ Generando código con ChatGPT…")
    new_code = generate_updated_code(current_code, req)

    print("📥 Subiendo a GitHub…")
    commit_updated_code(new_code, sha)
    print("✅ Listo: GitHub Actions compilará latest.bin.")

if __name__ == "__main__":
    main()
