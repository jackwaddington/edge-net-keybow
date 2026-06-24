# edge-net-keybow

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pi Zero with a Keybow 3-key hat — three physical buttons with RGB LEDs that participate in the MQTT network.

## Hardware

- [Raspberry Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)
- [Keybow Mini](https://shop.pimoroni.com/products/keybow-mini-3-key-macro-pad-kit) (three buttons, each with an RGB LED)
- Mini HDMI port (can drive a display)
- USB port (can connect peripherals)

The Keybow was designed as a USB HID macro pad — a Pi Zero running a full OS just to emulate a keyboard. Since its release, cheap microcontrollers have made USB HID trivial without needing an OS. What remains compelling here is the Pi Zero itself: it runs full Linux, is SSH-accessible over the Edge-NET WiFi, and can be updated without physical access.

## What it does

**Sends** — pressing a button publishes to MQTT:

| Button | Topic | Payload |
| ------ | ----- | ------- |
| 0 | `edge-net/keybow/button/0` | `press` |
| 1 | `edge-net/keybow/button/1` | `press` |
| 2 | `edge-net/keybow/button/2` | `press` |

**Receives** — the network can control each button's LED colour:

| Topic | Payload | Effect |
| ----- | ------- | ------ |
| `edge-net/keybow/led/0` | `r,g,b` | Set button 0 LED colour |
| `edge-net/keybow/led/1` | `r,g,b` | Set button 1 LED colour |
| `edge-net/keybow/led/2` | `r,g,b` | Set button 2 LED colour |

This two-way relationship is the interesting part: other nodes can light up a button to signal something needs attention, and a press sends the response.

See [POSSIBILITIES.md](POSSIBILITIES.md) for what this interaction model can grow into.

## Auto-start

To run on boot via systemd:

```bash
sudo nano /etc/systemd/system/keybow.service
```

```ini
[Unit]
Description=Keybow MQTT node
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/edge-net-keybow/main.py
WorkingDirectory=/home/pi/edge-net-keybow
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable keybow
sudo systemctl start keybow
```

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
