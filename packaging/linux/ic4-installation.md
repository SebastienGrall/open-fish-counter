# Installation IC4 pour les caméras The Imaging Source

## Prérequis

- Linux x86_64
- Adaptateur Ethernet Gigabit
- Caméra et PC sur le même sous-réseau
- GenTL Producer GigE Vision de The Imaging Source
- Environnement virtuel Python du projet

## Réseau utilisé lors des tests

- Caméra : `192.168.1.100`
- PC : `192.168.1.10/24`
- Liaison : `1000 Mb/s Full Duplex`

Vérifier la connectivité avec la caméra :

```bash
ping -c 4 192.168.1.100
```

Vérifier que la route vers la caméra utilise bien l’adaptateur Ethernet Gigabit :

```bash
ip route get 192.168.1.100
```

Identifier les interfaces réseau :

```bash
ip -br link
```

Vérifier le débit réseau en remplaçant `NOM_INTERFACE` par le nom réel de l’interface :

```bash
sudo ethtool NOM_INTERFACE
```

Le résultat doit notamment indiquer :

```text
Speed: 1000Mb/s
Duplex: Full
Link detected: yes
```

## Installation du GenTL Producer

Télécharger le paquet Linux x86_64 du GenTL Producer GigE Vision depuis le site de The Imaging Source.

Se placer dans le dossier contenant le paquet téléchargé.

Afficher le nom du paquet :

```bash
ls ic4-gentl-driver-
```

Compléter le nom du fichier avec la touche Tab, puis installer le paquet :

```bash
sudo apt install ./NOM_DU_PAQUET_IC4.deb
```

Vérifier que le fichier GenTL est présent :

```bash
ls -l /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Chemin attendu :

```text
/usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

## Variable d’environnement GenTL

Définir la variable dans le terminal courant :

```bash
export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis
```

Vérifier la variable :

```bash
printenv GENICAM_GENTL64_PATH
```

Résultat attendu :

```text
/usr/lib/x86_64-linux-gnu/gentl/tis
```

Pour rendre la variable persistante pour l’utilisateur courant :

```bash
echo 'export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis' >> ~/.bashrc
source ~/.bashrc
```

Vérifier de nouveau :

```bash
printenv GENICAM_GENTL64_PATH
```

Attention : un futur raccourci graphique ou service systemd ne chargera pas nécessairement le fichier `~/.bashrc`. Le lanceur définitif devra donc également définir cette variable d’environnement.

## Installation de l’API Python IC4

Se placer à la racine du projet :

```bash
cd ~/open-fish-counter
```

Créer l’environnement virtuel s’il n’existe pas encore :

```bash
python3 -m venv .venv
```

Activer l’environnement virtuel :

```bash
source .venv/bin/activate
```

Mettre pip à jour :

```bash
python -m pip install --upgrade pip
```

Installer les dépendances de l’application avec le support IC4 :

```bash
pip install -r requirements-ic4.txt
```

Vérifier l’import de la bibliothèque Python IC4 :

```bash
python -c "import imagingcontrol4; print('IC4 importé avec succès')"
```

## Test d’énumération de la caméra

Avec l’environnement virtuel activé :

```bash
python tests/test_ic4_camera.py
```

La caméra DMK doit apparaître avec :

- son modèle ;
- son numéro de série ;
- son identifiant unique.

Exemple de résultat attendu :

```text
1 caméra(s) IC4 détectée(s) :

[0] modèle=DMK 33GX287
    série=...
    identifiant=...
```

## Diagnostic

Si aucun fournisseur GenTL n’est détecté, vérifier d’abord la variable :

```bash
printenv GENICAM_GENTL64_PATH
```

Vérifier ensuite les dépendances du fichier GenTL :

```bash
ldd /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti
```

Pour afficher uniquement les éventuelles dépendances manquantes :

```bash
ldd /usr/lib/x86_64-linux-gnu/gentl/tis/libic4-gentl-gev.cti | grep "not found"
```

Si cette commande ne renvoie rien, aucune dépendance directe n’est signalée comme manquante.

Pour exécuter explicitement le test avec le chemin GenTL :

```bash
GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis python tests/test_ic4_camera.py
```

## Diagnostic réseau

Vérifier que la caméra répond :

```bash
ping -c 4 192.168.1.100
```

Vérifier l’état du lien Ethernet :

```bash
sudo ethtool NOM_INTERFACE
```

Si le résultat indique `Link detected: no` :

- vérifier le câble Ethernet ;
- vérifier le switch ;
- vérifier l’alimentation de la caméra ;
- vérifier que l’interface réseau est active.

Afficher l’état de l’interface :

```bash
ip link show NOM_INTERFACE
```

## Lancement d’Open Fish Counter

Avec l’environnement virtuel activé et la variable GenTL définie :

```bash
python src/main.py
```
