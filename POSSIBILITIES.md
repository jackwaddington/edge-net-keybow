# What's logically possible

This document maps out the interaction space of the keybow node — not what it does today, but what the hardware and protocol make possible. Use this when deciding what to build next.

## Button events

The current code only fires on `press`. The keybow library also supports:

| Event | Description |
| ----- | ----------- |
| `press` | Button down |
| `release` | Button up |
| `hold` | Button held for N seconds |
| `double_tap` | Two presses within a short window |

Publishing different payloads per event lets the network distinguish intent. A tap could mean "next", a hold could mean "reset", a double-tap could mean "confirm".

## LED as signal, not just decoration

Because the network can set LED colours independently of button presses, the buttons become indicators as well as triggers. Possible states a lit button could communicate:

| LED state | What it could mean |
| --------- | ------------------ |
| Off | Idle / nothing to report |
| Solid colour | Something is active or waiting |
| Colour = severity | Green = fine, amber = attention, red = critical |
| Lit before a press | "There is something for you to acknowledge" |
| Lit after a press | "Your action was received / is in progress" |
| Animated pattern | See below |

The network lights a button up; you press it to acknowledge; the network turns it off. That's a complete human-in-the-loop interaction with just MQTT and three buttons.

## Local state: what the keybow knows that the network doesn't

The keybow holds no application state — that lives on the network. But there is one thing only the keybow knows: **whether it's connected to MQTT**.

This is genuine local knowledge and worth expressing visually. Rather than alarming colours, subtle animations that say "something is slightly off" without screaming:

| State | LED behaviour |
| ----- | ------------- |
| Connected, idle | All off (dark = ready, waiting) |
| Connecting / no broker yet | Slow blue breathe across all three buttons |
| Lost connection (was connected, now isn't) | Slow warm white pulse, like a heartbeat looking for something |
| Boot sequence in progress | Gentle rainbow sweep, then settles to dark once connected |

The principle: connected and idle should be invisible. Only disconnection should be noticeable, and only just.

## Interaction patterns

### Attention + acknowledge

The network detects something (build failed, timer expired, device went offline). It lights a button. You press it. The network turns it off and does something.

### Mode switching

One button per mode. The network lights the currently active mode's button. Pressing a dark button switches to that mode and the network updates the LEDs to match.

### Cycle forward / back / confirm

Button 0 = previous, Button 2 = next, Button 1 = select/confirm. Lets three buttons navigate an arbitrarily long list. The display (if connected) shows the current item.

### Scene control

Each button triggers a "scene" — a coordinated state change across multiple nodes at once. Lights change, displays update, music shifts. One press, whole network responds.

### Status dashboard

All three LEDs are always lit, each one representing a different system or service. Colour = health. No pressing needed; it's a passive at-a-glance panel.

## Party mode: detected chaos

If a kid (or anyone) starts randomly mashing buttons, the keybow can detect that locally — rapid presses with no clear pattern, buttons in quick succession, no pause. When that threshold is crossed:

1. **Local**: LEDs go into a light show — fast colour cycling, random per-button colours, responsive to each press with a burst of colour
2. **Network**: publish `edge-net/keybow/event/party` — every other node on Edge-NET gets the message and does whatever it can to join in

This is the first example of the keybow inferring a *condition* from raw input rather than just forwarding events. It's not "button 2 was pressed" — it's "something is happening here." The network can choose to respond or ignore it.

The threshold for party mode is tunable: N presses within M seconds across any combination of buttons.

## AI layer: making sense of ambiguous input

Once you have a stream of button events — timing, sequence, which buttons, hold durations — you have data. An AI layer could sit between the raw events and the MQTT output and decide what they mean:

- Random mashing with no pattern → party mode (or just curiosity)
- Repeated single button → frustration, something isn't working
- Deliberate slow presses → intentional navigation
- Long hold followed by release → a considered action, not an accident

The AI doesn't need to run on the Pi — it can run anywhere on Edge-NET. The Pi publishes raw events with full timing data, an AI node subscribes, classifies the pattern, and publishes a semantic interpretation back. The keybow then lights up based on what the AI decided the interaction meant.

This adds generative randomness too: the AI can decide to respond with something unexpected, or inject variety into the light patterns, or decide that this sequence of presses means it's time to do something surprising. The keybow becomes an input to a system that can genuinely react rather than just map button → action.

## What the Pi Zero adds beyond the buttons

The device runs full Linux, so it can do things a microcontroller can't:

- **Run a local process** — scrape an API, watch a file, ping a host — and light a button based on the result
- **Drive a display** via HDMI — the buttons become controls for whatever's on screen
- **Connect USB peripherals** — a barcode scanner, serial device, USB audio
- **SSH access** — change what the buttons do without touching the hardware

## What needs to be built to unlock this

| Capability | What's needed |
| ---------- | ------------- |
| Hold / double-tap events | Update `main.py` to publish different payloads |
| LED patterns (breathe, sweep, burst) | A local animation loop running alongside the MQTT loop |
| Connection state indicator | On-connect / on-disconnect callbacks driving LED animations |
| Acknowledgement flow | Convention: network lights button, press turns it off |
| Party mode detection | Local press counter with a rolling time window |
| AI interpretation layer | Separate node subscribing to raw events, publishing semantic ones |
| Display output | HDMI display + something to render to it |
