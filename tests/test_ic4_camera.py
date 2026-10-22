import imagingcontrol4 as ic4


def main():
    ic4.Library.init()

    devices = ic4.DeviceEnum.devices()

    if not devices:
        print("Aucune caméra IC4 détectée.")
        return

    print(f"{len(devices)} caméra(s) IC4 détectée(s) :")

    for index, device in enumerate(devices):
        print(
            f"[{index}] "
            f"modèle={device.model_name} | "
            f"série={device.serial} | "
            f"identifiant={device.unique_name}"
        )


if __name__ == "__main__":
    main()



#1 caméra(s) IC4 détectée(s) :
#[0] modèle=DMK 33GX287 | série=09620071 | identifiant=The Imaging Source Europe GmbH-ic4-gentl-gev-09620071
