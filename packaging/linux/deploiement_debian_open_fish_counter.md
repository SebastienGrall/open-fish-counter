# Déploiement Debian d’Open Fish Counter

Ce document résume la préparation d’un poste Debian/Xfce autonome pour **Open Fish Counter** : connexion automatique, démarrage supervisé, accès à la caméra IC4/GenTL, relance après arrêt et rapport quotidien par e-mail.

> Configuration utilisée dans les exemples :
>
> - utilisateur Linux : `videocomptage`
> - dépôt : `/home/videocomptage/Documents/open-fish-counter`
> - environnement virtuel : `/home/videocomptage/Documents/open-fish-counter/.venv`
> - configuration utilisateur : `/home/videocomptage/.config/open-fish-counter/grid_config.json`
> - vidéos : dossier défini dans les paramètres d’Open Fish Counter

---

## 1. Point important : version de PySide6

Sous Debian avec Python 3.11, **PySide6 6.12.0 provoquait un crash natif** après environ une minute :

```text
Fatal Python error: none_dealloc: deallocating None:
bug likely caused by a refcount error in a C extension
```

La version stable retenue est :

```text
PySide6==6.11.2
```

Dans `requirements.txt` :

```text
PySide6==6.11.2
```

Installation ou rétrogradation :

```bash
source .venv/bin/activate
python -m pip install --force-reinstall "PySide6==6.11.2"
```

Supprimer les extensions 6.12 incompatibles si elles ne sont pas utilisées :

```bash
python -m pip uninstall -y PySide6_Pdf PySide6_WebEngine
python -m pip check
```

Vérification :

```bash
python -m pip list | grep -Ei "pyside|shiboken"
```

Résultat attendu :

```text
PySide6                   6.11.2
PySide6_Addons            6.11.2
PySide6_Essentials        6.11.2
shiboken6                 6.11.2
```

Cette version peut également être utilisée pour la construction de l’exécutable Windows afin de conserver des environnements reproductibles.

---

## 2. Connexion automatique sous Debian/Xfce

Xfce utilise généralement LightDM.

Éditer :

```bash
sudo nano /etc/lightdm/lightdm.conf
```

Dans la section `[Seat:*]` :

```ini
[Seat:*]
autologin-user=videocomptage
autologin-user-timeout=0
```

Tester avec un redémarrage :

```bash
sudo reboot
```

---

## 3. Supervision d’Open Fish Counter avec systemd

Le service utilisateur systemd :

- démarre Open Fish Counter automatiquement ;
- le relance après un crash ;
- le relance également après une fermeture manuelle ;
- centralise les journaux ;
- transmet à IC4 le chemin du producteur GenTL.

### 3.1 Créer le service

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/open-fish-counter.service
```

Contenu :

```ini
[Unit]
Description=Open Fish Counter
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/videocomptage/Documents/open-fish-counter

Environment="DISPLAY=:0.0"
Environment="XDG_SESSION_TYPE=x11"
Environment="GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis"

ExecStartPre=/bin/sleep 10
ExecStart=/home/videocomptage/Documents/open-fish-counter/.venv/bin/python /home/videocomptage/Documents/open-fish-counter/src/main.py

Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### 3.2 Pourquoi `GENICAM_GENTL64_PATH` est indispensable

Le lancement manuel depuis un terminal héritait de :

```text
GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis
```

Le service systemd ne recevait pas cette variable. L’application démarrait, mais affichait :

```text
Aucune caméra IC4 détectée.
```

La ligne suivante corrige le problème :

```ini
Environment="GENICAM_GENTL64_PATH=/usr/lib/x86_64-linux-gnu/gentl/tis"
```

### 3.3 Activer et démarrer

```bash
systemctl --user daemon-reload
systemctl --user enable --now open-fish-counter.service
```

État :

```bash
systemctl --user status open-fish-counter.service
```

Logs en direct :

```bash
journalctl --user -u open-fish-counter.service -f
```

Logs sans troncature :

```bash
journalctl --user -u open-fish-counter.service -n 100 --no-pager -o cat
```

### 3.4 Maintenir les services utilisateur

```bash
sudo loginctl enable-linger videocomptage
```

Vérification :

```bash
loginctl show-user videocomptage --property=Linger
```

Résultat attendu :

```text
Linger=yes
```

### 3.5 Éviter le double lancement

