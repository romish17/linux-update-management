# 🚀 Guide de démarrage rapide

## Installation en 3 étapes

### 1. Installation automatique

```bash
./start.sh
```

Le script va automatiquement:
- Créer l'environnement virtuel Python
- Installer les dépendances
- Générer une clé secrète
- Démarrer l'application

### 2. Accéder à l'application

Ouvrez votre navigateur: **http://localhost:5000**

### 3. Ajouter votre premier serveur

1. Cliquez sur "➕ Ajouter un serveur"
2. Remplissez le formulaire avec vos informations
3. Cliquez sur "🔍 Vérifier" pour tester

## Installation avec Docker

Si vous préférez Docker:

```bash
# Lancer l'application
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter l'application
docker-compose down
```

## Configuration SSH rapide

### Créer une clé SSH

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/update_manager
```

### Copier la clé sur vos serveurs

```bash
ssh-copy-id -i ~/.ssh/update_manager.pub user@votre-serveur
```

### Configurer sudo sans mot de passe

Sur chaque serveur, exécutez:

```bash
sudo visudo
```

Ajoutez (remplacez `username` par votre utilisateur):

```
username ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/apt, /usr/bin/yum, /usr/bin/dnf
```

## Tester la connexion

```bash
# Test de connexion SSH
ssh -i ~/.ssh/update_manager user@votre-serveur

# Test de commande sudo
ssh -i ~/.ssh/update_manager user@votre-serveur "sudo apt-get update"
```

## Dépannage rapide

### Problème de connexion SSH
- Vérifiez que le serveur est accessible: `ping votre-serveur`
- Vérifiez le port SSH: `telnet votre-serveur 22`
- Vérifiez les permissions: `chmod 600 ~/.ssh/update_manager`

### Erreur "sudo requires a password"
- Configurez sudo sans mot de passe (voir ci-dessus)
- Testez manuellement: `ssh user@serveur "sudo -n apt-get update"`

### L'application ne démarre pas
- Vérifiez Python: `python3 --version` (doit être ≥ 3.8)
- Réinstallez les dépendances: `pip install -r requirements.txt`

## Prochaines étapes

1. **Sécurisez l'application** en production avec HTTPS
2. **Configurez un reverse proxy** (nginx) si nécessaire
3. **Planifiez des vérifications automatiques** (cron job)
4. **Sauvegardez** régulièrement `updates.db`

## Support

Consultez le fichier [README.md](README.md) pour la documentation complète.
