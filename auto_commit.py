#!/usr/bin/env python
import os,re,openai
from github import Github
from datetime import datetime,UTC

openai.api_key = os.getenv("OPENAI_API_KEY")
gh = Github(os.getenv("GITHUB_TOKEN"))
repo = gh.get_repo("levy1107/kitmaker-esp32")

SKETCH="sketches/automatic.ino"; TAG="🤖 Auto-update"

def fetch():
    try: f=repo.get_contents(SKETCH); return f.decoded_content.decode(),f.sha
    except: return "",None

def bump(code:str):
    v=datetime.now(UTC).strftime("%Y%m%d%H%M")
    return re.sub(r'#define\s+FW_VERSION\s+"[^"]+"',
                  f'#define FW_VERSION "{v}"',code,1)

def gen(cur:str,req:str)->str:
    sys = (
    "Responde SOLO con el archivo .ino completo. Pines fijos:\n"
    "GPIO39 LDR, 21/22 I2C, GPIO14 Tilt, 0/15/13 botones, "
    "GPIO36 batt, 27 NeoPixels, 12 buzzer PWM canal0 2kHz.\n"
    "Siempre WiFi PoloTics/P4L4T3cs y OTA via manifest latest.json + bin único."
    )
    user=f"Código actual:\n```cpp\n{cur}\n```\nPetición:\n{req}\n"
    r=openai.ChatCompletion.create(model="gpt-4-turbo",
        messages=[{"role":"system","content":sys},{"role":"user","content":user}])
    code=r.choices[0].message.content
    code=code.strip().lstrip("cpp").strip("` \n")     # ← quita 'cpp'
    return bump(code)

def commit(code,sha):
    msg=f"{TAG} {datetime.now(UTC).isoformat(timespec='seconds')}"
    if sha: repo.update_file(SKETCH,msg,code,sha)
    else:   repo.create_file(SKETCH,msg,code)

def main():
    if not (openai.api_key and os.getenv("GITHUB_TOKEN")): return
    cur,sha=fetch(); req=input("Cambio?\n> ").strip(); 
    if not req: return
    commit(gen(cur,req),sha); print("✅ push listo")

if __name__=="__main__": main()