Désactiver l’ancien lancement automatique Xfce afin que systemd soit le seul à lancer le logiciel.

Lister les éléments d’autostart :

```bash
ls -l ~/.config/autostart/
```

Désactiver l’ancien fichier si présent :

```bash
mv ~/.config/autostart/open-fish-counter.desktop \
   ~/.config/autostart/open-fish-counter.desktop.disabled
```

Vérifier qu’une seule instance tourne :

```bash
pgrep -af "src/main.py"
```

### 3.6 Tester la relance automatique

Simuler un arrêt brutal :

```bash
systemctl --user kill --signal=SIGKILL open-fish-counter.service
```

Après environ cinq secondes :

```bash
systemctl --user status open-fish-counter.service
```

Le service doit être de nouveau `active (running)` avec un nouveau PID.

### 3.7 Arrêt volontaire pour maintenance

Avec `Restart=always`, fermer la fenêtre relance l’application. Pour l’arrêter volontairement :

```bash
systemctl --user stop open-fish-counter.service
```

Pour la remettre en route :

```bash
systemctl --user start open-fish-counter.service
```

---

## 4. Rapport quotidien par e-mail

Le rapport est envoyé tous les matins à **08:00** et analyse la **journée civile précédente**.

Exemple :

```text
Mail envoyé le 29/10/2026 à 08:00
Période analysée : 28/10/2026 de 00:00:00 à 23:59:59
```

Il contient notamment :

- le nom de la station lu dans la configuration ;
- le nombre de vidéos créées la veille ;
- le nombre de fichiers JSON créés la veille ;
- la dernière vidéo trouvée ;
- l’espace disque disponible et le taux d’occupation ;
- l’état actuel d’Open Fish Counter ;
- le nombre de redémarrages détectés ;
- le nom de la machine, son système et son uptime.

Le script est compatible Debian et Windows : il ne contient pas de chemin `/home/...` imposé pour la configuration ou le stockage.

### 4.1 Emplacement du script

```text
scripts/daily_report.py
```

Le script doit :

1. trouver automatiquement le dossier de configuration :
   - Debian : `~/.config/open-fish-counter/`
   - Windows : `%LOCALAPPDATA%\OpenFishCounter\`
2. charger `grid_config.json` ;
3. lire `app_config["station"]["name"]` ;
4. lire le dossier d’enregistrement dans la section `recording` ;
5. compter les fichiers dans :

```text
<DossierEnregistrement>/<NomStation>/AAAA-MM-JJ/videos/
```

### 4.2 Configuration Gmail sécurisée

Ne jamais mettre le mot de passe d’application Gmail dans le dépôt Git ou directement dans le script.

Sous Debian :

```bash
mkdir -p ~/.config/open-fish-counter
nano ~/.config/open-fish-counter/mail.env
```

Contenu :

```text
MAIL_FROM=adressedenvoi@gmail.com
MAIL_TO=adressedudestinataire@gmail.com
MAIL_APP_PASSWORD=mot_de_passe_application_gmail
```

Plusieurs destinataires peuvent être séparés par une virgule :

```text
MAIL_TO=adresse1@gmail.com,adresse2@gmail.com
```

Protéger le fichier :

```bash
chmod 600 ~/.config/open-fish-counter/mail.env
```

Vérifier :

```bash
ls -l ~/.config/open-fish-counter/mail.env
```

Les permissions attendues commencent par :

```text
-rw-------
```

Ajouter une protection au `.gitignore` :

```text
mail.env
```

> Ne jamais partager, committer ou copier dans une documentation le véritable mot de passe d’application Gmail/Microsoft.

### 4.3 Tester le rapport sans envoyer de mail

Depuis le dépôt :

```bash
source .venv/bin/activate
python scripts/daily_report.py --preview
```

Contrôler :

- le nom de la station ;
- la date analysée ;
- le dossier d’enregistrement ;
- le nombre de vidéos et JSON ;
- l’espace disque ;
- le statut du service.

### 4.4 Tester un véritable envoi

```bash
python scripts/daily_report.py
```

Résultat attendu :

```text
Rapport envoyé avec succès.
```

---

## 5. Automatiser l’envoi à 08:00

### 5.1 Service d’envoi

```bash
nano ~/.config/systemd/user/open-fish-report.service
```

Contenu :

```ini
[Unit]
Description=Rapport quotidien Open Fish Counter
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/home/videocomptage/Documents/open-fish-counter
ExecStart=/home/videocomptage/Documents/open-fish-counter/.venv/bin/python /home/videocomptage/Documents/open-fish-counter/scripts/daily_report.py
TimeoutStartSec=120
```

### 5.2 Timer quotidien

```bash
nano ~/.config/systemd/user/open-fish-report.timer
```

Contenu :

```ini
[Unit]
Description=Envoi du rapport Open Fish Counter chaque matin à 08h00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
```

`Persistent=true` signifie que si la machine est éteinte à 08:00, le rapport sera lancé au prochain démarrage possible.

### 5.3 Activer le timer

```bash
systemctl --user daemon-reload
systemctl --user enable --now open-fish-report.timer
```

Vérifier :

```bash
systemctl --user status open-fish-report.timer
```

Le statut attendu est :

```text
Active: active (waiting)
```

Voir la prochaine exécution :

```bash
systemctl --user list-timers open-fish-report.timer --all
```

### 5.4 Tester immédiatement le service d’envoi

```bash
systemctl --user start open-fish-report.service
```

Puis :

```bash
systemctl --user status open-fish-report.service
```

Pour un service `oneshot`, le statut suivant après une exécution réussie est normal :

```text
Active: inactive (dead)
status=0/SUCCESS
```

Consulter les journaux :

```bash
journalctl --user \
  -u open-fish-report.service \
  -n 100 \
  --no-pager \
  -o cat
