BROKER = "10.1.1.1"
PORT   = 1883

# Topics this node publishes to
TOPIC_BUTTON = "edge-net/keybow/button/{}"   # .format(index)

# Topics this node subscribes to
TOPIC_LED    = "edge-net/keybow/led/{}"      # .format(index)

# Events this node publishes
TOPIC_PARTY  = "edge-net/keybow/event/party"

# Mode control this node subscribes to — payload "on"/"off". Default off.
# The node owns what the rainbow *is*; the bus only says whether it's allowed.
TOPIC_PARTY_MODE = "edge-net/keybow/mode/party"
