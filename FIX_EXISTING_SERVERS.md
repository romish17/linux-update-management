# Correction de la configuration sudoers pour les serveurs existants

## Problème
Les serveurs provisionnés avant cette mise à jour ont une configuration sudoers qui ne permet pas de définir des variables d'environnement comme `DEBIAN_FRONTEND`, causant l'erreur :
```
sudo: sorry, you are not allowed to set the following environment variables: DEBIAN_FRONTEND
```

## Solutions

### Option 1 : Re-provisionner (Recommandé)

La méthode la plus simple est de supprimer et re-provisionner vos serveurs :

1. Notez les informations de vos serveurs (hostname, port, etc.)
2. Dans l'interface web, supprimez les serveurs existants
3. Reconstruisez le backend : `docker-compose down && docker-compose up -d --build backend`
4. Re-provisionnez vos serveurs via l'interface

### Option 2 : Mise à jour manuelle via SSH

Si vous ne pouvez pas re-provisionner, connectez-vous manuellement en root sur chaque serveur :

#### Pour Debian/Ubuntu :

```bash
# Se connecter en root sur le serveur distant
ssh root@votre-serveur

# Mettre à jour le fichier sudoers
cat > /etc/sudoers.d/lum-user << 'EOF'
lum-user ALL=(ALL) NOPASSWD: SETENV: /usr/bin/apt-get, /usr/bin/apt, /usr/bin/dpkg, /usr/bin/apt-cache, /sbin/reboot, /sbin/shutdown
EOF

# Définir les permissions correctes
chmod 440 /etc/sudoers.d/lum-user

# Valider la syntaxe
visudo -c -f /etc/sudoers.d/lum-user
```

#### Pour AlmaLinux/RHEL :

```bash
# Se connecter en root sur le serveur distant
ssh root@votre-serveur

# Mettre à jour le fichier sudoers
cat > /etc/sudoers.d/lum-user << 'EOF'
lum-user ALL=(ALL) NOPASSWD: SETENV: /usr/bin/yum, /usr/bin/dnf, /usr/bin/rpm, /sbin/reboot, /sbin/shutdown
EOF

# Définir les permissions correctes
chmod 440 /etc/sudoers.d/lum-user

# Valider la syntaxe
visudo -c -f /etc/sudoers.d/lum-user
```

## Vérification

Après la mise à jour, testez la configuration :

```bash
# Sur le serveur distant, en tant que lum-user
sudo DEBIAN_FRONTEND=noninteractive apt-get --version
```

Si aucune erreur n'apparaît, la configuration est correcte !

## Serveurs futurs

Tous les nouveaux serveurs provisionnés via l'interface auront automatiquement la configuration correcte avec `SETENV:`.
