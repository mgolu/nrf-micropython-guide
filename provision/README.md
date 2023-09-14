# Provisioning Wi-Fi details over BLE

This sample implements Nordic's [Wi-Fi Provisioning Service](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/bluetooth_services/services/wifi_prov.html#) in MicroPython.

You can use the nRF Wi-Fi Provisioner apps to interact with the device and install
Wi-Fi credentials on it. The apps are available for [Android](https://play.google.com/store/apps/details?id=no.nordicsemi.android.wifi.provisioning) and [iOS](https://apps.apple.com/us/app/nrf-wi-fi-provisioner/id1638948698).

## Installation

The sample uses the `bisect` library, and a modified version of the `minipb` library. The modified
version of `minipb` is provided here. You can either download `bisect` from micropython-lib, or use
`mpi` to install it. For example:

    $ mpremote mip --target '/flash' install bisect
    $ mpremote cp minipb.py :minipb.py
    $ mpremote cp provisioning.py :provisioning.py

## Running the program

You can run `provisioning.py` directly, and it will start the BLE advertisements. Use a phone with 
the nRF Wi-Fi Provisioner app and follow the instructions on the app.
