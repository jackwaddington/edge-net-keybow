"""
Keybow colour-mix logic — reference implementation
=====================================================

WHAT THIS IS
-------------
A small, dependency-free state machine for a 3-key Keybow (red, green, blue)
feeding a single RGB lamp. This file contains ONLY the decision logic —
"given this button event, what should the lamp now show, and what should
each key's own LED show?" It deliberately has no GPIO, no MQTT, no hardware
calls at all, so it can be tested and verified on its own before anyone
wires it into the real Keybow / MQTT setup.

Drop this into the Pi Zero project and call `on_key_down(i)` / `on_key_up(i)`
from the real Keybow button callbacks. Use the return values (or read
`engine.lamp_colour` / `engine.key_colour(i)` directly) to drive:
  - the key's own LED (set it to `engine.key_colour(i)`)
  - an MQTT publish of the lamp colour (publish `engine.lamp_colour` on
    every change — see the `on_change` hook below)

THE RULES (confirmed in conversation, in order)
-------------------------------------------------
1. Each key has an "in mix" flag — persistent, not just "currently held".
   - Key idle, not in mix  -> key LED shows its own colour (red/green/blue).
   - Key in mix            -> key LED is dark/off (it's "given" its colour
                               to the lamp), even after you let go of it.

2. Pressing a key DOWN previews what release will do:
   - If held alone and it's NOT yet in the mix -> key goes dark while held
     (a preview of "this colour is about to leave the key and go to the
     lamp").
   - If held alone and it IS already in the mix -> key lights back up to
     its own colour while held (a preview of "this colour is about to come
     back out of the mix").
   - If 2 or 3 keys are held down AT THE SAME TIME, all of the currently
     held keys preview the LIVE SUM of what the mix would become if every
     held key's toggle went through right now. (E.g. holding red+blue
     together previews magenta on both keys, even if neither was in the
     mix yet.)

3. Releasing a key TOGGLES its own "in mix" membership independently:
   - Not in mix -> release adds it to the mix.
   - In mix     -> release removes it from the mix.
   The lamp is always just "the additive RGB sum of every key currently
   flagged in-mix". Each release recomputes this sum and that's what gets
   sent to the lamp.
   NOTE: this means each key's release is independent — there is no
   "group" logic needed for what gets SENT. The group/live-preview in
   rule 2 is purely a *visual* preview while keys are still held down;
   the actual mix-membership toggle happens per-key, on that key's own
   release.

4. Three down -> white (since red+green+blue in the mix = full RGB).
   Three down again (i.e. toggling red, green, and blue each back out,
   one release at a time) -> back to off. This falls out naturally from
   rule 3 — no special-casing needed.

5. MASH DETECTION (deliberately simple per the latest direction):
   any messy burst of MANY presses across MULTIPLE different keys in a
   short window means the user is mashing (e.g. a kid pressing keys
   indiscriminately) -> lamp shows a continuous rainbow fade instead of
   the normal mix, for as long as the mashing continues, settling back
   to the last real mix colour once presses stop for a bit.
   This intentionally does NOT try to distinguish different combos with
   different themed effects — one rainbow response covers all mashing.

WHAT IS *NOT* IN HERE
-----------------------
- GPIO / Keybow hardware calls (use the `pimoroni-keybow` library's own
  button callbacks to call into `on_key_down` / `on_key_up` below).
- MQTT publish/subscribe calls. Hook in via the `on_change` callback
  passed into `ColourMixEngine` — call your `mqtt_client.publish(...)`
  from inside that callback whenever `engine.lamp_colour` changes.
- Any animation/rendering — `rainbow_colour_at(t)` returns a single RGB
  sample for a given timestamp; call it on your own animation loop /
  timer at whatever frame rate your LED strip needs, only while
  `engine.is_mashing` is True.
"""

import time


# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------

OFF   = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE  = (0, 0, 255)

BASE_COLOURS = [RED, GREEN, BLUE]  # index 0/1/2 = key 0/1/2


def mix(colours):
    """Additive RGB sum of a list of (r,g,b) tuples, clamped to 255."""
    r = min(255, sum(c[0] for c in colours))
    g = min(255, sum(c[1] for c in colours))
    b = min(255, sum(c[2] for c in colours))
    return (r, g, b)


def hsl_to_rgb(h, s, l):
    """h in [0,360), s and l in [0,1]. Returns (r,g,b) ints 0-255."""
    h = h / 360.0

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)
    return (round(r * 255), round(g * 255), round(b * 255))


