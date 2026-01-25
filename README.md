
# 🤖 VeilleManager - Bot de Gamification Discord

## 📝 Description

**VeilleManager** est un bot Discord conçu pour **gamifier la veille technologique** au sein d'une classe ou d'une équipe de développeurs.
Il encourage la lecture des articles techniques en attribuant de l'expérience (XP) et des niveaux aux utilisateurs actifs, tout en automatisant l'accueil des nouveaux arrivants.

Ce bot est conçu pour fonctionner en tandem avec un système d'automatisation (comme n8n) qui poste les articles, mais il peut fonctionner de manière autonome pour la gestion communautaire.

## ✨ Fonctionnalités

* **🎓 Auto-Role** : Attribution automatique du rôle "Reader" (ou autre) aux nouveaux arrivants sur le serveur.
* **👋 Accueil Personnalisé** : Message de bienvenue automatique dans le salon général.
* **✅ Auto-Réaction** : Ajoute automatiquement un emoji de validation sur les nouveaux articles postés dans le salon de veille.
* **📈 Système d'XP (Leveling)** :
* Les utilisateurs gagnent de l'XP en cliquant sur la réaction d'un article.
* Sauvegarde des données (persistence) via un fichier JSON local.


* **🏆 Annonce de Niveaux** : Notification publique lorsqu'un utilisateur passe un niveau supérieur.

## 🛠️ Prérequis

* Un token de Bot Discord (via le [Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications)).
* **Python 3.9+** (pour tester en local) OU **Docker** (recommandé pour la prod).
* Avoir activé les **"Privileged Gateway Intents"** (Presence, Server Members, Message Content) sur le portail développeur.

## ⚙️ Configuration

Avant de lancer le bot, ouvrez le fichier `bot.py` et modifiez les variables en haut du fichier :

```python
TOKEN = "VOTRE_TOKEN_DISCORD_ICI"
CHANNEL_VEILLE_ID = 123456789012345678  # ID du salon où sont postées les news
CHANNEL_GENERAL_ID = 123456789012345678 # ID du salon pour les bienvenues/LevelUp
ROLE_READER_NAME = "Reader"             # Nom exact du rôle à donner

```

## 🚀 Installation & Démarrage

### Option A : Via Docker (Recommandé)

Cette méthode assure que le bot tourne 24/7 et redémarre en cas de crash.

1. **Créer le fichier de sauvegarde** (Indispensable avant le premier lancement) :
```bash
touch xp_data.json && echo "{}" > xp_data.json

```


2. **Construire l'image** :
```bash
docker build -t veille-bot .

```


3. **Lancer le conteneur** :
```bash
docker run -d \
  --name bot-discord \
  --restart unless-stopped \
  -v $(pwd)/xp_data.json:/app/xp_data.json \
  veille-bot

```



### Option B : En local (Python)

1. Installer les dépendances :
```bash
pip install discord.py

```


2. Lancer le script :
```bash
python3 bot.py

```



## 🎮 Commandes Disponibles

| Commande | Description |
| --- | --- |
| `!level` | Affiche votre niveau actuel, votre XP totale et la progression vers le prochain niveau. |
| `!help` | Affiche le menu d'aide personnalisé expliquant le fonctionnement de la veille. |
| `!clear <n>` | *(Admin uniquement)* Supprime les `<n>` derniers messages du salon courant. |

## 📂 Structure des fichiers

```text
.
├── bot.py           # Code source principal du bot
├── Dockerfile       # Configuration pour l'image Docker
├── xp_data.json     # Fichier de base de données (XP des utilisateurs)
└── README.md        # Documentation

```

## 🛡️ Persistence des données

Le système utilise un volume Docker (`-v`) pour lier le fichier `xp_data.json` du conteneur à celui de votre machine hôte.
**Conséquence :** Si vous supprimez ou mettez à jour le conteneur Docker, les niveaux et l'XP des utilisateurs sont conservés !
