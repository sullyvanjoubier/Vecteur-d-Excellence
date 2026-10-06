# Motion — Variante A « La vitrine a changé de place »

Livrables (78 s, H.264 + AAC, ≈ −16 LUFS) :

| Fichier | Format |
|---|---|
| `Vecteur-d-Excellence_Variante-A_9x16.mp4` | 1080×1920 — format principal (Reels, Shorts, Stories) |
| `Vecteur-d-Excellence_Variante-A_16x9.mp4` | 1920×1080 — LinkedIn, site, présentation |
| `pistes_voix-off.m4a` · `pistes_musique-instrumentale.m4a` | pistes séparées pour le remontage |
| `SCRIPT.md` | script final, minutage, intentions sonores |

Tout est généré par code, sans banque d'images ni de sons (`src/`) :

* `voice.py` — voix off française (Piper, voix `fr_FR-siwis-medium`) + minutage des mots ;
* `scene.py` — la scène vectorielle 2D (Cairo), partagée par les deux formats ;
* `render.py` / `render_all.sh` — rendu image par image → H.264 ;
* `audio.py` — musique, bruit de crayon calé sur la vitesse du tracé, trois déclics ;
* `mix.sh` — mixage et normalisation.

Reproduire :

```bash
python3 -m venv --system-site-packages venv && venv/bin/pip install piper-tts pycairo
# polices : Cormorant Garamond Medium + Medium Italic (Google Fonts) dans ~/.fonts ; Inter installée
# modèle de voix : https://huggingface.co/rhasspy/piper-voices (fr/fr_FR/siwis/medium)
venv/bin/python src/voice.py out voice/fr_FR-siwis-medium.onnx
venv/bin/python src/audio.py out/timings.json out
PY=venv/bin/python src/render_all.sh out/timings.json out
src/mix.sh out
ffmpeg -i out/silent_9x16.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart final_9x16.mp4
```
