# Installation IC4 pour les caméras The Imaging Source

## Prérequis

- Linux x86_64
- Adaptateur Ethernet Gigabit
- Caméra et PC sur le même sous-réseau
- GenTL Producer GigE Vision de The Imaging Source

## Réseau utilisé lors des tests

- Caméra : 192.168.1.100
- PC : 192.168.1.10/24
- Liaison : 1000 Mb/s Full Duplex

## Installation du GenTL Producer

Télécharger le paquet Linux x86_64 depuis le site The Imaging Source.

Installer le paquet :

```bash
sudo apt install ./ic4-gentl-driver-*.deb

Le fichier GenTL attendu est :
/usr/lib/x86_64-lin*x-gnu/gentl/tis/libic4-gentl-gev.cti

## Variable d'environnement

Ajouter dans ~/.bashrc :
export GENICAM_GENTL64_PATH=/usr*lib/x86_64-linux-gnu/gentl/tis
```*

Puis recharger :
*rintenv GENICAM_GENTL64_PATH

## Installation de l'API Python

Depuis l'environnement virtuel du projet :
pip install*-r requirements-ic4.txt

## Test d'énumération
python tests/test_ic4_camera.py

La DMK doit apparaître avec son modèle, son numéro de série et son identifiant unique.