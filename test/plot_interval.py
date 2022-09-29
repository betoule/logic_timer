import numpy as np
import matplotlib.pyplot as plt

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Display the interval in seconds between successive fronts on the specified line.')
    parser.add_argument(
        '-i', '--input-file', default='timing_test.npy',
        help='Input filename')
    parser.add_argument(
        '-l', '--lines', default=[1], nargs='+', type=int,
        help='Lines to be displayed')
    
    args = parser.parse_args()

    record = np.load(args.input_file)
    for l in args.lines:
        t = record['time'][record['pinstate'] == l]
        t = t * 0.5e-6 # Convert timing in seconds
        plt.plot(t[1:] - t[:-1], 'o')
        plt.ylabel('Measured interval [s]')
        plt.xlabel('Pulse number')
        plt.tight_layout()
        plt.show()
