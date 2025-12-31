# Configuration des Mises à Jour Automatiques

## 📅 Planification des Mises à Jour

L'application permet de configurer des mises à jour automatiques sur vos serveurs Linux avec des planifications personnalisées.

### Fonctionnalités

- ✅ Planification quotidienne, hebdomadaire ou mensuelle
- ✅ Choix de l'heure d'exécution
- ✅ Mises à jour complètes ou uniquement de sécurité
- ✅ Redémarrage automatique optionnel si nécessaire
- ✅ Configuration automatique via SSH

### Types de Planifications

#### Quotidien
- Exécution tous les jours à une heure spécifique
- Exemple: Tous les jours à 5h00

#### Hebdomadaire
- Exécution un jour spécifique de la semaine
- Exemple: Tous les dimanches à 5h00
- Jours: 0=Lundi, 1=Mardi, ..., 6=Dimanche

#### Mensuel
- Exécution un jour spécifique du mois
- Exemple: Le 1er de chaque mois à 5h00
- Jour: 1-31

## 🔧 Gestion des Prompts de Configuration

### Le Problème

Lors des mises à jour, les gestionnaires de paquets peuvent demander si vous voulez :
- **Garder** votre fichier de configuration existant
- **Installer** la nouvelle version du fichier

Ces prompts bloquent les mises à jour automatiques car ils attendent une réponse humaine.

### La Solution Implémentée

Par défaut, l'application est configurée pour **garder vos fichiers de configuration existants** :

#### Pour Debian/Ubuntu

Options dpkg utilisées automatiquement :
```bash
--force-confold    # Garder l'ancienne version de la configuration
--force-confdef    # Utiliser l'option par défaut (garder existant)
```

Lors des mises à jour, les commandes incluent :
```bash
DEBIAN_FRONTEND=noninteractive \
apt-get upgrade -y \
-o Dpkg::Options::="--force-confold" \
-o Dpkg::Options::="--force-confdef"
```

#### Pour AlmaLinux/RHEL

DNF/YUM gère automatiquement ces conflits en :
- Créant un fichier `.rpmnew` avec la nouvelle configuration
- Conservant votre fichier existant
- Vous permettant de comparer manuellement plus tard si nécessaire

### Comportements Disponibles

Si vous voulez un comportement différent, vous pouvez modifier `config.py` :

```python
# Option 1: Garder les configurations existantes (DÉFAUT)
DPKG_CONFOLD = True   # Garder ancien fichier
DPKG_CONFNEW = False  # Ne pas installer nouveau

# Option 2: Toujours installer les nouvelles configurations
DPKG_CONFOLD = False
DPKG_CONFNEW = True

# Option 3: Demander (NON recommandé pour auto-updates)
# Ne pas spécifier d'options
```

## 🤖 Configuration Automatique sur les Serveurs

### Debian/Ubuntu - unattended-upgrades

L'application installe et configure automatiquement `unattended-upgrades` :

**Fichiers configurés :**
- `/etc/apt/apt.conf.d/50unattended-upgrades` - Configuration principale
- `/etc/apt/apt.conf.d/20auto-upgrades` - Activation
- `/etc/cron.d/linux-update-manager` - Planification cron

**Caractéristiques :**
- Logs dans `/var/log/unattended-upgrades/`
- Nettoyage automatique des paquets non utilisés
- Gestion automatique des redémarrages si configuré
- Pas de prompts de configuration

**Exemple de configuration générée :**
```
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    // "${distro_id}:${distro_codename}-updates";  // Si "all"
};

Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "05:00";

Dpkg::Options {
   "--force-confdef";
   "--force-confold";
};
```

### AlmaLinux/RHEL - dnf-automatic

L'application installe et configure automatiquement `dnf-automatic` ou `yum-cron` :

**Fichiers configurés :**
- `/etc/dnf/automatic.conf` (ou `/etc/yum/yum-cron.conf`)
- `/etc/cron.d/linux-update-manager` - Planification cron
- `/etc/cron.daily/auto-reboot-if-needed` - Script de redémarrage (si activé)

**Caractéristiques :**
- Logs dans `/var/log/dnf-automatic.log` (ou `/var/log/yum-cron.log`)
- Fichiers `.rpmnew` pour les configurations modifiées
- Redémarrage optionnel si `/var/run/reboot-required` existe

**Exemple de configuration générée :**
```ini
[commands]
upgrade_type = security  # ou "default" pour toutes
random_sleep = 0
download_updates = yes
apply_updates = yes

[emitters]
emit_via = stdio
```

