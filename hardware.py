from abc import ABCMeta, abstractmethod
import time
import urllib2

class HardwareInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def connect(self, timeout = None):
        """
        Connect to the underlying hardware. Optional connection timeout.
        """
        pass

    @abstractmethod
    def send(self, data):
        """
        Send data to the underlying hardware, then reads back the response.
        Returns the response, or None if the sending or subsequent reading
        fails.
        """
        pass

"""
Interface to OSCAR. Sends data by visiting a specified URL.
"""
class OscarInterface(HardwareInterface):
    def __init__(self, url):
        self.__url = url

    def connect(self, timeout = None):
        """Connecting to OSCAR succeeds trivially."""
        return True

    def send(self, data):
        """
        Open the URL. The supplied data is ignored. Returns a boolean
        indicating whether the operation succeeded.
        """
        try:
            response = urllib2.urlopen(self.__url)
            return bool(response)
        except urllib2.URLError:
            return False

class ArduinoInterface(HardwareInterface):
    START_BYTE = b'\x02'
    END_BYTE   = b'\x03'

    def __init__(self, serial_pool, port, address):
        self.__serial_pool = serial_pool
        self.__port = port
        self.__address = address
        self.__arduino = None

    def connect(self, timeout = 2):
        self.__arduino = self.__serial_pool.connect(self.__port, timeout)
        return bool(self.__arduino)

    def send(self, data):
        if not self.__arduino or not data:
            return None

        self.__send_command(data)
        return self.__wait_for_confirm()

    def __send_command(self, command):
        crc = (self.__address ^ ord(command) ^ self.data[0] ^ self.data[1] ^ self.data[2])
        n = self.__arduino.write(self.__format_msg(command, self.data[0], self.data[1], self.data[2], crc))

    def __format_msg(self, command, data0, data1, data2, data3):
        return b''.join([START_BYTE, chr(self.__address), command, chr(data0), chr(data1), chr(data2), END_BYTE, chr(data3)])

    def __wait_for_confirm(self):
        time.sleep(.000001)
        if self.__arduino.readable():
            data = self.__arduino.readline()
            if not data:
                return None
            else:
                return self.__parse_status_response(data)

        return None

    @classmethod
    def __parse_status_response(cls, data):
        crc = 0
        tag = 0
        startFound = False
        endFound = False
        value = 0

        for i in range(8):
            dataByte = data[i]

            if dataByte == START_BYTE:
                startIndex = i
                startFound = True
            elif dataByte == END_BYTE and not endFound:
                endFound = True
            else:
                if startFound and not endFound:
                    crc ^= ord(dataByte)
                    if (i >= (startIndex + 2)):
                        value = value << 8
                        value ^= ord(dataByte)

                if endFound:
                    checksum = ord(dataByte)
                    if checksum == crc:
                        return value
                    else:
                        return 0

        return 0

"""
Testing actuator. Prints upon connection, as well as any sent data. Can't be
read from.
"""
class TestActuator(HardwareInterface):
    def __init__(self, name):
        self.__name = name

    def connect(self, timeout = None):
        print('Opened connection to TestActuator {} (timeout {})'.format(self.__name, timeout))
        return True

    def send(self, data):
        print('Sent {} to {}'.format(data, self.__name))

"""
Testing actuator. A
"""
class TestSensor(HardwareInterface):
    def __init__(self, name):
        self.__name = name

    def connect(self, timeout = None):
        print('Opened connection to TestSensor {} (timeout {})'.format(self.__name, timeout))
        return True

    def send(self, data):
        if data == b'\x0b': #status
            time.sleep(0.1)
            return {'steen1': 13421961}.get(self.__name, None)
        return None

