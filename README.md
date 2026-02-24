# edge-net-keybow

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pi Zero with a Keybow 3-key hat — three physical buttons that publish MQTT messages to the broker on the hub. Other nodes on the network subscribe to those messages and react.

## Hardware

- [Raspberry Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)
- [Keybow Mini](https://shop.pimoroni.com/products/keybow-mini-3-key-macro-pad-kit) (three programmable buttons)

The Keybow was designed as a USB HID macro pad — a Pi Zero running a full OS just to emulate a keyboard. Since its release, cheap microcontrollers have made USB HID trivial without needing an OS. What remains compelling here is the Pi Zero itself: it runs full Linux, is SSH-accessible over the Edge-NET WiFi, and can be updated without physical access.

## What it does

Each button is mapped to an MQTT topic. Pressing a button publishes a message, which other nodes can subscribe to and act on:

- Change what pattern the Plasma Stick displays
- Update what's shown on the GFX display
- Trigger other actions on the network

## Software

Python on Raspberry Pi OS. The Pi Zero is SSH-accessible over the Edge-NET WiFi, so code can be updated without physical access.

## MQTT topics

| Button | Topic | Message | Effect |
| ------ | ----- | ------- | ------ |
| 1 | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD |

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
