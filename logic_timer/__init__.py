# Copyright 2021-2022 Marc Betoule
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bincoms
import struct
import time
import numpy as np

class LogicTimer(bincoms.SerialBC):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        self.duration = 1
        
    def async_packet_read(self):
        ans = self.rcv()
        answer = struct.unpack('<IB', ans)
        return answer

    def set_duration(self, duration):
        self.duration = duration

    def get_duration(self):
        return self.duration
    
    def get_data(self):
        data = []
        print(self.start(self.duration))
        self.com.timeout = self.duration+1
        while True:
            data.append(self.async_packet_read())
            if(data[-1][-1] == 0xFF):
                #data.pop()
                break
        return data
        #return np.rec.fromrecords(data, names=['time', 'pinstate'])

if __name__ == '__main__':
    d = LogicTimer(dev='/dev/ttyACM0', baudrate=1000000, debug=False)
    d.set_duration(100)
    import numpy as np
    import matplotlib.pyplot as plt
    toto = np.array(d.get_data())
    t = toto[toto[:,1] == 1, 0]
    plt.plot(t[1:] - t[:-1])
    plt.show()
