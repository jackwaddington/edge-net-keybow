import time
import threading
import colorsys
import math
import json
import hardware
import paho.mqtt.client as mqtt
import config

# --- Connection breathing ---

connected = False
breathing_thread = None
breathing_lock = threading.Lock()


def start_breathing():
    global breathing_thread
    with breathing_lock:
        t = threading.Thread(target=run_breathing, daemon=True)
        breathing_thread = t
        t.start()


def run_breathing():
    start = time.time()
    while True:
        with breathing_lock:
            if connected or party_active:
                break
        elapsed = time.time() - start
        # Sine wave: 0..1..0 over 3 seconds
        brightness = (math.sin(elapsed * math.pi * 2 / 3) + 1) / 2
        brightness = brightness ** 2  # ease in — subtle, not punchy
        v = int(brightness * 40)      # dim blue, not bright
        for i in range(3):
            hardware.set_led(i, 0, 0, v)
        hardware.show()
        time.sleep(0.05)
    all_leds_off()


# --- Party mode ---

PARTY_TRIGGER_COUNT = 4
PARTY_TRIGGER_WINDOW = 3.0
PARTY_DURATION = 10.0

press_times = []
party_active = False
party_deadline = 0.0
party_lock = threading.Lock()


def start_or_extend_party():
    global party_active, party_deadline
    with party_lock:
        party_deadline = time.time() + PARTY_DURATION
        if not party_active:
            party_active = True
            client.publish(config.TOPIC_PARTY, "start")
            threading.Thread(target=run_party, daemon=True).start()


def stop_party():
    global party_active
    with party_lock:
        party_active = False
    all_leds_off()
    client.publish(config.TOPIC_PARTY, "stop")


def run_party():
    hue = 0.0
    while True:
        with party_lock:
            if not party_active or time.time() > party_deadline:
                party_active = False
                break
        hue = (hue + 0.05) % 1.0
        for i in range(3):
            r, g, b = colorsys.hsv_to_rgb((hue + i * 0.33) % 1.0, 1.0, 1.0)
            hardware.set_led(i, int(r * 255), int(g * 255), int(b * 255))
        hardware.show()
        time.sleep(0.05)
    all_leds_off()


def all_leds_off():
    for i in range(3):
        hardware.set_led(i, 0, 0, 0)
    hardware.show()


def record_press():
    now = time.time()
    press_times.append(now)
    cutoff = now - PARTY_TRIGGER_WINDOW
    while press_times and press_times[0] < cutoff:
        press_times.pop(0)
    return len(press_times) >= PARTY_TRIGGER_COUNT


# --- MQTT ---

def on_connect(client, userdata, flags, rc):
    global connected
    msg = f"Connected to broker (rc={rc})\n"
    print(msg, flush=True)
    with open("/tmp/keybow_debug.log", "a") as f:
        f.write(msg)
    connected = True
    for i in range(3):
        client.subscribe(config.TOPIC_LED.format(i))
        msg = f"Subscribed to {config.TOPIC_LED.format(i)}\n"
        print(msg, flush=True)
        with open("/tmp/keybow_debug.log", "a") as f:
            f.write(msg)

def on_disconnect(client, userdata, rc):
    global connected
    print(f"Disconnected from broker (rc={rc})")
    connected = False
    if not party_active:
        start_breathing()

def on_message(client, userdata, msg):
    if party_active:
        return
    topic = msg.topic
    payload = msg.payload.decode().strip()
    msg_text = f"on_message: topic={topic}, payload={payload}\n"
    print(msg_text, flush=True)
    with open("/tmp/keybow_debug.log", "a") as f:
        f.write(msg_text)
    for i in range(3):
        if topic == config.TOPIC_LED.format(i):
            try:
                # Support both JSON {"rgb": [r, g, b]} and comma-separated "r,g,b"
                if payload.startswith("{"):
                    data = json.loads(payload)
                    r, g, b = data.get("rgb", [0, 0, 0])
                else:
                    r, g, b = (int(x) for x in payload.split(","))
                led_msg = f"Setting LED {i} to RGB({r},{g},{b})\n"
                print(led_msg, flush=True)
                with open("/tmp/keybow_debug.log", "a") as f:
                    f.write(led_msg)
                hardware.set_led(i, r, g, b)
                hardware.show()
            except (ValueError, json.JSONDecodeError) as e:
                err_msg = f"Bad LED payload: {payload} - {e}\n"
                print(err_msg, flush=True)
                with open("/tmp/keybow_debug.log", "a") as f:
                    f.write(err_msg)

client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

hardware.setup()
start_breathing()  # breathe until connected
# connect_async + loop_start: keep retrying in the background and auto-reconnect
# after drops, instead of crashing on a single failed attempt. The Pi Zero's
# WiFi to the AP is flaky, so the node must survive blips, not die on them.
client.reconnect_delay_set(min_delay=1, max_delay=20)
client.connect_async(config.BROKER, config.PORT)
client.loop_start()

# --- Button handling ---

def on_press(index):
    if party_active:
        stop_party()
        return

    if record_press():
        start_or_extend_party()
        return

    topic = config.TOPIC_BUTTON.format(index)
    client.publish(topic, "press")
    print(f"Button {index} → {topic}")

hardware.on_press(on_press)

# --- Main loop ---

while True:
    time.sleep(1)
