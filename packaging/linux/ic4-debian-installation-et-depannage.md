# Installation et dépannage IC4 / IC Capture sous Debian

Ce document résume l’installation et le diagnostic des caméras GigE Vision The Imaging Source avec IC Imaging Control 4 sous Debian, notamment pour les modèles DMK 33GX287.

## 1. Prérequis

- Debian Linux x86_64
- Adaptateur Ethernet Gigabit
- Caméra et PC sur un sous-réseau compatible
- GenTL Producer GigE Vision de The Imaging Source
- Bibliothèque Python `imagingcontrol4`
- Environnement virtuel Python du projet Open Fish Counter

## 2. Exemple de configuration réseau

Configuration utilisée lors des premiers tests :

- PC Ethernet : `192.168.1.10/24`
- Première caméra : `192.168.1.100/24`
- Deuxième caméra : `192.168.1.101/24`
- Masque : `255.255.255.0`
- Liaison : `1000 Mb/s Full Duplex`

Chaque caméra doit avoir une adresse IP unique.

Il est préférable d’éviter d’utiliser le même sous-réseau pour le Wi-Fi et le réseau caméra. Par exemple :

- Wi-Fi : `192.168.1.0/24`
- PC Ethernet caméra : `192.168.50.10/24`
- Première caméra : `192.168.50.100/24`
- Deuxième caméra : `192.168.50.101/24`

Cela évite les routes concurrentes entre le Wi-Fi et l’adaptateur Ethernet.

## 3. Vérification du réseau

Afficher les interfaces et leurs adresses :

```bash
ip -br address
```

Afficher les routes :

```bash
ip route
```

Vérifier la route vers une caméra :

```bash
ip route get 192.168.1.100
```

La sortie doit indiquer l’interface Ethernet reliée à la caméra, par exemple :

```text
dev enx00e04c68028a src 192.168.1.10
```

Vérifier la liaison Gigabit, en remplaçant `NOM_INTERFACE` par le nom réel :

```bash
sudo ethtool NOM_INTERFACE
```

Le résultat doit notamment indiquer :

```text
Speed: 1000Mb/s
Duplex: Full
Link detected: yes
```

Tester la connectivité :

```bash
ping -c 4 192.168.1.100
```

### Désactiver temporairement le Wi-Fi

Si le Wi-Fi et l’Ethernet utilisent le même sous-réseau, couper temporairement le Wi-Fi pour les tests :

```bash
nmcli radio wifi off
```

Pour le réactiver :

```bash
nmcli radio wifi on
```

## 4. Installation du GenTL Producer

Installer le paquet Debian téléchargé depuis The Imaging Source :

```bash
sudo apt install ./NOM_DU_PAQUET_IC4.deb
```

Le nom du paquet installé peut être vérifié avec :

```bash
dpkg -l | grep -Ei 'ic4|gentl|imaging'
```

Dans l’installation testée, le paquet est :

```text
ic4-gentl-driver-gigevision
```

Vérifier le fichier GenTL :

```bash
ls -l /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Identifier le paquet propriétaire du fichier :

```bash
dpkg -S /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Résultat attendu :

```text
ic4-gentl-driver-gigevision: /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Vérifier les dépendances du fichier GenTL :

```bash
ldd /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Afficher uniquement les dépendances manquantes :

```bash
ldd /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti | grep "not found"
```

Si cette commande ne renvoie rien, aucune dépendance directe n’est signalée comme manquante.

## 5. Variable d’environnement GenTL

Définir la variable dans le terminal courant :

```bash
export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis
```

Vérifier sa valeur :

```bash
printenv GENICAM_GENTL64_PATH
```

Résultat attendu :

```text
/usr/lib/x86_64-linux-gnu/gentl/tis
```

Pour la rendre persistante dans les terminaux Bash :

```bash
echo 'export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis' >> ~/.bashrc
source ~/.bashrc
```

Attention : une application lancée depuis le menu graphique ne charge pas nécessairement `~/.bashrc`. Il faut donc définir la variable dans le lanceur de l’application ou dans un script intermédiaire.

## 6. Installation de l’API Python IC4

Depuis la racine du projet :

```bash
cd ~/Documents/open-fish-counter
```

Créer l’environnement virtuel s’il n’existe pas :

```bash
python3 -m venv .venv
```

L’activer :

```bash
source .venv/bin/activate
```

Mettre pip à jour :

```bash
python -m pip install --upgrade pip
```

Installer les dépendances IC4 :

```bash
python -m pip install -r requirements-ic4.txt
```

Le fichier `requirements-ic4.txt` doit contenir une ligne valide, par exemple :

```text
imagingcontrol4>=1.5,<2
```

Vérifier l’import :

```bash
python -c "import imagingcontrol4; print('IC4 importé avec succès')"
```

## 7. Tests IC4 du projet

### Énumération des caméras

```bash
python tests/test_ic4_camera.py
```

Exemple de sortie :

```text
1 caméra(s) IC4 détectée(s) :
[0] modèle=DMK 33GX287 | série=09620068 | identifiant=The Imaging Source Europe GmbH-ic4-gentl-gev-09620068
```

Une même caméra peut apparaître plusieurs fois si elle est découverte par plusieurs interfaces réseau. Open Fish Counter dédoublonne les appareils par numéro de série.

