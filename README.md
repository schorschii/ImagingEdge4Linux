# ImagingEdge4Linux

## Preamble
So, here we go again. Thought I would do some vacation, but forgot the micro USB cable for my Sony camera (and no SD card reader was in sight too). Too bad if you want to view your images on your notebook from your cool WiFi-enabled DSLR. Sony thought: "TAKE THAT, Linux users! We do not implement a simple web interface for downloading the images via network which could be used easily across all operating systems; we do our own proprietary protocol, because we can. And we implement this protocol in a mobile app which behaves as annoying as possible. Let's call it Playmemories Mobile, and rename it later to Imaging Edge Mobile."

I wasn't very amused about that - ImagingEdge4Linux was born.

## Introduction
This project tries to reverse engineer and implement the SOAP API (XML over HTTP) offered by Sony DSLR cameras for image download to mobile devices using the app "Imaging Edge Mobile" (camera menu "Send to Smartphone"). In contrast to the PTP/IP implementation (camera menu "Send to computer"), which is already reverse-engineered in [sony-pm-alt](https://github.com/falk0069/sony-pm-alt), the SOAP API seems to be less complex to set up (no PTP-GUID etc.) and easier to use.

## Installation
Make sure you have the `python3-gi` package installed in your Linux distribution, e.g. via `apt install python3-gi`.

## Usage
1. Select "Send to Smartphone" in the menu of your Sony camera (**not** "Send to Computer")
2. Connect your computer to the WiFi access point of the camera
3. Execute the python script: `python3 imaging-edge.py`. All images will be copied to your computer. Already copied files will be skipped.
   - Normally, the camera is available at 192.168.122.1:64321, but you can adjust this by the `--address` and `--port` parameter.
   - By default, the images will be downloaded into your personal images folder. You can adjust this using the `--output-dir` directory.
   - You can add this script to your autostart with the `--daemon` parameter. The script will then run in the background and automatically copy the images. A desktop notification will inform you about the progress.

The script downloads the best available quality automatically, which is the original, unmodified image in case of JPEG. Note that the API does not allow to download RAW files. Instead of the RAW file, a compressed JPEG will be downloaded.

You can automate the WiFi connection using the `autoconnect.sh` script. Set your camera wifi credentials in `SSID` and `PASSWORD`, then run `./autoconnect.sh`. It will reconnect to your previous network after completion.

## Reverse Engineering
The camera shows which web services it offers in `http://192.168.122.1:64321/DmsDescPush.xml`. This for example leads to `http://192.168.122.1:64321/XPlsDesc.xml`, showing which commands it understands for transfer control. While the commands TransferStart and TransferEnd are working, TransferProgress does nothing on my camera.

## Tests
Feedback, stars and contributions welcome! Please tell me if your camera is working too.

|       Model       | Working? |
| ----------------- | -------- |
| ILCA-77M2 (v2.00) | Yes      |
| ILCE-7S           | Yes      |
| ILCE-6400         | Yes      |
| ILCE-6600         | Yes      |
| DSC-HX90V         | Yes      |
| DSC-RX100-M3      | Yes      |
| DSC-RX100-M7      | Yes      |
| DSC-WX300         | Yes      |
| RX10 IV           | Yes      |