## 📋 Exemple d'Utilisation via API

### Créer une planification hebdomadaire

```bash
# Tous les dimanches à 5h00, mises à jour de sécurité uniquement
curl -X POST http://localhost:5000/api/servers/1/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_type": "weekly",
    "day_of_week": 6,
    "hour": 5,
    "minute": 0,
    "update_type": "security",
    "auto_reboot": false,
    "enabled": true
  }'
```

### Récupérer les planifications d'un serveur

```bash
curl http://localhost:5000/api/servers/1/schedules
```

### Supprimer une planification

```bash
curl -X DELETE http://localhost:5000/api/schedules/1
```

### Vérifier le statut de la configuration automatique

```bash
curl http://localhost:5000/api/servers/1/auto-update-status
```

## 🔍 Vérification Manuelle sur les Serveurs

### Debian/Ubuntu

```bash
# Vérifier la configuration
cat /etc/apt/apt.conf.d/50unattended-upgrades
cat /etc/apt/apt.conf.d/20auto-upgrades

# Vérifier le cron job
cat /etc/cron.d/linux-update-manager

# Voir les logs
tail -f /var/log/unattended-upgrades/unattended-upgrades.log

# Tester manuellement
sudo unattended-upgrade --dry-run -d
```

### AlmaLinux/RHEL

```bash
# Vérifier la configuration
cat /etc/dnf/automatic.conf

# Vérifier le cron job
cat /etc/cron.d/linux-update-manager

# Voir les logs
tail -f /var/log/dnf-automatic.log

# Tester manuellement
sudo dnf-automatic
```

## ⚠️ Considérations Importantes

### Redémarrages Automatiques

- **Activer avec précaution** : Peut causer des interruptions de service
- **Heure de redémarrage** : Configurée pour correspondre à votre planification
- **Délai** : 5 minutes de préavis avant redémarrage
- **Recommandation** : Désactiver pour les serveurs critiques

### Sécurité

- Les configurations sont installées via SSH avec vos credentials
- Les fichiers de configuration sont créés avec les permissions appropriées
- Les logs sont consultables pour audit
- sudo est requis sur les serveurs distants

### Mises à Jour de Sécurité vs Toutes

#### Sécurité uniquement (Recommandé pour production)
- ✅ Minimise les risques de régression
- ✅ Applique uniquement les correctifs critiques
- ✅ Moins de risque de casser les applications

#### Toutes les mises à jour
- ⚠️ Inclut des mises à jour non critiques
- ⚠️ Peut introduire des changements de comportement
- ✅ Garde le système complètement à jour
- ✅ Recommandé pour environnements de test

## 🛠️ Dépannage

### Les mises à jour ne s'exécutent pas

1. Vérifier que le cron job existe :
   ```bash
   sudo cat /etc/cron.d/linux-update-manager
   ```

2. Vérifier les logs cron :
   ```bash
   sudo grep CRON /var/log/syslog  # Debian
   sudo tail -f /var/log/cron      # AlmaLinux
   ```

3. Tester la commande manuellement :
   ```bash
   # Debian
   sudo unattended-upgrade -v

   # AlmaLinux
   sudo dnf-automatic
   ```

### Prompts de configuration apparaissent toujours

Vérifier les options dpkg dans la configuration :
```bash
cat /etc/apt/apt.conf.d/50unattended-upgrades | grep -A 3 "Dpkg::Options"
```

Devrait afficher :
```
Dpkg::Options {
   "--force-confdef";
   "--force-confold";
};
```

### Serveur ne redémarre pas automatiquement

1. Vérifier la configuration :
   ```bash
   # Debian
   cat /etc/apt/apt.conf.d/50unattended-upgrades | grep Reboot

   # AlmaLinux
   cat /etc/cron.daily/auto-reboot-if-needed
   ```

2. Vérifier si un redémarrage est nécessaire :
   ```bash
   # Debian
   [ -f /var/run/reboot-required ] && echo "Reboot needed"

   # AlmaLinux
   needs-restarting -r
   ```

## 📚 Références

- [Debian - UnattendedUpgrades](https://wiki.debian.org/UnattendedUpgrades)
- [Ubuntu - Automatic Updates](https://help.ubuntu.com/community/AutomaticSecurityUpdates)
- [RHEL - DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html)
- [Dpkg Configuration File Handling](https://raphaelhertzog.com/2010/09/21/debian-conffile-configuration-file-managed-by-dpkg/)