### Test du flux

```bash
python tests/test_ic4_stream.py --serial 09620068
```

La touche `Q` ou `Échap` ferme la fenêtre de test.

Pour forcer explicitement le chemin GenTL :

```bash
GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis python tests/test_ic4_stream.py --serial 09620068
```

## 8. Caméra détectée mais inaccessible

Le message suivant indique généralement un problème d’adresse IP ou de sous-réseau :

```text
Failed to open unreachable device
```

La découverte GigE peut trouver une caméra même si son adresse IP n’est pas compatible avec l’interface Ethernet du PC.

Vérifications à effectuer :

1. La caméra et le PC doivent utiliser le même sous-réseau.
2. Chaque caméra doit avoir une adresse IP unique.
3. La route doit utiliser l’interface Ethernet Gigabit.
4. Le lien doit être à `1000 Mb/s Full Duplex`.
5. Le Wi-Fi ne doit pas créer une route concurrente vers le même sous-réseau.
6. Aucune autre application ne doit déjà contrôler la caméra.

Exemple de configuration valide :

```text
PC Ethernet       192.168.1.10/24
DMK série 09620071 192.168.1.100/24
DMK série 09620068 192.168.1.101/24
```

## 9. Installation et lancement d’IC Capture sous Linux

IC Capture 4 existe pour Linux amd64 sous forme d’archive `tar.gz`.

Après installation ou extraction, IC Capture peut afficher :

```text
No IC4 GenTL Producers being installed
```

alors que le GenTL Producer est bien présent. La cause est généralement que l’application graphique ne reçoit pas la variable `GENICAM_GENTL64_PATH`.

### Test depuis le terminal

Définir la variable puis lancer IC Capture dans le même terminal :

```bash
export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis
ic-capture
```

Si la commande `ic-capture` n’est pas trouvée, rechercher l’exécutable :

```bash
find /opt /usr/local /usr "$HOME"   -type f   -iname '*ic*capture*'   -executable   2>/dev/null
```

Puis lancer avec son chemin complet :

```bash
GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis /chemin/reel/vers/ic-capture
```

## 10. Créer un lanceur permanent pour IC Capture

Remplacer `/CHEMIN/REEL/VERS/IC-CAPTURE` par le chemin réellement trouvé :

```bash
sudo tee /usr/local/bin/ic-capture-with-gentl >/dev/null <<'EOF'
#!/usr/bin/env bash
set -e

export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis

exec /CHEMIN/REEL/VERS/IC-CAPTURE "$@"
EOF
```

Rendre le lanceur exécutable :

```bash
sudo chmod 755 /usr/local/bin/ic-capture-with-gentl
```

Lancer IC Capture avec :

```bash
ic-capture-with-gentl
```

## 11. Lanceur Open Fish Counter installé par le paquet Debian

Le paquet Debian d’Open Fish Counter installe un lanceur dans :

```text
/usr/bin/open-fish-counter
```

Ce lanceur définit automatiquement `GENICAM_GENTL64_PATH` si le dossier GenTL existe :

```bash
#!/usr/bin/env bash
set -e

if [[ -z "${GENICAM_GENTL64_PATH:-}" ]]; then
    DEFAULT_GENTL_PATH="/usr/lib/x86_64-linux-gnu/gentl/tis"

    if [[ -d "${DEFAULT_GENTL_PATH}" ]]; then
        export GENICAM_GENTL64_PATH="${DEFAULT_GENTL_PATH}"
    fi
fi

exec /opt/open-fish-counter/OpenFishCounter "$@"
```

Cela permet à Open Fish Counter de trouver le GenTL Producer même lorsqu’il est lancé depuis le menu graphique XFCE.

## 12. Dépannage rapide

### Aucun GenTL Producer détecté

```bash
printenv GENICAM_GENTL64_PATH
ls -l /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
ldd /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti | grep "not found"
```

### Caméra visible mais inaccessible

```bash
ip -br address
ip route
ip route get ADRESSE_IP_CAMERA
sudo ethtool NOM_INTERFACE
ping -c 4 ADRESSE_IP_CAMERA
```

### Interfaces Wi-Fi et Ethernet sur le même sous-réseau

```bash
nmcli radio wifi off
python tests/test_ic4_stream.py --serial NUMERO_DE_SERIE
nmcli radio wifi on
```

### Vérifier le paquet GenTL installé

```bash
dpkg -l | grep -Ei 'ic4|gentl|imaging'
```

### Vérifier le fichier CTI et son paquet

```bash
dpkg -S /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

## 13. Configuration recommandée pour une station autonome

- Utiliser une interface Ethernet Gigabit dédiée aux caméras.
- Utiliser un sous-réseau caméra distinct du Wi-Fi.
- Attribuer une IP fixe unique à chaque caméra.
- Identifier les caméras dans Open Fish Counter par leur numéro de série.
- Définir `GENICAM_GENTL64_PATH` dans les lanceurs graphiques et les services.
- Conserver les tests `test_ic4_camera.py` et `test_ic4_stream.py` dans le dépôt Git.
- Vérifier le flux après toute mise à jour du GenTL Producer, d’IC4, de Debian, de NumPy ou d’OpenCV.
