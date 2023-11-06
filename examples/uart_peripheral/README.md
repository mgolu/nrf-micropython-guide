# Nordic UART Service peripheral

This example shows how to run the BLE Nordic UART Service (NUS) peripheral on the device.

## Running the program

You can install the file in the filesystem and run it from REPL, or you can use `mpremote` to run it from a command line:

    mpremote <device> run ble_uart_peripheral.py

- Use a mobile App that connects to the NUS. There are many Apps that do that. For example, you can use the [nRF Toolbox](https://www.nordicsemi.com/Products/Development-tools/nrf-toolbox) and select the Nordic UART application. 
- Connect to the device called `mpy-uart` and observe the numbers 4, 8, 15, 16, 23, 42 print out in sequence. Send text using the App and observe it come out the USB serial port.
