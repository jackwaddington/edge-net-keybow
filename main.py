import time
import threading
import math
import json
import hardware
import paho.mqtt.client as mqtt
import config
from colour_mix import ColourMixEngine, rainbow_colour_at

# --- Connection breathing ---

connected = False
breathing_lock = threading.Lock()


def start_breathing():
    t = threading.Thread(target=run_breathing, daemon=True)
    t.start()


def run_breathing():
    start = time.time()
    while True:
        with breathing_lock:
            if connected:
                break
        elapsed = time.time() - start
        brightness = (math.sin(elapsed * math.pi * 2 / 3) + 1) / 2
        brightness = brightness ** 2
        v = int(brightness * 40)
        for i in range(3):
            hardware.set_led(i, 0, 0, v)
        hardware.show()
        time.sleep(0.05)
    refresh_key_leds()


def refresh_key_leds():
    for i in range(3):
        r, g, b = engine.key_colour(i)
        hardware.set_led(i, r, g, b)
    hardware.show()


# --- Colour-mix engine ---

def on_lamp_change(rgb):
    r, g, b = rgb
    client.publish(config.TOPIC_LAMP, json.dumps({"rgb": [r, g, b]}), retain=True)
    refresh_key_leds()


engine = ColourMixEngine(on_change=on_lamp_change)


# --- MQTT ---

def on_connect(c, userdata, flags, rc):
    global connected
    print(f"Connected to broker (rc={rc})", flush=True)
    connected = True
    r, g, b = engine.lamp_colour
    client.publish(config.TOPIC_LAMP, json.dumps({"rgb": [r, g, b]}), retain=True)
    refresh_key_leds()


def on_disconnect(c, userdata, rc):
    global connected
    print(f"Disconnected from broker (rc={rc})", flush=True)
    connected = False
    start_breathing()


client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect

hardware.setup()
start_breathing()
client.reconnect_delay_set(min_delay=1, max_delay=20)
client.connect_async(config.BROKER, config.PORT)
client.loop_start()


# --- Button handling ---

def on_press(index):
    engine.on_key_down(index)
    refresh_key_leds()
    client.publish(config.TOPIC_BUTTON.format(index), "press")
    print(f"Button {index} ↓", flush=True)


def on_release(index):
    engine.on_key_up(index)
    refresh_key_leds()
    client.publish(config.TOPIC_BUTTON.format(index), "release")
    print(f"Button {index} ↑  lamp={engine.lamp_colour}", flush=True)


hardware.on_press(on_press)
hardware.on_release(on_release)


# --- Main loop ---

while True:
    now = time.monotonic()
    engine.tick(now=now)
    if engine.is_mashing:
        r, g, b = rainbow_colour_at(now)
        client.publish(config.TOPIC_LAMP, json.dumps({"rgb": [r, g, b]}))
        refresh_key_leds()
    time.sleep(0.05)
