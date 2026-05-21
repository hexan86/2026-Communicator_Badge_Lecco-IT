import time
from machine import I2C, Pin
from adafruit_pn532 import PN532, BusyError  # <--- Questa è la riga fondamentale

_I2C_ADDRESS = 0x24
_NOT_BUSY = 0x01

class PN532_I2C(PN532):
    """Driver per il PN532 connesso via I2C per MicroPython."""

    def __init__(self, i2c, *, reset=None, req=None, debug=False):
        self.debug = debug
        self._i2c = i2c
        self._req = req
        
        if reset:
            if self.debug:
                print("Resetting PN532...")
            reset_pin = Pin(reset, Pin.OUT)
            reset_pin.value(1)
            time.sleep(0.1)
            reset_pin.value(0)
            time.sleep(0.5)
            reset_pin.value(1)
            time.sleep(0.1)
            
        # Inizializza la classe base (quella di Luiz Brandao)
        super().__init__(debug=debug)

    def _wakeup(self):
        """Sveglia il PN532 inviando i segnali necessari."""
        if self._req:
            req_pin = Pin(self._req, Pin.OUT)
            req_pin.value(1)
            time.sleep(0.1)
            req_pin.value(0)
            time.sleep(0.1)
            req_pin.value(1)
        time.sleep(0.5)

    def _wait_ready(self, timeout=1):
        """Attende che il PN532 sia pronto."""
        status = bytearray(1)
        # Usiamo time.ticks_ms() che è lo standard MicroPython per l'ESP32
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < (timeout * 1000):
            try:
                self._i2c.readfrom_into(_I2C_ADDRESS, status)
            except OSError:
                self._wakeup()
                continue
            if status == b'\x01':
                return True
            time.sleep(0.01)
        return False

    def _read_data(self, count):
        """Legge i dati dal PN532 via I2C."""
        frame = bytearray(count + 1)
        status_byte = bytearray(1)
        
        self._i2c.readfrom_into(_I2C_ADDRESS, status_byte)
        if status_byte[0] != _NOT_BUSY:
            raise BusyError
            
        self._i2c.readfrom_into(_I2C_ADDRESS, frame)
        return frame[1:]  # Salta lo status byte

    def _write_data(self, framebytes):
        """Scrive i dati nel PN532 via I2C."""
        self._i2c.writeto(_I2C_ADDRESS, framebytes)
