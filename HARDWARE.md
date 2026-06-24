# Hardware

## Physical assembly

The Keybow Mini hat sits on top of the Pi Zero W and connects via the 40-pin GPIO header — pogo pins on the underside of the hat make contact with the Pi's header without soldering. No wires, no connectors beyond the header itself.

## What's connected to what

### Buttons

Each button is a mechanical switch wired to a single GPIO pin, pulled high by the Pi's internal pull-up resistor. Pressing a button pulls the pin low.

| Button index | BCM GPIO | Physical pin |
| ------------ | -------- | ------------ |
| 0 | GPIO 17 | Pin 11 |
| 1 | GPIO 22 | Pin 15 |
| 2 | GPIO 6  | Pin 31 |

Configured as inputs with pull-up resistors (`GPIO.PUD_UP`). A press = pin goes LOW.

### LEDs

Each button has an APA102 RGB LED behind it. APA102 is a two-wire protocol — data and clock — wired to the Pi's hardware SPI bus.

| Signal | BCM GPIO | Physical pin |
| ------ | -------- | ------------ |
| SPI MOSI (data) | GPIO 10 | Pin 19 |
| SPI SCLK (clock) | GPIO 11 | Pin 23 |

SPI bus 0, chip select 0 (`/dev/spidev0.0`). Speed: 1 MHz. Protocol: APA102 (start frame + one 4-byte frame per LED + end frame).

### Power

The hat takes 3.3V and GND from the header. No separate power supply needed.

## What this means for software

- **Buttons**: read GPIO 17, 22, 6 — any GPIO library works (`gpiozero`, `RPi.GPIO`, direct `/sys/class/gpio`)
- **LEDs**: write to `/dev/spidev0.0` — needs `spidev` Python library and SPI enabled in `raspi-config`
- **No i2c, no UART, no special protocol** — just GPIO and SPI

```
Pi Zero W 40-pin header
│
├── Pin 11 (GPIO 17) ──── Button 0
├── Pin 15 (GPIO 22) ──── Button 1
├── Pin 31 (GPIO 6)  ──── Button 2
│
├── Pin 19 (GPIO 10) ──── LED data  (SPI MOSI)
├── Pin 23 (GPIO 11) ──── LED clock (SPI SCLK)
│
├── Pin 17 (3.3V)    ──── Power
└── Pin 6  (GND)     ──── Ground
```

## Dependencies

| Package | Source | Notes |
| ------- | ------ | ----- |
| `RPi.GPIO` or `gpiozero` | pre-installed on Pi OS | buttons |
| `spidev` | `apt install python3-spidev` | LEDs |
| `paho-mqtt` | `pip install paho-mqtt` | MQTT |

SPI must be enabled: `raspi-config` → Interface Options → SPI → Enable.
