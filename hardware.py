import spidev
from gpiozero import Button

BUTTON_PINS = [6, 22, 17]  # outer pins swapped so button index matches LED index

_leds = [(0, 0, 0)] * 3
_spi = None
_buttons = []


def setup():
    global _spi, _buttons
    try:
        _spi = spidev.SpiDev()
        _spi.open(0, 0)
        _spi.max_speed_hz = 1_000_000
    except Exception as e:
        print(f"Warning: SPI setup failed: {e}")
        _spi = None

    try:
        _buttons = [Button(pin, pull_up=True, bounce_time=0.05) for pin in BUTTON_PINS]
    except Exception as e:
        print(f"Warning: Button setup failed (GPIO not available?): {e}")
        _buttons = []


def set_led(index, r, g, b):
    _leds[index] = (r, g, b)


def show():
    if _spi is None:
        return  # SPI not available, skip
    buf = [0x00, 0x00, 0x00, 0x00]          # APA102 start frame
    for r, g, b in _leds:
        buf += [0xFF, b, g, r]              # full brightness, B G R order
    buf += [0xFF, 0xFF, 0xFF, 0xFF]         # end frame
    _spi.xfer2(buf)


def on_press(callback):
    if not _buttons:
        return  # No buttons available, skip
    def make_handler(index):
        return lambda: callback(index)
    for i, button in enumerate(_buttons):
        button.when_pressed = make_handler(i)


def on_release(callback):
    if not _buttons:
        return  # No buttons available, skip
    def make_handler(index):
        return lambda: callback(index)
    for i, button in enumerate(_buttons):
        button.when_released = make_handler(i)
