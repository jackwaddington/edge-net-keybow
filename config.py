BROKER = "10.1.1.1"
PORT   = 1883

# Topics this node publishes to
TOPIC_BUTTON = "edge-net/keybow/button/{}"   # .format(index)
TOPIC_LAMP   = "edge-net/keybow/lamp"        # retained JSON {"rgb": [r, g, b]}
