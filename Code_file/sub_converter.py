import sys
import os
import pigpio

# ==== CONFIG ====
MAX_PULSES_PER_WAVE = 5400
# ================

# =======================
# Protocol Definitions
# =======================
PROTOCOLS = {
    # GateTX
    "GateTX": {
        "short": 350,
        "long": 700,
        "bit_len": 24,
        "header": [(-49, 2)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(1, -30)],  
    },
    # Princeton
    "Princeton": {
        "short": 390,
        "long": 1170,
        "bit_len": 24,
        "bit_map": {
            "0": [(1, -3)],
            "1": [(3, -1)],
        },
    "stop": [(1, -30)],
    },
    # Honeywell WDB
    "Honeywell": {
        "short": 160,
        "long": 320,
        "bit_len": 48,
        "header": [(-3, )],
        "bit_map": {
            "0": [(1, -2)],
            "1": [(2, -1)],
        },
    "stop": [(3,)],
    },
    # Holtek
    "Holtek": {
        "short": 430,
        "long": 870,
        "bit_len": 40,
        "header": [(-36, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)], # To prevent trailing - last bit longer
    },
    "Holtek_HT12X": {
        "short": 320,
        "long": 640,
        "bit_len": 12,
        "header": [(-36, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    # Nice FLO
    "Nice FLO": {
        "short": 700,
        "long": 1400,
        "bit_len": 12,
        "header": [(-36, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    # Ansonic
    "Ansonic": {
        "short": 555,
        "long": 1111,
        "bit_len": 12,
        "header": [(-35, 1)],
        "bit_map": {
            "0": [(-2, 1)],
            "1": [(-1, 2)],
        },
    "stop": [(-1,)],
    },
    # Hormann
    "Hormann HSM": {
        "short": 500,
        "long": 1000,
        "bit_len": 44,
        "header": [(24, -1)],
        "bit_map": {
            "0": [(1, -2)],
            "1": [(2, -1)],
        },
    "stop": [(-24,)],
    },
    # SMC5326
    "SMC5326": {
        "short": 300,
        "long": 900,
        "bit_len": 25,
        "bit_map": {
            "0": [(1, -3)],
            "1": [(3, -1)],
        },
    "stop": [(1,25)],
    },
    # Phoenix_V2
    "Phoenix_V2": {
        "short": 427,
        "long": 853,
        "bit_len": 52,
        "header": [(-60, 6)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    # Came variants (does not include CAME TWEE, not sure about this one, uses XOR magic)
    "Came12": {
        "short": 320,
        "long": 640,
        "bit_len": 12,
        "header": [(-47, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    "Came18": {
        "short": 320,
        "long": 640,
        "bit_len": 18,
        "header": [(-47, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    "Came24": {
        "short": 320,
        "long": 640,
        "bit_len": 24,
        "header": [(-76, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
    "Came25": {
        "short": 320,
        "long": 640,
        "bit_len": 25,
        "header": [(-36, 1)],
        "bit_map": {
            "0": [(-1, 2)],
            "1": [(-2, 1)],
        },
    "stop": [(-1,)],
    },
}
# Maybe will add more in the future

# =======================
# Parsers
# =======================
class FlipperSubParser:
    def __init__(self, path):
        self.path = path
        self.meta = {}
        self.raw_blocks = []
        self.parse_file()

    def parse_file(self):
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    self.meta[key.strip()] = val.strip()

                if line.startswith("RAW_Data:"):
                    raw_line = line.split(":", 1)[1].strip()
                    pulses = [int(x) for x in raw_line.split()]
                    self.raw_blocks.append(pulses)
                elif line.startswith("+") or line.startswith("-"):
                    pulses = [int(x) for x in line.split()]
                    if self.raw_blocks:
                        self.raw_blocks[-1].extend(pulses)


# =======================
# Encoders
# =======================
def encode_protocol(proto_def, key_hex, te_override=None):
    pulses = []

    short = te_override if te_override else proto_def["short"] # Princeton often has TE, this is for better precision, not sure about others... but just to be sure

    # Multiplying based on constant short lenght for each protocol
    def apply_multiplier(seg):
        return [val * short for val in seg]

    # Header (optional)
    if "header" in proto_def:
        for h in proto_def["header"]:
            pulses.extend(apply_multiplier(h))

    # Convert hex key to binary string, padded to protocol's bit_len to match the bits exactly
    bit_len = proto_def["bit_len"]
    key_bin = bin(int(key_hex.replace(" ", ""), 16))[2:].zfill(bit_len)

    # Bit encoding for precision
    for b in key_bin:
        for seg in proto_def["bit_map"].get(b, []):
            pulses.extend(apply_multiplier(seg))

    # Stop (optional)
    if "stop" in proto_def:
        for s in proto_def["stop"]:
            pulses.extend(apply_multiplier(s))

    return pulses

def encode_binraw(bit_len, te, data_raw): # BinRAW encoding, just to be complete
    pulses = []
    data_bits = "".join(f"{int(x,16):04b}" for x in data_raw.split())
    data_bits = data_bits[:bit_len]

    for bit in data_bits:
        if bit == "1":
            pulses.append(te)
        else:
            pulses.append(-te)
    return pulses


# =======================
# Wave sending
# =======================
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
                pi.wave_clear()
                raise RuntimeError("No more control blocks available")

            wave_ids.append(wave_id)
            idx += len(chunk)

        if wave_ids:
            chain = []
            for wid in wave_ids:
                chain += [255, 0, wid]

            pi.wave_chain(chain)
            while pi.wave_tx_busy():
                pass

            for wid in wave_ids:
                pi.wave_delete(wid)

    pi.write(pin, 0)
    pi.wave_clear()


# =======================
# Main
# =======================
def main():
    if len(sys.argv) != 4:
        print("Usage: python3 sub_converter.py /path/to/file.sub <chain_length> <gpio_pin>")
        sys.exit(1)

    sub_path, chain_length, gpio_pin = sys.argv[1], sys.argv[2], sys.argv[3]
    MAX_CHAIN_LENGTH = int(chain_length)
    PIN = int(gpio_pin)

    parser = FlipperSubParser(sub_path)
    meta = parser.meta
    pulses = []
    # Main decision logic
    try:
        proto = meta.get("Protocol", "RAW")

        if proto == "RAW":
            for block in parser.raw_blocks:
                pulses.extend(block)

        elif proto == "BinRAW":
            te = int(meta["TE"])
            bit_len = int(meta["Bit_RAW"])
            data_raw = meta["Data_RAW"]
            pulses = encode_binraw(bit_len, te, data_raw)

        elif proto == "Princeton":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Princeton"], key, te)

        elif proto == "Ansonic":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Ansonic"], key, te)

        elif proto == "GateTX":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["GateTX"], key, te)

        elif proto == "Holtek":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Holtek"], key, te)

        elif proto == "Holtek_HT12X":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Holtek_HT12X"], key, te)
        
        elif proto == "SMC5326":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["SMC5326"], key, te)    
                  
        elif proto == "Hormann HSM":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Hormann HSM"], key, te)    
        
        elif proto == "Phoenix_V2":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Phoenix_V2"], key, te)
        
        elif proto == "Honeywell":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Honeywell"], key, te)  
                        
        elif proto == "Ansonic":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Ansonic"], key, te)

        elif proto == "Nice FLO":
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]
            pulses = encode_protocol(PROTOCOLS["Nice FLO"], key, te)

        elif proto == "CAME":
            bit_len = int(meta.get("Bit", 0))
            te = int(meta.get("TE", 0)) or None
            key = meta["Key"]

            if bit_len == 12:
                pulses = encode_protocol(PROTOCOLS["Came12"], key, te)
            elif bit_len == 18:
                pulses = encode_protocol(PROTOCOLS["Came18"], key, te)
            elif bit_len == 24:
                pulses = encode_protocol(PROTOCOLS["Came24"], key, te)
            elif bit_len == 25:
                pulses = encode_protocol(PROTOCOLS["Came25"], key, te)

    except:
            print(f"Sub file contains unsupported protocol!")

    pi = pigpio.pi()

    print(f"Transmitting {len(pulses)} pulses via {proto} protocol")
    send_wave_chained(pi, PIN, pulses, MAX_PULSES_PER_WAVE, MAX_CHAIN_LENGTH)
    pi.stop()


if __name__ == "__main__":
    main()
