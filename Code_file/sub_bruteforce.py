import sys
import os
import time
import pigpio
# Good for for transmitting long codes line by line

class FlipperSubParser:
    def __init__(self, path):
        self.path = path
        self.raw_blocks = self.extract_raw_blocks()

    def extract_raw_blocks(self):
        blocks = []
        with open(self.path, "r") as f:
            for line in f:
                if line.startswith("RAW_Data:"):
                    raw_line = line.split(":", 1)[1].strip()
                    pulses = [int(x) for x in raw_line.split()]
                    blocks.append(pulses)
                elif line.strip().startswith("+") or line.strip().startswith("-"):
                    pulses = [int(x) for x in line.strip().split()]
                    if blocks:
                        blocks[-1].extend(pulses)
        return blocks

def send_waveform(pi, pin, pulses):
    pi.set_mode(pin, pigpio.OUTPUT)
    pi.write(pin, 0)
    waveform = []

    for pulse in pulses:
        duration = abs(pulse)
        if pulse > 0:
            waveform.append(pigpio.pulse(1 << pin, 0, duration))
        else:
            waveform.append(pigpio.pulse(0, 1 << pin, duration))

    pi.wave_clear()
    pi.wave_add_generic(waveform)
    wave_id = pi.wave_create()
    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        while pi.wave_tx_busy():
            pass
        pi.wave_delete(wave_id)
    pi.write(pin, 0)

def main():
    global pi, PIN

    if len(sys.argv) != 5:
        print("Usage: sub_bruteforce.py /path/to/file.sub <repeat> <delay_ms> <gpio_pin>")
        sys.exit(1)

    sub_path, repeat_str, delay_str, gpio_str = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    REPEAT = int(repeat_str)
    DELAY = int(delay_str) / 1000
    PIN = int(gpio_str)

    pi = pigpio.pi()

    pi.set_mode(PIN, pigpio.OUTPUT)
    pi.write(PIN, 0)

    parser = FlipperSubParser(sub_path)
    if not parser.raw_blocks:
        print("No RAW_Data found in file.")
        pi.stop()
        sys.exit(1)

    for idx, block in enumerate(parser.raw_blocks):
        print(f"Sending data block {idx+1}/{len(parser.raw_blocks)} with {len(block)} pulses")
        for _ in range(REPEAT):
            send_waveform(pi, PIN, block)
            time.sleep(0.02)
        time.sleep(DELAY)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        if pi:
            if PIN is not None:
                pi.write(PIN, 0)
            pi.stop()



