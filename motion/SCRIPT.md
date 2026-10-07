# « Invisible. » — script définitif (typographie seule, 1:08)

Formats : 9:16 (principal, 1080×1920) · 16:9 (secondaire, 1920×1080) — 30 i/s.
Charte : crème `#EFE7D3` · bleu profond `#1A0089` · orange `#D4633F` (accent) · noir encre `#1F1F1F`.
Typo : Cormorant Garamond (mots isolés, phrases) · Inter Medium (énumérations, contact).
Marges gauche/droite identiques sur les 7 plans : 96 px (9:16) / 160 px (16:9). Règle de fond à 1/3 de la hauteur.
Apparition : fondu 0,5 s + translation verticale de 14 px (12 px en 16:9), puis immobilité.
Temps en dixièmes de seconde (0 = début de la vidéo).

| Plan | Durée | Fond | Texte exact (/ = retour à la ligne 9:16) | Apparition (dixièmes de s) |
|---|---|---|---|---|
| 1 | 0:00–0:07 | crème | « Invisible. » (seul, pleine largeur) | fondu à 6 (0,8 s) · **muet** |
| 2 | 0:07–0:18 | crème | mot réduit en titre, puis « Ce n’est pas votre travail / qui est en cause. » puis « C’est ce qu’on trouve / de vous. » | mot : 70→84 · ligne 1 : 86 · ligne 2 : 93 · (mot à mot : +1) · « C’est ce qu’on trouve » : 114 · « de vous. » : 121 · sortie : 174→179 |
| 3 | 0:18–0:30 | crème | « Une fiche vide. » / « Un site de 2017. » / « Un formulaire qui / ne renvoie rien. » (**orange**) | 186 · 206 · 228 · tenu jusqu’à la coupe |
| 4 | 0:30–0:42 | **bleu**, coupe sèche à 300 | « On ne vous compare pas / à vos concurrents. » puis « On vous compare à / *ce qu’on voit d’eux.* » (crème) | 308 · 315 · 342 · 349 · (mot à mot : +1) · sortie 415→420 |
| 5 | 0:42–0:55 | bleu | « Une page claire. » / « Une fiche complète. » / « Des photos justes. » / « Quelqu’un qui l’entretient. » — chacune précédée d’une règle orange qui se trace (0,55 s) | règle : 426 · 445 · 464 · 483 — texte : règle + 3 · sortie 544→549 |
| 6 | 0:55–1:04 | retour crème (fondu 548→560) | « Votre métier mérite / mieux qu’un résultat / de recherche. » (centré) | fondu 562 (0,9 s) · tenu · sortie 628→635 |
| 7 | 1:04–1:08 | crème | « Vecteur d’excellence » · règle orange (tracée) · « vecteur.excellence@gmail.com » | logo 642 · règle 649 (0,8 s) · contact 658 · fixe jusqu’à 680 |

Un seul élément de texte passe en orange par plan (plan 3, ligne 3). Les règles orange sont des filets, pas du texte.
Aucune voix, aucun pictogramme. Le « 2017 » du plan 3 est conservé tel que dans la trame.

## Son
- 0:00–0:07 : silence total (plan 1).
- 0:07 → : piste instrumentale (cordes tenues + piano feutré, ~76 BPM, intensité constante), entrée progressive, très bas (≈ −30 LUFS), jamais modifiée.
- 0:30,00 : **un seul** son mat et grave (≈ 0,4 s), synchrone avec la coupe crème → bleu.
- 0:56 → 1:04 : extinction progressive sur le plan 6. Plan 7 : signature muette.
- Aucun clic, aucune frappe.

## Régénérer
```
python3 render.py v <dossier_images>      # ou h
python3 audio.py <dossier_audio>
ffmpeg -f concat -safe 0 -i <dossier_images>/frames.txt -i <dossier_audio>/soundtrack_68s.wav ... (voir build.sh)
```

---
# Version dynamique (40 s) — `video2.html`, `audio2.py`
Même texte, rythme x1,7 : 120 BPM, une coupe ou un mot toutes les 0,5 à 1 s, photos réelles (Unsplash, voir CREDITS.md).
| Temps | Scène |
|---|---|
| 0,0–2,5 | « Invisible. » claque, puis disparaît lettre par lettre |
| 2,5–8,8 | artisan (photo plein cadre) puis recherche sur mobile ; barres bleues, mots un par un, « de vous. » sur barre orange |
| 8,5–15,5 | trois photos, trois lignes qui s'empilent (3e en orange) |
| 15,5 | **coupe sèche en bleu + son grave** ; « On ne vous compare pas à vos concurrents. » + 3 vitrines |
| 19,5–23,0 | « On vous compare à ce qu'on voit d'eux. » |
| 23,0–31,0 | quatre lignes, quatre photos, règles orange qui se tracent |
| 31,0–36,5 | balayage crème, « Votre métier mérite mieux qu'un résultat de recherche. » |
| 36,5–40,0 | signature |
Régénération : `render2.py <v|h> <dossier>`, `audio2.py <dossier>`, puis ffmpeg comme dans build.sh.
