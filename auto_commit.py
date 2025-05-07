#!/usr/bin/env python
"""
auto_commit.py – genera un .ino con ChatGPT, actualiza #define FW_VERSION,
sube el sketch a GitHub y deja que el workflow compile el binario
firmware_<versión>.bin + latest.json
"""

import os, re, openai, textwrap
from github import Github
from datetime import datetime, UTC

# ── credenciales ──────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY")
gh_token       = os.getenv("GITHUB_TOKEN")
if not (openai.api_key and gh_token):
    raise SystemExit("❌ Falta OPENAI_API_KEY o GITHUB_TOKEN")

gh     = Github(gh_token)
repo   = gh.get_repo("levy1107/kitmaker-esp32")

SKETCH = "sketches/automatic.ino"
TAG    = "🤖 Auto‑update"

# ── utilidades GitHub ─────────────────────────────────────────
def fetch_sketch() -> tuple[str, str | None]:
    """Devuelve (contenido, sha) o ("", None) si no existe aún."""
    try:
        f = repo.get_contents(SKETCH)
        return f.decoded_content.decode(), f.sha
    except Exception:
        return "", None

def push_sketch(code: str, sha: str | None):
    msg = f"{TAG} {datetime.now(UTC).isoformat(timespec='seconds')}"
    if sha:
        repo.update_file(SKETCH, msg, code, sha)
    else:
        repo.create_file(SKETCH, msg, code)

# ── helpers de código ────────────────────────────────────────
def bump_fw_version(code: str) -> str:
    ver = datetime.now(UTC).strftime("%Y%m%d%H%M")
    if "#define FW_VERSION" in code:
        code = re.sub(r'#define\s+FW_VERSION\s+"[^"]+"',
                      f'#define FW_VERSION "{ver}"', code, 1)
    else:
        code = f'#define FW_VERSION "{ver}"\n' + code
    return code

def clean_fence(raw: str) -> str:
    """
    Elimina ```cpp ... ``` y un posible encabezado 'cpp\n'.
    También recorta comillas invertidas sobrantes.
    """
    # quita triple fences
    cleaned = re.sub(r"^```(\w+)?", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.rstrip("` \n")
    # quita 'cpp' aislado
    if cleaned.startswith("cpp"):
        cleaned = cleaned[3:].lstrip()
    return cleaned

# ── prompt base ───────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""\
    Devuelve SOLO el archivo .ino completo (sin explicaciones).
    Pines fijos placas ESP32 KitMaker 2.0:
      • GPIO39  LDR
      • GPIO21/22 I2C (OLED 128×64 y HTU21D)
      • GPIO14  Tilt
      • GPIO0/15/13 botones (15 = OTA 5 s)
      • GPIO36  batería
      • GPIO27  NeoPixels
      • GPIO12  buzzer pasivo (PWM 2 kHz, canal 0)
    Requisitos obligatorios de cada sketch:
      • Wi‑Fi  SSID "PoloTics", pass "P4L4T3cs"
      • OTA por manifest latest.json + bin firmware_<ver>.bin
      • Línea  #define FW_VERSION "YYYYMMDDHHMM"  actualizada
""")

# ── generación con ChatGPT ───────────────────────────────────
def generate_code(current: str, user_req: str) -> str:
    user_prompt = (f"Código actual:\n```cpp\n{current}\n```\n\n"
                   f"Aplica esta modificación:\n{user_req}\n\n"
                   "Devuélveme *solo* el archivo en ```")

    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user",  "content":user_prompt}],
        temperature=0.2
    )
    code_raw = resp.choices[0].message.content
    code = clean_fence(code_raw)
    code = bump_fw_version(code)
    return code

# ── flujo principal ──────────────────────────────────────────
def main() -> None:
    cur, sha = fetch_sketch()
    task = input("¿Qué quieres cambiar en el sketch?\n> ").strip()
    if not task:
        print("Sin cambios."); return

    print("⏳ Generando código…")
    new_code = generate_code(cur, task)

    print("📤 Haciendo push a GitHub…")
    push_sketch(new_code, sha)
    print("✅ Listo: workflow compilará binario y manifest.")

if __name__ == "__main__":
    main()
