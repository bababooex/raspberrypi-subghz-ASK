import argparse
import time
import json
import os
import pigpio
import matplotlib
import matplotlib.pyplot as plt

# Original file by @breisa - https://github.com/breisa/433mhz
# This is modified version, that uses single .json file and also allows exporting plots
# I replaced my original rfrp.py with this code, because it has better functions and features

# ========== CONFIG =========
DEFAULT_FILENAME = "saved_codes.json"
DEFAULT_GRAPHFILE = "./graphs/"
DEFAULT_RECORD_MS = 500
# ===========================

def store(path, key, data):
    if os.path.exists(path):
        with open(path, 'r') as file:
            all_data = json.load(file)
    else:
        all_data = {}
    all_data[key] = data
    with open(path, 'w') as file:
        json.dump(all_data, file, indent=2)
def load(path, key):
    with open(path, 'r') as file:
        all_data = json.load(file)
    if key not in all_data:
        raise KeyError(f"Code with name {key} not found in {path}.")
    return all_data[key]

def record(file, name, pin, rectime):
    print("Recording started!")
    record_edges = False
    edges = []
    pi=pigpio.pi()
    def handle_edge(pin, level, useconds):
        if (record_edges and useconds > start_time):
            edges.append((level, useconds))
    pi.set_pull_up_down(pin, pigpio.PUD_DOWN)
    pi.set_mode(pin, pigpio.INPUT)
    pi.callback(pin, pigpio.EITHER_EDGE, handle_edge)
    print("Recording started!")
    start_time = pi.get_current_tick()
    record_edges = True
    time.sleep(rectime)
    record_edges = False
    stop_time = pi.get_current_tick()

    pi.stop()

    if (len(edges) >= 2):
        if (edges[0][0] == 0):
            edges = edges[1:]
        if (edges[-1][0] == 1):
            edges = edges[:-1]

    if (len(edges) < 2):
        print("No signal recorded, check you receiver or connection!")
    else:
        signal = []
        last_time = start_time
        for level, useconds in edges:
            time_diff = useconds - last_time
            signal.append((int(level == 0), time_diff))
            last_time = useconds
        signal.append((0, stop_time - last_time))

        store(file, name, signal)
        print(f"Saved {len(signal)} with {name} to {file}.")

def send(file, name, pin):
    data = load(file, name)
    pi=pigpio.pi()
    pi.set_mode(pin, pigpio.OUTPUT)
    print(f"Sending {name} from {file}...", end='', flush=True)
    waveform = []
    for state, duration in data:
        match state:
            case 1:
                waveform.append(pigpio.pulse(1<<pin, 0, duration))
            case 0:
                waveform.append(pigpio.pulse(0, 1<<pin, duration))
    pi.wave_clear()
    pi.wave_add_generic(waveform)
    signal = pi.wave_create()

    pi.wave_send_once(signal)
    time.sleep(1.5 * pi.wave_get_micros()/1_000_000)
    pi.wave_tx_stop()
    pi.wave_clear()

    print("Code sent!")
    pi.stop()

def plot(file, name, export=False):
    signal = load(file, name)

    dots = []
    time = 0
    for state, duration in signal:
        dots.append((time, state))
        time += duration
        dots.append((time, state))

    x, y = zip(*dots)
    plt.figure(num=f"{file}:{name}")
    plt.title(f"ASK code: {name}")
    plt.xlabel("Microseconds [μS]")
    plt.ylabel("Amplitude (logic 0/1)")
    plt.plot(x, y)
    if export:
        outfile = f"{name}.svg"
        plt.savefig(DEFAULT_GRAPHFILE + outfile)
        print(f"Saved plot as {outfile}.")
    else:
        plt.show()

def create_argument_parser():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--record", metavar="GPIO", type=int,
        help="Record a signal")
    modes.add_argument("--plot", action="store_true", default=False,
        help="Plot a signal")
    modes.add_argument("--send", metavar="GPIO", type=int,
        help="Send a signal")
    parser.add_argument("--rectime", metavar='MS', type=int, default=DEFAULT_RECORD_MS,
        help="Recording time (ms)")
    parser.add_argument("--name", required=True,
        help="Name of a signal")
    parser.add_argument("--file", required=True, default=DEFAULT_FILENAME, help="JSON file to store all signals")
    parser.add_argument("--export", action='store_true', help="Export as .svg if using CLI, otherwise show normally")
    return parser

def main():
    arg_parser = create_argument_parser()
    args = arg_parser.parse_args()
    pi = pigpio.pi()
    if (args.record is not None):
        if (args.rectime < 100 or args.rectime > 10_000):
            print("Recording time should be between 100ms and 10s.")
        else:
            record(args.file, args.name, args.record, args.rectime/1000)
    elif (args.plot):
        plot(args.file, args.name, export=args.export)
    elif (args.send is not None):
        send(args.file, args.name, args.send)
    else:
        arg_parser.print_help()

if __name__ == "__main__":
        main()




