# Détection CVE et Alertes de Sécurité

## ✅ Implémenté

### Backend - Détection CVE pour Debian/Ubuntu

La méthode `DebianUpdateManager.check_updates()` détecte maintenant :

1. **Extraction automatique des CVE**
   - Parse les changelogs des paquets de sécurité
   - Extrait les IDs CVE (format CVE-YYYY-NNNNN)
   - Limite à 10 paquets pour éviter la lenteur

2. **Classification par sévérité**
   - **CRITICAL** : Paquets système critiques
     - Kernel (linux-image, linux-headers)
     - OpenSSL, OpenSSH
     - sudo, systemd
     - glibc/libc6
     - bind9, apache2, nginx
   - **HIGH** : Paquets de sécurité
   - **MEDIUM** : Autres paquets

3. **Retour API enrichi**
   ```python
   {
       'success': True,
       'count': 23,
       'packages': [...],
       'security_count': 5,        # NEW
       'cve_info': [               # NEW
           {
               'id': 'CVE-2024-1234',
               'package': 'openssl',
               'severity': 'critical'
           },
           ...
       ],
       'critical_cves': [          # NEW
           'CVE-2024-1234',
           'CVE-2024-5678'
       ],
       'output': "..."
   }
   ```

4. **Messages enrichis**
   ```
   Found 23 updates available
   ⚠️  5 security updates
   🔴 2 CRITICAL vulnerabilities
      CVEs: CVE-2024-1234, CVE-2024-5678

   Upgradable packages:
   ...
   ```

## 🔨 À Implémenter

### 1. Backend - Modèle de Base de Données

Ajouter des champs à `UpdateHistory` :

```python
class UpdateHistory(db.Model):
    # ... champs existants ...
    security_count = db.Column(db.Integer, default=0)
    cve_list = db.Column(db.Text)  # JSON array de CVE IDs
    critical_cves = db.Column(db.Text)  # JSON array des CVE critiques
```

**Migration nécessaire** : `migrate_db.py`

### 2. Backend - Mise à jour de app.py

Modifier `check_updates` route pour stocker les CVE :

```python
history = UpdateHistory(
    # ... champs existants ...
    security_count=result.get('security_count', 0),
    cve_list=json.dumps(result.get('cve_info', [])),
    critical_cves=json.dumps(result.get('critical_cves', []))
)
```

### 3. Backend - Support RHEL/AlmaLinux

Ajouter `get_cve_info()` pour `AlmaLinuxUpdateManager` :

```python
@staticmethod
def get_cve_info(ssh_manager, packages):
    # Utiliser: yum/dnf updateinfo info <package>
    # ou: yum/dnf updateinfo list security
    pass
```

### 4. Frontend - Types TypeScript

Ajouter à `types/index.ts` :

```typescript
export interface CVEInfo {
  id: string
  package: string
  severity: 'critical' | 'high' | 'medium' | 'low'
}

export interface UpdateHistory {
  // ... champs existants ...
  security_count?: number
  cve_list?: CVEInfo[]
  critical_cves?: string[]
}

export interface Server {
  // ... champs existants ...
  critical_cves_count?: number  // Nombre de CVE critiques
}
```

### 5. Frontend - Dashboard avec Alertes

Ajouter des cartes/alertes sur le Dashboard :

```tsx
{server.critical_cves_count > 0 && (
  <Alert severity="error" icon={<WarningIcon />}>
    {server.critical_cves_count} failles CRITIQUES détectées !
    <Button size="small">Voir détails</Button>
  </Alert>
)}
```

### 6. Frontend - Page CVE dédiée (optionnel)

Créer `frontend/src/pages/CVE.tsx` :
- Liste de tous les CVE détectés
- Filtrage par sévérité
- Filtrage par serveur
- Lien vers détails CVE (NVD, etc.)
- Statut (corrigé/non corrigé)

### 7. Améliorations futures

#### Scanner CVE externe
Intégrer un scanner comme :
- `vuls.io` (scanner Go très complet)
- `lynis` (audit de sécurité)
- API NVD pour enrichir les infos CVE

#### Notifications
- Email pour CVE critiques
- Webhook/Slack
- Rapport hebdomadaire

#### Tableau de bord sécurité
- Score de sécurité par serveur
- Graphiques d'évolution
- Comparaison entre serveurs

## 🚀 Prochaines étapes recommandées

1. **Migration DB** : Ajouter les colonnes CVE
2. **Mise à jour app.py** : Stocker les CVE dans l'historique
3. **Frontend - Alertes Dashboard** : Afficher les CVE critiques
4. **AlmaLinux** : Ajouter support CVE pour RHEL

Voulez-vous que je continue avec une de ces étapes ?