def rainbow_colour_at(t_seconds):
    """One sample of the mash rainbow fade, for a given time in seconds.
    Call this from your own LED-refresh loop while engine.is_mashing."""
    hue = (t_seconds * 60) % 360  # full hue cycle every 6 seconds — tune to taste
    return hsl_to_rgb(hue, 1.0, 0.5)


# ---------------------------------------------------------------------------
# Mash (chaotic multi-key spam) detector
# ---------------------------------------------------------------------------

class MashDetector:
    """
    Watches a rolling window of key-down events. If enough presses land
    across enough distinct keys in a short enough window, flags "mashing".
    Mashing clears itself automatically after a period of no presses.

    Tune the four constants below if real-world testing shows it's too
    sensitive (fires on deliberate testing) or not sensitive enough
    (doesn't fire on genuine chaotic mashing).
    """

    WINDOW_SECONDS = 1.2     # look at presses within this rolling window
    MIN_PRESSES = 10         # need at least this many presses...
    MIN_DISTINCT_KEYS = 2    # ...across at least this many different keys
    COOLDOWN_SECONDS = 1.5   # no presses for this long -> mashing ends

    def __init__(self):
        self._log = []          # list of (key_index, timestamp)
        self.is_mashing = False
        self._last_press_time = 0.0

    def register_press(self, key_index, now=None):
        """Call this on every key-down (not key-up). Returns True if this
        press caused mashing to START (useful if you want a one-shot
        trigger), but you should generally just read `self.is_mashing`
        after calling this."""
        now = now if now is not None else time.monotonic()
        self._last_press_time = now
        self._log.append((key_index, now))
        self._log = [(k, t) for (k, t) in self._log if now - t <= self.WINDOW_SECONDS]

        distinct_keys = {k for k, _ in self._log}
        started = False
        if (not self.is_mashing
                and len(self._log) >= self.MIN_PRESSES
                and len(distinct_keys) >= self.MIN_DISTINCT_KEYS):
            self.is_mashing = True
            started = True
        return started

    def tick(self, now=None):
        """Call this periodically (e.g. once per main-loop iteration) so
        mashing can time out even if no new presses arrive. Returns True
        if this call caused mashing to END."""
        if not self.is_mashing:
            return False
        now = now if now is not None else time.monotonic()
        if now - self._last_press_time >= self.COOLDOWN_SECONDS:
            self.is_mashing = False
            self._log = []
            return True
        return False


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class ColourMixEngine:
    """
    Call on_key_down(i) / on_key_up(i) for i in {0, 1, 2} from your real
    Keybow button callbacks. Read `self.lamp_colour` (or use the
    on_change callback) to know what to send to the lamp / publish over
    MQTT. Read `self.key_colour(i)` to know what each key's own LED
    should show right now.
    """

    def __init__(self, on_change=None):
        """
        on_change: optional callback `fn(lamp_rgb: tuple)` called every
        time the lamp's target colour changes (on release-toggle, or on
        mash start/end). This is where you'd hook your MQTT publish, e.g.:

            def publish_lamp(rgb):
                r, g, b = rgb
                mqtt_client.publish("keybow/lamp", f"{r},{g},{b}")

            engine = ColourMixEngine(on_change=publish_lamp)
        """
        self.held = [False, False, False]      # is the key physically down right now
        self.in_mix = [False, False, False]    # is this key's colour currently in the lamp mix
        self.lamp_colour = OFF
        self._on_change = on_change
        self.mash = MashDetector()

    # -- internal helpers ---------------------------------------------------

    def _current_mix(self):
        return mix([BASE_COLOURS[i] for i in range(3) if self.in_mix[i]])

    def _set_lamp(self, rgb):
        if rgb != self.lamp_colour:
            self.lamp_colour = rgb
            if self._on_change:
                self._on_change(rgb)

    # -- public API -----------------------------------------------------

    @property
    def is_mashing(self):
        return self.mash.is_mashing

    def key_colour(self, i):
        """What key i's own LED should show RIGHT NOW. Call this after
        on_key_down/on_key_up (or any time) to refresh that key's LED."""
        if self.is_mashing:
            # During a mash, key LEDs are not meaningful — dim/off is fine,
            # since the lamp itself is doing the rainbow. Adjust to taste.
            return OFF

        held_indices = [j for j in range(3) if self.held[j]]

        if not self.held[i]:
            # At rest: lit if not in the mix, dark if it's currently contributing.
            return OFF if self.in_mix[i] else BASE_COLOURS[i]

        if len(held_indices) >= 2:
            # 2+ keys held together: preview the live sum they'd produce on release.
            projected = []
            for j in range(3):
                will_be_in = (not self.in_mix[j]) if self.held[j] else self.in_mix[j]
                if will_be_in:
                    projected.append(BASE_COLOURS[j])
            return mix(projected)

        # Single key held alone: preview what IT alone will become on release.
        return BASE_COLOURS[i] if self.in_mix[i] else OFF

    def on_key_down(self, i, now=None):
        """Call from your Keybow button-down callback, i in {0,1,2}."""
        now = now if now is not None else time.monotonic()

        mash_started = self.mash.register_press(i, now=now)
        if mash_started:
            self._set_lamp(self.lamp_colour)  # no-op colour change, just to fire on_change if you want a "mash started" hook
        if self.is_mashing:
            return  # mash owns the lamp; ignore normal toggle logic while it's active

        self.held[i] = True

    def on_key_up(self, i, now=None):
        """Call from your Keybow button-up callback, i in {0,1,2}."""
        # Always clear the physical held-flag, even mid-mash, so it doesn't
        # get stuck once mashing ends.
        was_held = self.held[i]
        self.held[i] = False

        if self.is_mashing:
            return  # mash owns the lamp; this release doesn't toggle the mix

        if not was_held:
            return  # shouldn't normally happen, but guard against stray events

        self.in_mix[i] = not self.in_mix[i]
        self._set_lamp(self._current_mix())

    def tick(self, now=None):
        """Call this once per loop iteration (e.g. every 20-50ms) so the
        mash detector can time out even with no new key events, and so
        the lamp settles back to the real mix colour when mashing ends."""
        now = now if now is not None else time.monotonic()
        mash_ended = self.mash.tick(now=now)
        if mash_ended:
            self._set_lamp(self._current_mix())


