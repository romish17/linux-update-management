#!/usr/bin/env python3
"""
Script to create an admin user for Linux Update Manager
"""

import sys
import getpass
from app import app, db
from models import User


def create_admin_user():
    """Create an admin user interactively"""
    print("\n=== Création d'un compte administrateur ===\n")

    # Get username
    while True:
        username = input("Nom d'utilisateur (admin): ").strip() or "admin"
        if len(username) < 3:
            print("❌ Le nom d'utilisateur doit contenir au moins 3 caractères")
            continue

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            overwrite = input(f"⚠️  L'utilisateur '{username}' existe déjà. Écraser? (o/N): ").strip().lower()
            if overwrite == 'o':
                db.session.delete(existing_user)
                db.session.commit()
                break
            else:
                continue
        break

    # Get email (optional)
    email = input("Email (optionnel): ").strip() or None

    # Get password
    while True:
        password = getpass.getpass("Mot de passe: ")
        if len(password) < 6:
            print("❌ Le mot de passe doit contenir au moins 6 caractères")
            continue

        password_confirm = getpass.getpass("Confirmer le mot de passe: ")
        if password != password_confirm:
            print("❌ Les mots de passe ne correspondent pas")
            continue
        break

    # Create user
    user = User(
        username=username,
        email=email,
        is_admin=True,
        is_active=True,
        auth_type='local'
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        print(f"\n✅ Utilisateur administrateur '{username}' créé avec succès!")
        print(f"📧 Email: {email or 'Non défini'}")
        print(f"🔑 Vous pouvez maintenant vous connecter avec ces identifiants\n")
        return 0
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Erreur lors de la création de l'utilisateur: {e}\n")
        return 1


def main():
    """Main function"""
    with app.app_context():
        # Ensure database exists
        db.create_all()

        # Check if any admin users exist
        admin_count = User.query.filter_by(is_admin=True).count()

        if admin_count == 0:
            print("ℹ️  Aucun administrateur n'existe encore.")
        else:
            print(f"ℹ️  Il existe déjà {admin_count} administrateur(s).")

        return create_admin_user()


if __name__ == '__main__':
    sys.exit(main())
