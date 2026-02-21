# edge-net-keybow

A node in [edge-net](https://github.com/jackwaddington/edge-net). A Pi Zero with a Keybow 3-key hat — three physical buttons that publish MQTT messages to the broker on the hub. Other nodes on the network subscribe to those messages and react.

## Hardware

- Raspberry Pi Zero
- Keybow 3-key hat (three programmable buttons)

## What it does

Each button is mapped to an MQTT topic. Pressing a button publishes a message, which other nodes can subscribe to and act on:

- Change what pattern the Plasma Stick displays
- Update what's shown on the GFX display
- Trigger other actions on the network

## Software

Python on Raspberry Pi OS. The Pi Zero is SSH-accessible over the edge-net WiFi, so code can be updated without physical access.

## MQTT topics

| Button | Topic | Message | Effect |
| ------ | ----- | ------- | ------ |
| 1 | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD |

## Part of edge-net

See [edge-net](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
