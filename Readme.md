
# media_manager

**media_manager** est une solution logicielle dédiée à la gestion et à l'analyse de flux vidéo en temps réel, intégrant des fonctionnalités avancées telles que la détection d'objets, le suivi d'objets, la gestion de caméras RealSense, et la configuration via des fichiers texte. Ce projet est conçu pour être utilisé dans des environnements de production nécessitant une surveillance vidéo efficace et flexible.

## Fonctionnalités principales

- Détection d'objets en temps réel.
- Suivi d'objets à travers les images successives.
- Intégration avec les caméras Intel RealSense pour la capture vidéo et de profondeur.
- Configuration flexible via fichiers texte et JSON.
- Intégration avec `systemd` pour une gestion facile du service.

## Structure du dépôt

- `Primary_Detector/` : Module principal de détection d'objets.
- `realsense_examples/` : Exemples d’utilisation des caméras RealSense.
- `systemd/` : Fichiers pour l’intégration avec systemd.
- Scripts Python clés :
  - `color_depth.py`
  - `detect_camera.py`
  - `distance_objetc_finder.py`
  - `multi_rs.py`
  - `object_finder.py`
  - `realsense_plugin.py`
  - `rs_helpers.py`
  - `rs_pipeline.py`
  - `rs_track.py`
  - `tracker_finder.py`
- Fichiers de configuration :
  - `tracker_config.txt`
  - `tracker_perf.yml`
  - `test.json`
- Script d’installation de la bibliothèque `libuvc_installation.sh`
- Fichier de logs : `media_manager.log`

## Prérequis

- Python 3.6 ou supérieur
- NVIDIA GPU (recommandé pour traitement accéléré)
- Caméra Intel RealSense compatible
- Bibliothèques Python suivantes (exemple d’installation via pip) :
  ```bash
  pip install pyrealsense2 opencv-python numpy pyyaml
  ```
- Installation de `libuvc` via le script fourni.

## Installation

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/toutia/media_manager.git
   cd media_manager
   ```

2. Installer les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```

3. Installer `libuvc` :
   ```bash
   ./libuvc_installation.sh
   ```

4. Recharger les règles udev pour détecter les caméras :
   ```bash
   sudo udevadm control --reload-rules
   ```

## Utilisation

- Lancer le gestionnaire principal :
  ```bash
  python3 media_manager.py
  ```

- Pour lancer un script spécifique, par exemple la détection caméra :
  ```bash
  python3 detect_camera.py
  ```

- Pour gérer le service avec systemd :
  ```bash
  sudo cp systemd/media_manager.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable media_manager
  sudo systemctl start media_manager
  ```

## Configuration

Personnalisez les fichiers de configuration avant utilisation :

- `tracker_config.txt` : paramètres du tracker.
- `tracker_perf.yml` : paramètres des performances du tracker.
- `test.json` : paramètres pour tests spécifiques.

## Logs

Les logs du service sont enregistrés dans `media_manager.log`. Consultez ce fichier pour le diagnostic et le suivi.

## Contribution

Les contributions sont les bienvenues. Merci de respecter les bonnes pratiques (pull requests, documentation, tests).

## Licence

Ce projet est sous licence Apache-2.0. Voir le fichier LICENSE pour plus de détails.
