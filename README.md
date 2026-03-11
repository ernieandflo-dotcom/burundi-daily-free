# 🌍 Burundi Daily Intelligence — Version Gratuite

Veille économique quotidienne automatisée. **Coût : 0 €/mois.**

**Votre URL mobile :** `https://VOTRE_USERNAME.github.io/burundi-daily-free/`

---

## Stack 100% gratuit

| Fonction | Outil |
|---|---|
| Recherche | DuckDuckGo |
| Résumés | facebook/bart-large-cnn (Hugging Face) |
| Traduction | Helsinki-NLP/opus-mt-en-fr (Hugging Face) |
| Audio TTS | gTTS (Google Translate, sans clé) |
| PDF | ReportLab |
| Hébergement | GitHub Pages |
| Automatisation | GitHub Actions |

---

## ⚡ Démarrage en 5 étapes

### 1. Créer un token Hugging Face (gratuit)
→ [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
→ **New token** → rôle : **Read** → Copiez le token (`hf_...`)

### 2. Créer le dépôt GitHub
Créez un dépôt **public** nommé `burundi-daily-free`

### 3. Uploader les fichiers
Glissez-déposez tout le contenu dans le dépôt GitHub

### 4. Activer GitHub Pages
`Settings → Pages → Source → GitHub Actions`

### 5. Ajouter votre token HF dans GitHub Secrets
`Settings → Secrets and variables → Actions → New repository secret`

| Nom | Valeur |
|---|---|
| `HF_API_KEY` | Votre token Hugging Face |

### Premier lancement
`Actions → "Burundi Daily Intelligence (Free)" → Run workflow`

---

## 📱 Fonctionnalités du viewer

- 4 catégories : Actualités · Marchés · Contrats · Entrepreneurs
- Résumés en français avec chiffres clés et acteurs
- Compteur de pertinence Locale / Régionale / Internationale
- 🃏 Carte PDF individuelle par article (téléchargeable)
- 📄 Rapport PDF complet lisible en ligne
- 🎧 Audio français (gTTS) pour chaque article

---

## ℹ️ Différences vs version payante

La version gratuite fonctionne très bien pour un usage quotidien. Les différences sont :
- Résumés un peu plus courts et moins nuancés (BART vs Claude)
- Traduction correcte mais plus littérale (Helsinki-NLP vs Claude)
- Extraction d'entités basique (regex vs compréhension contextuelle)

Pour une qualité supérieure, la version payante coûte ~1–2 €/mois (Claude API uniquement).
