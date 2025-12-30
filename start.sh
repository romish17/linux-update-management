#!/bin/bash

echo "🐧 Linux Update Manager - Installation"
echo "======================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

echo "✓ Python 3 détecté: $(python3 --version)"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
    echo "✓ Environnement virtuel créé"
fi

# Activate venv
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Install dependencies
echo "📥 Installation des dépendances..."
pip install -q -r requirements.txt
echo "✓ Dépendances installées"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Création du fichier .env..."
    cp .env.example .env
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
    echo "✓ Fichier .env créé avec une clé secrète générée"
fi

# Create data directory
mkdir -p data

echo ""
echo "✅ Installation terminée !"
echo ""
echo "🚀 Démarrage de l'application..."
echo "   L'application sera accessible sur http://localhost:5000"
echo ""
echo "   Pour arrêter l'application, appuyez sur Ctrl+C"
echo ""

# Start application
python app.py