```

### 5.5 Commandes utiles

Déclencher un rapport manuellement :

```bash
systemctl --user start open-fish-report.service
```

Désactiver temporairement les rapports :

```bash
systemctl --user disable --now open-fish-report.timer
```

Réactiver les rapports :

```bash
systemctl --user enable --now open-fish-report.timer
```

Voir tous les timers utilisateur :

```bash
systemctl --user list-timers --all
```

---

## 6. Contrôle complet avant déploiement sur site

Effectuer un redémarrage réel :

```bash
sudo reboot
```

Puis vérifier la chaîne complète :

1. LightDM ouvre automatiquement la session Xfce.
2. Le service attend environ 10 secondes.
3. Open Fish Counter démarre.
4. La caméra IC4/DMK est détectée.
5. Le flux vidéo apparaît.
6. La détection fonctionne.
7. Une séquence crée bien un fichier vidéo et un fichier JSON.
8. Fermer la fenêtre entraîne une relance après environ cinq secondes.
9. `open-fish-report.timer` est `active (waiting)`.
10. Un lancement manuel de `open-fish-report.service` envoie bien le rapport.

Commandes de contrôle rapide :

```bash
systemctl --user status open-fish-counter.service
systemctl --user status open-fish-report.timer
systemctl --user list-timers --all
pgrep -af "src/main.py"
```

Journaux du logiciel :

```bash
journalctl --user -u open-fish-counter.service -n 100 --no-pager -o cat
```

Journaux du rapport :

```bash
journalctl --user -u open-fish-report.service -n 100 --no-pager -o cat
```

---

## 7. Fichiers à sauvegarder ou reproduire sur une nouvelle station

```text
requirements.txt
scripts/daily_report.py
~/.config/systemd/user/open-fish-counter.service
~/.config/systemd/user/open-fish-report.service
~/.config/systemd/user/open-fish-report.timer
~/.config/open-fish-counter/grid_config.json
~/.config/open-fish-counter/mail.env
```

Attention : `mail.env` contient un secret. Il doit être transféré séparément, protégé avec `chmod 600`, et ne doit jamais être ajouté à Git.

Après copie des unités systemd :

```bash
systemctl --user daemon-reload
systemctl --user enable --now open-fish-counter.service
systemctl --user enable --now open-fish-report.timer
sudo loginctl enable-linger videocomptage
```

---

## 8. Résumé de l’architecture

```text
Démarrage Debian
    ↓
Connexion automatique LightDM/Xfce
    ↓
Service utilisateur systemd
    ↓
Open Fish Counter + environnement IC4/GenTL
    ↓
Relance automatique après arrêt ou crash

Chaque jour à 08:00
    ↓
Timer systemd
    ↓
daily_report.py
    ↓
Analyse de la journée civile précédente
    ↓
Rapport Gmail : vidéos, JSON, disque, service et machine
```
