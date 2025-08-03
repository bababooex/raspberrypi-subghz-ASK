import sys
import os
import time
import pigpio
# Simple conversion from .sub to ASK signal, uses wave chaining for longer continuous signal
# ==== CONFIG ====
MAX_PULSES_PER_WAVE = 5400
# =================

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

def send_wave_chained(pi, pin, pulses, max_chunk_len, max_chain_length):
    pi.set_mode(pin, pigpio.OUTPUT)
    pi.write(pin, 0)
    pi.wave_clear()

    idx = 0
    total_len = len(pulses)

    while idx < total_len:
        wave_ids = []

        for _ in range(max_chain_length):
            if idx >= total_len:
                break

            chunk = pulses[idx:idx + max_chunk_len]
            waveform = []

            for pulse in chunk:
                duration = abs(pulse)
                if pulse > 0:
                    waveform.append(pigpio.pulse(1 << pin, 0, duration))  # HIGH
                else:
                    waveform.append(pigpio.pulse(0, 1 << pin, duration))  # LOW

            pi.wave_add_generic(waveform)
            wave_id = pi.wave_create()

            if wave_id < 0:
                print(f"Error with wave creation!")
                pi.wave_clear()
                # Retry this chunk after cleaning up
                return send_wave_chained(pi, pin, pulses[idx:], max_chunk_len, max_chain_length)

            wave_ids.append(wave_id)
            idx += len(chunk)

        if wave_ids:
            chain = []
            for wid in wave_ids:
                chain += [255, 0, wid]  # Append each waveform ID to the chain

            pi.wave_chain(chain)
            while pi.wave_tx_busy():
                pass

            for wid in wave_ids:
                pi.wave_delete(wid)

    pi.write(pin, 0)
    pi.wave_clear()


def main():
    if len(sys.argv) !=4:
        print("Usage: python3 sub_converter.py /path/to/file.sub [chain_length] [gpio_pin]")
        sys.exit(1)

    sub_path, chain_length, gpio_pin = sys.argv[1], sys.argv[2], sys.argv[3]
    MAX_CHAIN_LENGTH = int(chain_length)
    PIN = int(gpio_pin)

    if not os.path.isfile(sub_path):
        print(f"Specific file not found")
        sys.exit(1)

    pi = pigpio.pi()

    parser = FlipperSubParser(sub_path)

    # Merge all RAW blocks
    all_pulses = []
    for block in parser.raw_blocks:
        all_pulses.extend(block)

    print(f"Transmitting {len(all_pulses)} pulses with wave chaining")
    send_wave_chained(pi, PIN, all_pulses, MAX_PULSES_PER_WAVE, MAX_CHAIN_LENGTH)

    pi.stop()

if __name__ == "__main__":
    main()

