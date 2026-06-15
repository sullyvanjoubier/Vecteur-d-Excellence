# Vecteur d'excellence — Site web

Studio numérique premium pour PME. Sites web, identités visuelles, contenus créatifs.

## Structure

- **index.html** — site principal (responsive, single-file, CSS/JS inline)
- **Formulaire/index.html** — brief créatif client (4-étapes wizard)
- **assets/** — logos, polices (Google Fonts), images
- **projets/** — portfolio en live (7 sites web locaux)

## Charte graphique

**Couleurs :**
- Terre Bleue (navy) : `#1A0089` — structure
- Portland Orange : `#D4633F` — accent (pas de grandes surfaces)
- White Chocolate (crème) : `#EFE7D3` — fond
- Noir Encre : `#1F1F1F` — texte

**Typographie :**
- **Cormorant Garamond** (serif) — titres, signatures, accent
- **Inter** (sans-serif) — corps, UI, lisibilité

Voir `Vecteur-d-excellence_Charte-Graphique.pdf` au niveau parent.

## Formulaires

### Brief créatif (`/Formulaire/`)
4 étapes :
1. **Vous** — contact, métier, présence
2. **Votre projet** — prestations, objectifs (max 2), budget (curseur 0–2000 €), échéance, existant
3. **Direction artistique** — ambiance (max 3), palettes couleur (max 2 ou palette perso à roue chromatique), typo, références
4. **Finalisation** — texte libre, uploads, RDV découverte, RGPD

**Backend :** FormSubmit.co (gratuit) → `vecteur.excellence@gmail.com`
- Native POST (multipart/form-data, pièces jointes 25 Mo)
- Première soumission : clic d'activation dans le mail FormSubmit
- Après : chaque brief arrive direct en Gmail

### Devis (`/index.html` section #devis)
Formulaire classique (multiselect services, budget, uploads). Même FormSubmit backend.

## Dev local

**Prévisualisation :**
```bash
cd "Site web"
python3 -m http.server 8000
```
Ouvre `http://localhost:8000`

**Note macOS/TCC :** Python du preview sandboxé ne lit pas ~/Documents. Solution : miroir `/tmp/vesite_root/`, rsync après edits.

## Déploiement

Site prêt pour :
- **Vercel** / **Netlify** (auto-rebuild sur push GitHub)
- Hébergement statique classique (HTML+CSS+JS, pas de backend)

## Palette (quick ref)

| Rôle | Nom | Hex | RGB | CMYK |
|------|-----|-----|-----|------|
| Primaire | Terre Bleue | #1A0089 | 26,0,137 | 81,100,0,46 |
| Accent | Portland Orange | #D4633F | 212,99,63 | 0,63,80,0 |
| Fond | White Chocolate | #EFE7D3 | 239,231,211 | 0,3,12,6 |
| Encre | Noir Encre | #1F1F1F | 31,31,31 | 0,0,0,88 |

---

**Tagline :** « Le premium accessible à toutes les ambitions »  
**Établi :** Juin 2026
