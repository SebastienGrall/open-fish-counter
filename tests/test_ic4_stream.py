#!/usr/bin/env python3
"""Test minimal du flux IC4 avec affichage OpenCV.

Ce script :
- enumere les cameras IC4 ;
- dedoublonne les detections par numero de serie ;
- ouvre la camera demandee ;
- affiche le flux avec OpenCV ;
- calcule une estimation du nombre d'images par seconde ;
- ferme proprement le flux avec Q ou Echap.

Exemples :
    python tests/test_ic4_stream.py
    python tests/test_ic4_stream.py --serial 09620071
    python tests/test_ic4_stream.py --timeout 2000
"""

from __future__ import annotations

import argparse
import sys
import time

import cv2
import imagingcontrol4 as ic4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teste l'acquisition et l'affichage d'un flux video IC4."
    )
    parser.add_argument(
        "--serial",
        help="Numero de serie de la camera a ouvrir. Sans cette option, la premiere camera unique est utilisee.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=2000,
        help="Delai maximal d'attente d'une image, en millisecondes (defaut : 2000).",
    )
    return parser.parse_args()


def unique_devices_by_serial() -> list[ic4.DeviceInfo]:
    """Retourne les cameras IC4 dedoublonnees par numero de serie."""
    unique_devices: dict[str, ic4.DeviceInfo] = {}

    for device in ic4.DeviceEnum.devices():
        serial = str(device.serial).strip()
        key = serial or str(device.unique_name)
        unique_devices.setdefault(key, device)

    return list(unique_devices.values())


def select_device(
    devices: list[ic4.DeviceInfo], requested_serial: str | None
) -> ic4.DeviceInfo:
    if not devices:
        raise RuntimeError("Aucune camera IC4 detectee.")

    if requested_serial:
        for device in devices:
            if str(device.serial).strip() == requested_serial:
                return device
        available = ", ".join(str(device.serial) for device in devices)
        raise RuntimeError(
            f"Camera de serie {requested_serial} introuvable. "
            f"Series disponibles : {available}"
        )

    return devices[0]


def run_stream(device: ic4.DeviceInfo, timeout_ms: int) -> None:
    grabber = ic4.Grabber()
    sink = ic4.SnapSink()
    stream_started = False
    window_name = f"IC4 - {device.model_name} - {device.serial}"

    try:
        print(
            f"Ouverture : modele={device.model_name} | "
            f"serie={device.serial} | identifiant={device.unique_name}"
        )
        grabber.device_open(device)

        grabber.stream_setup(
            sink,
            setup_option=ic4.StreamSetupOption.ACQUISITION_START,
        )
        stream_started = True

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        print("Flux demarre. Appuyer sur Q ou Echap pour quitter.")

        frame_count = 0
        fps_started_at = time.monotonic()
        last_fps = 0.0
        first_frame = True

        while True:
            buffer = sink.snap_single(timeout_ms)

            # numpy_wrap() pointe vers la memoire du buffer IC4.
            # copy() rend l'image independante avant l'iteration suivante.
            frame = buffer.numpy_wrap().copy()

            if first_frame:
                print(
                    f"Premiere image recue : shape={frame.shape} | "
                    f"dtype={frame.dtype} | type IC4={buffer.image_type}"
                )
                first_frame = False

            frame_count += 1
            elapsed = time.monotonic() - fps_started_at
            if elapsed >= 1.0:
                last_fps = frame_count / elapsed
                frame_count = 0
                fps_started_at = time.monotonic()

            display_frame = frame.copy()
            cv2.putText(
                display_frame,
                f"{last_fps:.1f} FPS",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                255 if display_frame.ndim == 2 else (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break

    finally:
        if stream_started:
            grabber.stream_stop()
        cv2.destroyAllWindows()


def main() -> int:
    args = parse_args()

    if args.timeout <= 0:
        print("Erreur : --timeout doit etre strictement positif.", file=sys.stderr)
        return 2

    ic4.Library.init(
        api_log_level=ic4.LogLevel.INFO,
        log_targets=ic4.LogTarget.STDERR,
    )

    try:
        devices = unique_devices_by_serial()
        print(f"{len(devices)} camera(s) IC4 unique(s) detectee(s) :")
        for index, device in enumerate(devices):
            print(
                f"[{index}] modele={device.model_name} | "
                f"serie={device.serial} | identifiant={device.unique_name}"
            )

        device = select_device(devices, args.serial)
        run_stream(device, args.timeout)
        return 0

    except ic4.IC4Exception as error:
        message = getattr(error, "message", str(error))
        print(f"Erreur IC4 : {message}", file=sys.stderr)
        return 1
    except (RuntimeError, cv2.error) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        return 130
    finally:
        ic4.Library.exit()


if __name__ == "__main__":
    raise SystemExit(main())
