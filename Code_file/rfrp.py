import argparse
import json
import pigpio
import time
import os
# ========== CONFIG =========
DEFAULT_FILENAME = "saved_codes.json"
DEFAULT_RECORD_MS = 500
MAX_PULSES = 5400
# ===========================
def record(pi, filename, name, rx_gpio, record_time_ms):
    print(f"Recording '{name}' on GPIO {rx_gpio} for {record_time_ms} ms (max {MAX_PULSES} transitions)...")

    last_tick = None
    recording = []
    error = False

    def cb_func(gpio, level, tick):
        nonlocal last_tick, error
        if last_tick is not None:
            duration = pigpio.tickDiff(last_tick, tick)
            if len(recording) < MAX_PULSES:
                recording.append([level, duration])
            else:
                error = True
        last_tick = tick

    pi.set_mode(rx_gpio, pigpio.INPUT)
    cb = pi.callback(rx_gpio, pigpio.EITHER_EDGE, cb_func)
    time.sleep(record_time_ms / 1000.0)
    cb.cancel()

    if not recording:
        print("No signal recorded, check you receiver or connection!")
        return

    if error:
        print(f"Max pulse limit ({MAX_PULSES}) exceeded! Recording was cut off.")

    data = {}
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
     try:
        with open(filename, "r") as f:
            data = json.load(f)
     except json.JSONDecodeError:
         print(f"Warning: '{filename}' is invalid or empty. JSON error!")


    data[name] = recording[:MAX_PULSES]

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[+] Saved {len(recording[:MAX_PULSES])} transitions to '{name}'.")

def send(pi, filename, name, tx_gpio):
    if not os.path.exists(filename):
        print(f"File '{filename}' not found, check your directory!")
        return

    with open(filename, "r") as f:
        data = json.load(f)

    if name not in data:
        print(f"No code named '{name}' found!")
        return

    signal = data[name]
    wf = []

    for level, duration in signal:
        if level == 1:
            wf.append(pigpio.pulse(1 << tx_gpio, 0, duration))
        else:
            wf.append(pigpio.pulse(0, 1 << tx_gpio, duration))

    pi.set_mode(tx_gpio, pigpio.OUTPUT)
    pi.wave_add_new()
    pi.wave_add_generic(wf)
    wave_id = pi.wave_create()
    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        print(f"Sending '{name}' on GPIO {tx_gpio}...")
        while pi.wave_tx_busy():
            pass
        pi.wave_delete(wave_id)
    else:
        print("Failed to create waveform.")

def main():
    parser = argparse.ArgumentParser(description="433 MHz ASK recorder/player")
    parser.add_argument("--record", action="store_true", help="Record a signal")
    parser.add_argument("--send", action="store_true", help="Send a signal")
    parser.add_argument("--name", required=True, help="Name of signal")
    parser.add_argument("--file", default=DEFAULT_FILENAME, help="JSON file")
    parser.add_argument("--time", type=int,  help="Recording time (ms)")
    parser.add_argument("--tx", type=int, help="TX GPIO pin")
    parser.add_argument("--rx", type=int, help="RX GPIO pin")
    args = parser.parse_args()

    pi = pigpio.pi()

    try:
        if args.record:
            record(pi, args.file, args.name, args.rx, args.time)
        elif args.send:
            send(pi, args.file, args.name, args.tx)
        else:
            print("Use --record or --send.")
    finally:
        pi.stop()

if __name__ == "__main__":
    main()


