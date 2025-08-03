import sys
import os
import time
import signal
import pigpio
# Sends jamming signal unitl you exit with CTRL+C, only works at close range, 
running = True
def handle_exit(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, handle_exit)

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
            waveform.append(pigpio.pulse(1 << pin, 0, duration))  # HIGH
        else:
            waveform.append(pigpio.pulse(0, 1 << pin, duration))  # LOW

    pi.wave_clear()
    pi.wave_add_generic(waveform)
    wave_id = pi.wave_create()

    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        while pi.wave_tx_busy() and running:
            pass
        pi.wave_delete(wave_id)
    else:
        print(f"Error with wave creation!")

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python3 sub_loop_jammer.py /path/to/file.sub [gpio_pin]")
        sys.exit(1)

    sub_path = sys.argv[1]
    pin = int(sys.argv[2]) if len(sys.argv) == 3 else 13  # Default to GPIO13

    if not os.path.isfile(sub_path):
        print(f"Specific file not found!")
        sys.exit(1)

    pi = pigpio.pi()
    parser = FlipperSubParser(sub_path)

    print(f"Jamming started! Press Ctrl+C to stop.\n")

    try:
        while running:
            for i, pulses in enumerate(parser.raw_blocks):
                if not running:
                    break
                send_waveform(pi, pin, pulses)
                pi.write(pin, 0)
    finally:
        pi.wave_clear()
        pi.write(pin, 0)
        pi.stop()
        print("\nInterrupt detected, jamming ended!")

if __name__ == "__main__":
    main()
