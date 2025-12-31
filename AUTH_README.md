# Système d'Authentification

## Vue d'ensemble

Linux Update Manager utilise Flask-Login pour gérer l'authentification des utilisateurs. Le système supporte deux types d'authentification :

- **Local** : Authentification avec base de données locale (implémenté)
- **LDAP** : Authentification avec serveur LDAP/Active Directory (à venir)

## Compte Administrateur Local

### Créer un administrateur

Pour créer le premier compte administrateur :

```bash
python3 create_admin.py
```

Le script vous demandera :
- Nom d'utilisateur (par défaut : admin)
- Email (optionnel)
- Mot de passe (minimum 6 caractères)

### Connexion

1. Accédez à l'URL de l'application : `http://votre-serveur:5000`
2. Vous serez redirigé vers la page de connexion
3. Entrez vos identifiants
4. Cliquez sur "Se connecter"

### Déconnexion

Cliquez sur le bouton "🚪 Déconnexion" en haut à droite de la page.

## Configuration LDAP (Future)

### Variables d'environnement

Pour activer l'authentification LDAP, configurez les variables suivantes dans votre fichier `.env` :

```bash
# Type d'authentification
AUTH_TYPE=ldap  # 'local' ou 'ldap'

# Configuration LDAP
LDAP_HOST=ldap://votre-serveur-ldap.com
LDAP_PORT=389
LDAP_BASE_DN=dc=example,dc=com
LDAP_USER_DN=ou=users,dc=example,dc=com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=votre-mot-de-passe
LDAP_USERNAME_ATTRIBUTE=uid
LDAP_USE_TLS=true
```

### Configuration pour Active Directory

Pour Active Directory, utilisez ces paramètres :

```bash
AUTH_TYPE=ldap
LDAP_HOST=ldap://ad.example.com
LDAP_PORT=389
LDAP_BASE_DN=dc=example,dc=com
LDAP_USER_DN=ou=Users,dc=example,dc=com
LDAP_BIND_DN=CN=ServiceAccount,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=votre-mot-de-passe
LDAP_USERNAME_ATTRIBUTE=sAMAccountName
LDAP_USE_TLS=true
```

### Fonctionnement LDAP (à implémenter)

Lorsque l'authentification LDAP sera implémentée :

1. L'utilisateur entre son nom d'utilisateur et mot de passe
2. L'application se connecte au serveur LDAP avec les credentials de service
3. L'application recherche l'utilisateur dans le LDAP
4. L'application tente de s'authentifier avec les credentials de l'utilisateur
5. Si succès, l'utilisateur est créé/mis à jour dans la base locale
6. Une session est créée pour l'utilisateur

### Installation des dépendances LDAP

Quand vous serez prêt à implémenter LDAP, ajoutez à `requirements.txt` :

```
python-ldap==3.4.3
# ou
ldap3==2.9.1
```

## Sécurité

### Bonnes pratiques

1. **Changez la SECRET_KEY** en production :
   ```bash
   # Dans .env
   SECRET_KEY=une-cle-secrete-tres-longue-et-aleatoire
   ```

2. **Utilisez HTTPS** en production pour protéger les credentials

3. **Mots de passe forts** :
   - Minimum 6 caractères (recommandé : 12+)
   - Mélange de majuscules, minuscules, chiffres et symboles

4. **Limitez les tentatives de connexion** (à implémenter) :
   - Rate limiting sur /login
   - Blocage temporaire après X échecs

### Hashage des mots de passe

Les mots de passe sont hashés avec `werkzeug.security` qui utilise :
- Algorithme : pbkdf2:sha256
- Sel aléatoire par mot de passe
- Impossible de récupérer le mot de passe original

## Gestion des utilisateurs

### Modèle User

Champs disponibles :
- `username` : Nom d'utilisateur unique
- `password_hash` : Hash du mot de passe
- `email` : Email (optionnel)
- `is_admin` : Droits administrateur
- `is_active` : Compte actif/désactivé
- `auth_type` : 'local' ou 'ldap'
- `created_at` : Date de création
- `last_login` : Dernière connexion

### Créer des utilisateurs supplémentaires

Pour créer d'autres utilisateurs administrateurs, utilisez le script :

```bash
python3 create_admin.py
```

### Désactiver un utilisateur

Pour désactiver un utilisateur sans le supprimer, utilisez Python :

```python
from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(username='utilisateur').first()
    if user:
        user.is_active = False
        db.session.commit()
        print(f"Utilisateur {user.username} désactivé")
```

## Dépannage

### "Table users has no column"

Si vous avez cette erreur après mise à jour :

```bash
# Supprimer l'ancienne base (sauvegardez vos données d'abord!)
rm updates.db

# Recréer la base avec la nouvelle structure
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"

# Créer un admin
python3 create_admin.py
```

### "Module 'flask_login' has no attribute"

Installez Flask-Login :

```bash
pip3 install -r requirements.txt
```

### Session expirée trop rapidement

Ajoutez dans `config.py` :

```python
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 7 jours
```

## Migration vers LDAP

Quand vous serez prêt à migrer :

1. Installez les dépendances LDAP
2. Configurez les variables d'environnement
3. Implémentez la fonction `authenticate_ldap()` dans un nouveau fichier `ldap_auth.py`
4. Modifiez la route `/login` pour utiliser LDAP selon `AUTH_TYPE`
5. Testez avec un compte LDAP
6. Basculez `AUTH_TYPE=ldap` en production

Les utilisateurs locaux existants continueront de fonctionner même avec LDAP activé.
