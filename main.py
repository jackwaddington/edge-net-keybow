import keybow
import paho.mqtt.client as mqtt
import config

# --- MQTT ---

def on_connect(client, userdata, flags, rc):
    print(f"Connected to broker (rc={rc})")
    for i in range(3):
        client.subscribe(config.TOPIC_LED.format(i))
        print(f"Subscribed to {config.TOPIC_LED.format(i)}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip()
    for i in range(3):
        if topic == config.TOPIC_LED.format(i):
            try:
                r, g, b = (int(x) for x in payload.split(","))
                keybow.set_led(i, r, g, b)
                keybow.show()
            except ValueError:
                print(f"Bad LED payload: {payload}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(config.BROKER, config.PORT)
client.loop_start()

# --- Keybow ---

keybow.setup(keybow.MINI)

@keybow.on_press()
def on_press(index):
    topic = config.TOPIC_BUTTON.format(index)
    client.publish(topic, "press")
    print(f"Button {index} → {topic}")

# --- Main loop ---

while True:
    keybow.update()
