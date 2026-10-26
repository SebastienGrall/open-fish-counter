#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

PACKAGE_NAME="open-fish-counter"
APP_VERSION="1.0.0~alpha1"
ARCHITECTURE="amd64"
PACKAGE_ROOT="${PROJECT_ROOT}/build/deb/${PACKAGE_NAME}_${APP_VERSION}_${ARCHITECTURE}"
OUTPUT_DIR="${PROJECT_ROOT}/packaging/linux/output"
PYINSTALLER_DIST="${PROJECT_ROOT}/dist/OpenFishCounter"

if [[ ! -f "assets/icons/open-fish-counter.svg" ]]; then
    echo "Erreur: assets/icons/open-fish-counter.svg est introuvable." >&2
    exit 1
fi

if [[ ! -f "assets/icons/open-fish-counter-256.png" ]]; then
    echo "Erreur: assets/icons/open-fish-counter-256.png est introuvable." >&2
    exit 1
fi

python -m PyInstaller \
    --noconfirm \
    --clean \
    "packaging/linux/OpenFishCounter-linux.spec"

rm -rf "${PACKAGE_ROOT}"
mkdir -p \
    "${PACKAGE_ROOT}/DEBIAN" \
    "${PACKAGE_ROOT}/opt/open-fish-counter" \
    "${PACKAGE_ROOT}/usr/bin" \
    "${PACKAGE_ROOT}/usr/share/applications" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/256x256/apps" \
    "${OUTPUT_DIR}"

cp -a "${PYINSTALLER_DIST}/." \
    "${PACKAGE_ROOT}/opt/open-fish-counter/"

install -m 0755 /dev/stdin \
    "${PACKAGE_ROOT}/usr/bin/open-fish-counter" <<'LAUNCHER'
#!/usr/bin/env bash
set -e

if [[ -z "${GENICAM_GENTL64_PATH:-}" ]]; then
    DEFAULT_GENTL_PATH="/usr/lib/x86_64-linux-gnu/gentl/tis"

    if [[ -d "${DEFAULT_GENTL_PATH}" ]]; then
        export GENICAM_GENTL64_PATH="${DEFAULT_GENTL_PATH}"
    fi
fi

exec /opt/open-fish-counter/OpenFishCounter "$@"
LAUNCHER

install -m 0644 \
    "packaging/linux/open-fish-counter.desktop" \
    "${PACKAGE_ROOT}/usr/share/applications/open-fish-counter.desktop"

install -m 0644 \
    "assets/icons/open-fish-counter.svg" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps/open-fish-counter.svg"

install -m 0644 \
    "assets/icons/open-fish-counter-256.png" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/256x256/apps/open-fish-counter.png"

cat > "${PACKAGE_ROOT}/DEBIAN/control" <<CONTROL
Package: ${PACKAGE_NAME}
Version: ${APP_VERSION}
Section: science
Priority: optional
Architecture: ${ARCHITECTURE}
Maintainer: Sebastien Grall
Depends: libc6, libgl1, libglib2.0-0, libx11-6, libxcb1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libfreetype6
Recommends: desktop-file-utils, hicolor-icon-theme
Description: Application de videocomptage par detection de mouvement
 Open Fish Counter gere les cameras OpenCV et les cameras industrielles
 The Imaging Source via IC Imaging Control 4. Il enregistre les evenements,
 les metadonnees, les snapshots et les videos decoupees en plusieurs parties.
CONTROL

cat > "${PACKAGE_ROOT}/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

exit 0
POSTINST
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/postinst"

cat > "${PACKAGE_ROOT}/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

exit 0
POSTRM
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/postrm"

find "${PACKAGE_ROOT}" -type d -exec chmod 0755 {} +

dpkg-deb --root-owner-group --build \
    "${PACKAGE_ROOT}" \
    "${OUTPUT_DIR}/${PACKAGE_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"

echo
echo "Paquet cree :"
ls -lh "${OUTPUT_DIR}/${PACKAGE_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"

echo
echo "Verification du paquet :"
dpkg-deb --info "${OUTPUT_DIR}/${PACKAGE_NAME}_${APP_VERSION}_${ARCHITECTURE}.deb"
