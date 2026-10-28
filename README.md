<h1>
  Open Fish Counter
  <img
    src="assets/icons/open-fish-counter-256.png"
    alt="Logo Open Fish Counter"
    width="48"
    align="right"
  >
</h1>


Open Fish Counter est une application de vidéocomptage destinée à surveiller automatiquement une zone filmée, détecter les mouvements et enregistrer les événements vidéo associés.

Le logiciel fonctionne sous Windows et Debian avec :

- les webcams et caméras compatibles OpenCV ;
- les caméras industrielles The Imaging Source compatibles IC Imaging Control 4, notamment les caméras DMK GigE Vision.

> État du projet : version alpha. Le logiciel est fonctionnel, mais il doit encore être validé dans des conditions de terrain représentatives avant un déploiement en production.

## Fonctionnalités principales

### Acquisition vidéo

- prise en charge des webcams via OpenCV ;
- prise en charge des caméras The Imaging Source via IC4 ;
- sélection des caméras IC4 par numéro de série ;
- dédoublonnage des caméras GigE détectées sur plusieurs interfaces réseau ;
- reconnexion automatique après une perte de caméra ;
- configuration de la résolution et de la fréquence d’acquisition ;
- réglage de l’exposition automatique ou manuelle pour les caméras IC4 ;
- réglage du gain automatique ou manuel pour les caméras IC4.

### Détection de mouvement

- découpage de l’image en grille configurable ;
- activation ou désactivation individuelle des cellules ;
- seuil de mouvement configurable pour chaque cellule ;
- seuil global de variation des pixels ;
- confirmation d’un événement après plusieurs images consécutives ;
- délai configurable avant la fin d’un événement ;
- affichage en temps réel des cellules déclenchées et du mouvement maximal.

### Enregistrement vidéo

- démarrage automatique d’un enregistrement lorsqu’un événement est confirmé ;
- pré-buffer configurable afin de conserver les images précédant la détection ;
- estimation de la fréquence réelle à partir du pré-buffer ;
- enregistrement MP4 ;
- arrêt propre de l’enregistrement à la fin de l’événement ;
- finalisation automatique de la vidéo lorsque l’application est fermée ou que la caméra est perdue.

### Découpage des événements longs

La durée maximale d’un fichier vidéo est configurable. Lorsqu’un événement dépasse cette durée, Open Fish Counter ouvre automatiquement une nouvelle partie sans interrompre l’événement logique.

Exemple :

```text
Station_14-00-00-123_part001.mp4
Station_14-00-00-123_part001.json
Station_14-00-00-123_part002.mp4
Station_14-00-00-123_part002.json
Station_14-00-00-123_event.json
```

Toutes les parties partagent un identifiant d’événement commun. Le manifeste `event.json` décrit l’événement complet et liste les vidéos dans l’ordre. Cette structure est prévue pour permettre leur regroupement dans un futur logiciel de dépouillement.

### Métadonnées

Pour chaque partie vidéo, un fichier JSON contient notamment :

- l’identifiant de l’événement ;
- le numéro de la partie ;
- le nombre total de parties ;
- les dates de début et de fin ;
- le nombre d’images ;
- la fréquence d’enregistrement ;
- la résolution ;
- les indicateurs de continuité avec les parties précédente et suivante.

Un manifeste JSON global est également créé pour chaque événement.

### Banque d’images

- création facultative d’un snapshot par événement ;
- sélection de l’image présentant le niveau de mouvement maximal ;
- enregistrement du snapshot dans un dossier dédié.

### Surveillance du stockage

- affichage du pourcentage d’occupation du disque d’enregistrement ;
- affichage de l’espace disponible ;
- seuil d’avertissement configurable ;
- seuil critique configurable ;
- finalisation de la vidéo en cours lorsque le seuil critique est atteint ;
- blocage des nouveaux enregistrements tant que l’espace disque reste insuffisant ;
- reprise automatique lorsque suffisamment d’espace est à nouveau disponible.

### Configuration et journalisation

- fenêtre de paramètres avec défilement pour les petits écrans ;
- sauvegarde de la configuration dans le dossier utilisateur ;
- migration d’une ancienne configuration du projet ;
- chemins compatibles Windows et Linux ;
- journalisation des opérations et des erreurs ;
- conservation de la configuration et des vidéos lors d’une désinstallation.

## Plateformes prises en charge

### Windows

- Windows 10 ou Windows 11 64 bits ;
- exécutable construit avec PyInstaller ;
- installateur construit avec Inno Setup ;
- configuration utilisateur dans :