# ---------------------------------------------------------------------------
# Self-test — run this file directly to see the rules verified end-to-end.
# This is NOT the hardware integration; it's a sanity check of the logic.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    events = []
    engine = ColourMixEngine(on_change=lambda rgb: events.append(rgb))

    def press(i):
        engine.on_key_down(i)
        print(f"  key {i} DOWN  -> key_colour={engine.key_colour(i)}")

    def release(i):
        engine.on_key_up(i)
        print(f"  key {i} UP    -> lamp={engine.lamp_colour}  key_colour={engine.key_colour(i)}")

    print("== Single key: red alone ==")
    press(0); release(0)
    assert engine.lamp_colour == RED, engine.lamp_colour
    assert engine.key_colour(0) == OFF, "red key should be dark once in mix"

    print("\n== Add green: should become yellow ==")
    press(1); release(1)
    assert engine.lamp_colour == (255, 255, 0), engine.lamp_colour
    assert engine.key_colour(0) == OFF and engine.key_colour(1) == OFF

    print("\n== Add blue: should become white ==")
    press(2); release(2)
    assert engine.lamp_colour == (255, 255, 255), engine.lamp_colour

    print("\n== Toggle red back out: should drop to cyan (green+blue) ==")
    press(0); release(0)
    assert engine.lamp_colour == (0, 255, 255), engine.lamp_colour
    assert engine.key_colour(0) == RED, "red key should be lit again, it's out of the mix"

    print("\n== Toggle green and blue out too: should reach OFF ==")
    press(1); release(1)
    press(2); release(2)
    assert engine.lamp_colour == OFF, engine.lamp_colour

    print("\n== Hold two keys together: live preview before release ==")
    engine.on_key_down(0)
    engine.on_key_down(2)
    preview0 = engine.key_colour(0)
    preview2 = engine.key_colour(2)
    print(f"  holding red+blue -> preview on both keys: {preview0}, {preview2}")
    assert preview0 == (255, 0, 255) and preview2 == (255, 0, 255), "should preview magenta on both"
    engine.on_key_up(0)
    engine.on_key_up(2)
    assert engine.lamp_colour == (255, 0, 255), engine.lamp_colour

    print("\n== Mash detection: lots of presses across multiple keys ==")
    t = 0.0
    pattern = [0, 1, 2, 1, 1, 0, 2, 1, 2, 0, 1, 2, 2, 0]
    for k in pattern:
        t += 0.05  # 50ms apart -> fast mashing
        engine.on_key_down(k, now=t)
        engine.on_key_up(k, now=t + 0.01)
    print(f"  is_mashing after burst: {engine.is_mashing}")
    assert engine.is_mashing, "should detect mashing from this messy burst"

    print("\n  ...waiting for cooldown...")
    engine.tick(now=t + 2.0)  # well past COOLDOWN_SECONDS with no new presses
    print(f"  is_mashing after cooldown: {engine.is_mashing}")
    assert not engine.is_mashing, "mashing should have ended after the cooldown"

    print("\nAll checks passed.")
