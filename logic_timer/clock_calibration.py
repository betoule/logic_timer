import ntplib
import time
import numpy as np
import matplotlib.pyplot as plt
import tqdm

server="pool.ntp.org"
client = ntplib.NTPClient()
        
def acquire_clock_data(device, duration=600, ntp=0, interval=0.1):
    ''' Acquire clock synchronisation data from the host and mcu.
    
    Note:
    -----
    Keep in mind that the mcu ~2MHz clock roll over after ~35.79 minutes (2**32/2e6)

    Parameters:
    -----------
    device: SmartIris object
    duration: float
      Acquisition duration in seconds
    ntp: float
      If non zero, attempt to perform ntp queries at the provided interval to check the host clock calibration as well
    interval: float
      Approximate interval between 2 mcu queries in seconds

    return:
    -------
    mcu_data: numpy record array
    ntp_data: numpy record array
    '''
    def mcu_tic():
        start = time.time()
        devtime = device.get_time()
        stop = time.time()
        mcu_temp = device.read_mcu_temperature()
        #temp = device.read_temperature()
        #ubank = device.read_capacitor_bank_voltage()
        #return start, devtime/device.frequency, stop, mcu_temp, temp, ubank
        return start, devtime/device.frequency, stop, mcu_temp

    def ntp_tic():
        start = time.time()
        devtime = device.get_time()
        response = client.request(server, version=4)
        stop = time.time()
        return start, response.tx_time, stop

    mcu_data = []
    ntp_data = []
    last_ntp = 0
    start = time.time()
    device.start_timer()
    total_steps = int(duration / interval)
    with tqdm.tqdm(total=total_steps, desc="Clock calibration", unit="s") as pbar:
        while(time.time() - start < duration):
            mcu_data.append(mcu_tic())
            if (ntp != 0) and ((time - last_ntp) > ntp):
                try:
                    ntp_data.append(ntp_tic())
                except:
                    pass
            progress = int(((time.time() - start) / duration) * total_steps)
            pbar.n = min(progress, total_steps)
            pbar.refresh()
            time.sleep(interval)
    if not ntp_data:
        ntp_data = [[np.nan, np.nan, np.nan]]
    return (np.rec.fromrecords(mcu_data, names=['start', 'mcu', 'stop', 'mcu_temp']),
            np.rec.fromrecords(ntp_data, names=['start', 'nntp', 'stop']))


def save(mcu_data, ntp_data, filename='timing.npz'):
    np.savez(filename, ntp_data=ntp_data, mcu_data=mcu_data)

def load(filename='timing.npz'):
    data = np.load(filename)
    return data['mcu_data'], data['ntp_data']

def clock_calibration_fit(t1, t2, show=False, axes=None, **keys):
    x = t1 - t1.min()
    y = t2 - t2.min()
    p, cov = np.polyfit(x, y, 1, cov=True)
    res = y - np.polyval(p, x)
    eslope = np.sqrt(cov[0,0])
    if show: 
        if axes is None:
            axes = plt.gcf().subplots(2,1,sharex=True)
        ax1, ax2 = axes

        ax1.plot(x, y-x, ',', **keys)
        v = [x.min(), x.max()]
        ax1.plot(v, np.polyval(p, v)-np.array(v), 'k-', label=rf'$\alpha={p[0]-1:.6f}\pm{eslope:.6f}$', **keys)
        ax1.legend(frameon=False)
        ax2.plot(x, res*1000, ',', label=rf'$\sigma={res.std()*1000:.2f}$ ms', **keys)
        ax2.legend(frameon=False)
        ax2.set_xlabel('host clock [s]')
        ax1.set_ylabel('mcu - host [s]')
        ax2.set_ylabel(rf'mcu - $(1+\alpha)$ host [ms]')
        ax2.axhline(0, color='k')
        return p[0], eslope, axes 
    else:
        return p[0], eslope
def binplot(x, y, binsize=10, ls='None', marker='.', ax=None, **kwargs):
    """
    Plot the average of y data in bins of binsize successive x values.
    
    Parameters:
    x (array-like): x-coordinates of the data points
    y (array-like): y-coordinates of the data points
    binsize (int): Number of x values per bin (default: 10)
    **kwargs: Additional keyword arguments passed to plt.plot
    """
    if ax is None:
        ax = plt.gca()
    # Convert inputs to numpy arrays
    x = np.array(x)
    y = np.array(y)
    
    # Sort data by x values
    sort_idx = np.argsort(x)
    x_sorted = x[sort_idx]
    y_sorted = y[sort_idx]
    
    # Calculate number of bins
    n = len(x)
    nbins = n // binsize + (1 if n % binsize else 0)

    bins = np.repeat(np.arange(nbins), binsize)[:n]
    N = np.bincount(bins)
    x_means = np.bincount(bins, x)/N
    y_means = np.bincount(bins, y)/N
    y_rms = np.sqrt(np.bincount(bins, y**2) / N - y_means**2)
    # Create the plot
    ax.errorbar(x_means, y_means, y_rms/np.sqrt(N), ls=ls, marker=marker, **kwargs)
    return x_means, y_means, y_rms/np.sqrt(N)
    #plt.grid(True)
    
if __name__ == '__main__':
    import smartiris
    import sys
    plt.rc('axes.spines', right=False, top=False)
    plt.rc('text', usetex=True)

    mcu_data, ntp_data = load(sys.argv[1])
    plt.figure('calibration fit')
    slope1, eslope1, axes = clock_calibration_fit(mcu_data['start'], mcu_data['mcu'], show=True, color='#1b9e77')
    #d1 = mcu_data[:mcu_data['mcu'].argmax()+1]
    #d2 = mcu_data[mcu_data['mcu'].argmax()+1:]
    #slope1, eslope1, axes = clock_calibration_fit(d1['start'], d1['mcu'], show=True, color='#1b9e77')
    #slope2, eslope2, axes = clock_calibration_fit(d2['start'], d2['mcu'], show=True, axes=axes, color='#d95f02')

    calibrated_frequency = 2e6 * slope1
    plt.tight_layout()
    binsize = 300
    t = []
    slope = []
    eslope = []
    for i in range(len(mcu_data)//binsize):
        cutout = slice(i*binsize,(i+1)*binsize)
        s, e = clock_calibration_fit(mcu_data['start'][cutout], mcu_data['mcu'][cutout])
        t.append((mcu_data['start'][cutout] - mcu_data['start'][0]).mean())
        slope.append(s)
        eslope.append(e)
    f = plt.figure('temp evolution')
    if not f.axes:
        ax1, ax2 = f.subplots(2,1,sharex=True)
    else:
        ax1, ax2 = f.axes
    t0, temp, etemp = binplot(mcu_data['start'] - mcu_data['start'].min(), mcu_data['mcu_temp'], binsize, ax=ax1)
    plt.xlabel('mcu clock [s]')
    plt.ylabel('temperature [°C]')
    
    ax2.errorbar(t, slope, eslope)
    plt.tight_layout()

    plt.figure('temp')
    plt.errorbar(temp[:-1], slope, xerr=etemp[:-1], yerr=eslope, ls='None', marker='.')
    #plt.savefig('doc/clock_calibration.png', dpi=300)
    
#axes = calib(mcu_data['start'] - mcu_data['start'].min(), mcu_data['mcu'] - mcu_data['mcu'].min())
#calib(ntp_data['start'] - ntp_data['start'].min(), ntp_data['ntp'] - ntp_data['ntp'].min(), axes)