```text
%LOCALAPPDATA%\OpenFishCounter\grid_config.json
```

### Debian Linux

- Debian x86_64 avec environnement graphique ;
- paquet `.deb` ;
- entrée dans le menu des applications ;
- configuration utilisateur dans :

```text
~/.config/open-fish-counter/grid_config.json
```

## Installation depuis les sources

### Préparation générale

```bash
git clone https://github.com/SebastienGrall/open-fish-counter.git
cd open-fish-counter
python3 -m venv .venv
```

Sous Debian :

```bash
source .venv/bin/activate
```

Sous Windows PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances principales :

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Pour le support IC4 :

```bash
python -m pip install -r requirements-ic4.txt
```

Lancer l’application :

```bash
python src/main.py
```

## Caméras The Imaging Source et IC4

Le paquet Python `imagingcontrol4` ne suffit pas à lui seul. Le GenTL Producer correspondant au type de caméra doit également être installé.

Pour les caméras DMK GigE Vision, installer le GenTL Producer GigE Vision fourni par The Imaging Source.

Sous Debian, le chemin utilisé lors des tests est :

```text
/usr/lib/x86_64-linux-gnu/gentl/tis
```

La variable suivante peut être nécessaire :

```bash
export GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis
```

Une documentation détaillée est disponible dans :

```text
packaging/linux/ic4-debian-installation-et-depannage.md
packaging/linux/ic4-installation.md
packaging/linux/deploiement_debian_open_fish_counter.md

```

## Tests caméra

Énumérer les caméras IC4 :

```bash
python tests/test_ic4_camera.py
```

Tester le flux d’une caméra IC4 :

```bash
python tests/test_ic4_stream.py --serial NUMERO_DE_SERIE
```

## Construction Windows

Construire l’application et l’installateur :

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windowsuild-installer.ps1
```

L’installateur est généré dans :

```text
packaging/windows/output/
```

## Construction du paquet Debian

```bash
chmod +x packaging/linux/build-deb.sh
./packaging/linux/build-deb.sh
```

Le paquet est généré dans :

```text
packaging/linux/output/
```

Installation locale :

```bash
sudo apt install ./packaging/linux/output/open-fish-counter_*.deb
```

## Organisation des enregistrements

```text
Dossier racine/
└── Nom_de_la_station/
    └── AAAA-MM-JJ/
        ├── videos/
        │   ├── evenement_part001.mp4
        │   ├── evenement_part001.json
        │   └── evenement_event.json
        └── snapshots/
            └── evenement_max_motion.jpg
```

## Avertissements

- Le logiciel est en version alpha.
- La détection repose actuellement sur des variations de pixels et doit être réglée selon la scène, l’éclairage et la caméra.
- Les automatismes d’exposition et de gain peuvent provoquer des variations globales de luminosité et influencer la détection.
- Les caméras GigE doivent utiliser des adresses IP uniques et un sous-réseau compatible avec l’interface Ethernet du PC.
- Il est recommandé d’utiliser un réseau caméra distinct du Wi-Fi.
- Le projet ne remplace pas une validation scientifique ou réglementaire du protocole de comptage.

## Licence

Copyright © Sébastien Grall.

Le code propre à Open Fish Counter est distribué sous la licence **PolyForm Noncommercial 1.0.0**.

Cette licence autorise notamment l’utilisation, l’étude, la modification et la redistribution du logiciel pour des finalités non commerciales, sous réserve du respect de ses conditions.

Toute vente, intégration dans une offre commerciale, prestation commerciale, exploitation commerciale ou utilisation dans un produit ou service commercial nécessite une autorisation écrite distincte du titulaire des droits.

Consultez le fichier [`LICENSE`](LICENSE) pour le texte complet de la licence.

Les bibliothèques, pilotes et composants tiers conservent leurs propres licences. Cela concerne notamment Python, PySide6, OpenCV, NumPy, PyInstaller, IC Imaging Control 4 et le GenTL Producer de The Imaging Source.

### Demande d’autorisation commerciale

Pour demander une autorisation ou une licence commerciale, ouvrez une issue dans le dépôt ou contactez le titulaire des droits par le moyen indiqué dans le profil du dépôt.

## Contribution

Les rapports de bugs et propositions d’amélioration sont les bienvenus via les issues du dépôt.

Avant de proposer une modification importante :

1. ouvrir une issue décrivant le besoin ;
2. préciser le système utilisé, la caméra, le backend et les étapes de reproduction ;
3. éviter d’inclure des vidéos, chemins, numéros de série ou données sensibles sans les anonymiser.

## Auteur

Projet développé par Sébastien Grall.
