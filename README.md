# 🐧 Linux Update Manager

Application web simple pour gérer les mises à jour de serveurs Linux (AlmaLinux/RHEL et Debian/Ubuntu).

## 📋 Fonctionnalités

- ✅ Gestion centralisée de plusieurs serveurs Linux
- 🔍 Vérification des mises à jour disponibles (toutes ou sécurité uniquement)
- ⬆️ Application des mises à jour à distance (toutes ou sécurité uniquement)
- 🔐 Mises à jour de sécurité isolées pour installations ciblées
- 📊 Tableau de bord avec statistiques en temps réel
- 📜 Historique détaillé des opérations avec :
  - Liste complète des paquets installés
  - Versions avant/après mise à jour
  - Horodatage précis et durée d'exécution
  - Type de mise à jour (toutes/sécurité)
  - Nom d'hôte et serveur pour traçabilité
- 🔐 Connexion SSH sécurisée (clé ou mot de passe)
- 🎯 Support AlmaLinux/RHEL/CentOS et Debian/Ubuntu

## 🛠️ Prérequis

### Sur le serveur de gestion (où l'app tourne)

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Accès SSH vers les serveurs à gérer

### Sur les serveurs à gérer

- SSH activé et accessible
- `sudo` configuré pour l'utilisateur (sans mot de passe recommandé)
- Pour Debian/Ubuntu: `apt` et `apt-get`
- Pour AlmaLinux/RHEL: `yum` ou `dnf`

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone <votre-repo>
cd linux-update-management
```

### 2. Créer un environnement virtuel Python

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
venv\Scripts\activate  # Sur Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer l'application

```bash
cp .env.example .env
```

Éditez `.env` et changez les valeurs si nécessaire:

```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=votre-clé-secrète-unique-et-complexe
DATABASE_URL=sqlite:///updates.db
```

### 5. Lancer l'application

```bash
python app.py
```

L'application sera accessible sur `http://localhost:5000`

## 🔧 Configuration des serveurs distants

### Configuration SSH avec clé (recommandé)

1. Générer une paire de clés SSH si nécessaire:

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/update_manager
```

2. Copier la clé publique sur les serveurs:

```bash
ssh-copy-id -i ~/.ssh/update_manager.pub user@serveur
```

3. Dans l'application, spécifier le chemin: `/home/user/.ssh/update_manager`

### Configuration sudo sans mot de passe

Sur chaque serveur à gérer, éditez la configuration sudo:

```bash
sudo visudo
```

Ajoutez cette ligne (remplacez `username` par votre utilisateur):

```
username ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/apt, /usr/bin/yum, /usr/bin/dnf
```

Pour plus de sécurité, vous pouvez limiter aux commandes spécifiques:

```
username ALL=(ALL) NOPASSWD: /usr/bin/apt-get update, /usr/bin/apt-get upgrade, /usr/bin/apt list, /usr/bin/yum check-update, /usr/bin/yum update, /usr/bin/dnf check-update, /usr/bin/dnf update
```

## 📖 Utilisation

### Ajouter un serveur

1. Cliquer sur "➕ Ajouter un serveur"
2. Remplir le formulaire:
   - **Nom du serveur**: Nom descriptif (ex: "Web Server Prod")
   - **Hostname/IP**: Adresse IP ou nom d'hôte
   - **Port SSH**: Par défaut 22
   - **Utilisateur**: Utilisateur SSH avec droits sudo
   - **Système d'exploitation**: Debian/Ubuntu ou AlmaLinux/RHEL
   - **Chemin clé SSH**: Chemin vers votre clé privée (optionnel)

### Vérifier les mises à jour

Vous avez deux options pour vérifier les mises à jour :

- **"🔍 Vérifier tout"** : Vérifie toutes les mises à jour disponibles
- **"🔐 Vérifier sécurité"** : Vérifie uniquement les mises à jour de sécurité

La liste détaillée des paquets s'affichera avec :
- Nom du paquet
- Version actuelle et nouvelle version
- Indication `[SÉCURITÉ]` pour les mises à jour de sécurité

### Appliquer les mises à jour

Vous avez deux options pour appliquer les mises à jour :

- **"⬆️ Tout mettre à jour"** : Applique toutes les mises à jour disponibles
- **"🔐 MAJ sécurité"** : Applique uniquement les mises à jour de sécurité

Après l'installation :
- Liste complète des paquets installés
- Versions installées
- Sortie détaillée de la commande d'installation

### Consulter l'historique

L'historique détaillé est accessible en bas de page :

- **Cliquez sur une entrée** pour voir les détails complets
- Pour chaque opération :
  - Date et heure exactes
  - Serveur et hostname
  - Type d'action (vérification, mise à jour complète, mise à jour sécurité)
  - Nombre de paquets
  - Durée d'exécution
  - Liste complète des paquets avec versions
  - Sortie complète de la commande

## 🐳 Déploiement avec Docker (optionnel)

Créer un fichier `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

Créer un fichier `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./updates.db:/app/updates.db
      - ~/.ssh:/root/.ssh:ro
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=votre-clé-secrète
    restart: unless-stopped
```

Lancer avec Docker Compose:

```bash
docker-compose up -d
```

## 🔒 Sécurité

### Recommandations importantes

1. **Changez la SECRET_KEY** dans `.env` en production
2. **Utilisez HTTPS** en production (avec un reverse proxy comme nginx)
3. **Limitez l'accès** à l'application (pare-feu, authentification)
4. **Permissions SSH**: Utilisez des clés SSH plutôt que des mots de passe
5. **Sauvegardez** régulièrement la base de données `updates.db`
6. **Logs**: Surveillez les fichiers de logs pour détecter les anomalies

### Configuration avec nginx (production)

Exemple de configuration nginx:

```nginx
server {
    listen 80;
    server_name update-manager.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🧪 Test de l'application

Pour tester la connexion à un serveur:

```bash
# Test SSH manuel
ssh -i ~/.ssh/update_manager user@serveur

# Test commande sudo
ssh -i ~/.ssh/update_manager user@serveur "sudo apt-get update"
```

## 📝 Architecture

```
linux-update-management/
├── app.py              # Application Flask principale
├── config.py           # Configuration
├── models.py           # Modèles de base de données
├── ssh_manager.py      # Gestion SSH et mises à jour
├── requirements.txt    # Dépendances Python
├── static/
│   ├── css/
│   │   └── style.css   # Styles CSS
│   └── js/
│       └── app.js      # JavaScript frontend
├── templates/
│   └── index.html      # Template HTML
└── updates.db          # Base de données SQLite (créée auto)
```

## 🐛 Dépannage

### Erreur de connexion SSH

- Vérifier que le serveur est accessible: `ping serveur`
- Vérifier le port SSH: `telnet serveur 22`
- Tester la connexion SSH manuellement
- Vérifier les permissions de la clé SSH: `chmod 600 ~/.ssh/cle_privee`

### Erreur sudo

- Vérifier la configuration sudo sur le serveur distant
- Tester manuellement: `ssh user@serveur "sudo apt-get update"`

### L'application ne démarre pas

- Vérifier que Python 3.8+ est installé: `python3 --version`
- Vérifier que les dépendances sont installées: `pip list`
- Vérifier les logs d'erreur dans le terminal

## 📄 Licence

Ce projet est fourni tel quel, libre d'utilisation pour des besoins personnels ou professionnels.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir des issues ou des pull requests.

## 📞 Support

Pour toute question ou problème, créez une issue sur le repository GitHub.
