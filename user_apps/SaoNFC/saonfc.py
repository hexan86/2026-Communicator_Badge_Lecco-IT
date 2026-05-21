""" Async PN532 NFC Reader App for Hackaday Communicator Badge SAO Port """

import time
import lvgl
import uasyncio as aio

from apps.base_app import BaseApp
from pn532_i2c import PN532_I2C


class NFCReaderApp(BaseApp):

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        self.nfc = None

        self.uid_label = None
        self.status_label = None

        self.last_uid = None
        self.last_seen_time = 0

        self.pending_uid = None

        self.nfc_task = None
        self.running = False

        # Keep UI responsive
        self.foreground_sleep_ms = 10
        self.background_sleep_ms = 1000

        self._init_nfc()

    # PN532 INIT
    def _init_nfc(self):

        try:
            i2c = self.badge.sao_i2c

            try:
                devices = i2c.scan()
                print("I2C devices found:", [hex(d) for d in devices])

            except Exception as e:
                print("I2C scan failed:", e)

            self.nfc = PN532_I2C(i2c, debug=False)
            self.nfc.SAM_configuration()

            print("PN532 initialized!")

        except Exception as e:
            print("PN532 init error:", e)
            self.nfc = None

    # ASYNC NFC LOOP
    async def nfc_loop(self):

        print("Starting NFC polling loop")

        while self.running:

            try:
                if self.nfc:

                    # VERY IMPORTANT:
                    # tiny timeout prevents scheduler blocking
                    uid = self.nfc.read_passive_target(timeout=1)

                    if uid:
                        self.pending_uid = tuple(uid)

            except Exception as e:
                print("NFC read error:", e)

            # Yield back to scheduler
            await aio.sleep_ms(10)

        print("NFC polling stopped")

    # FOREGROUND
    def switch_to_foreground(self):

        super().switch_to_foreground()

        self.badge.display.clear()

        # Background color
        self.badge.display.screen.set_style_bg_color(
            lvgl.color_hex(0x1A1A1A),
            0
        )

        # Status label
        self.status_label = lvgl.label(self.badge.display.screen)
        self.status_label.set_style_text_font(
            lvgl.font_montserrat_14,
            0
        )
        self.status_label.set_style_text_color(
            lvgl.color_hex(0xE39810),
            0
        )
        self.status_label.align(
            lvgl.ALIGN.TOP_LEFT,
            5,
            5
        )

        if self.nfc:
            self.status_label.set_text("Tap a card...")
        else:
            self.status_label.set_text("PN532 not found!")

        # UID label
        self.uid_label = lvgl.label(self.badge.display.screen)

        self.uid_label.set_style_text_font(
            lvgl.font_montserrat_28,
            0
        )

        self.uid_label.set_style_text_color(
            lvgl.color_hex(0xFFFFFF),
            0
        )

        self.uid_label.set_long_mode(
            lvgl.label.LONG_MODE.WRAP
        )

        self.uid_label.set_width(400)

        self.uid_label.align(
            lvgl.ALIGN.CENTER,
            25,
            15
        )

        self.uid_label.set_text("")

        # Bottom menu
        self.badge.display.f5("Home")

        # Start async polling
        self.running = True

        try:
            self.nfc_task = aio.create_task(
                self.nfc_loop()
            )

        except Exception as e:
            print("Failed to start NFC task:", e)

        return self

    # MAIN UI LOOP
    def run_foreground(self):

        # EXIT
        if self.badge.keyboard.f5():

            print("Exiting NFC app")

            self.switch_to_background()

            return

        # UPDATE UI FROM ASYNC DATA
        if self.pending_uid:

            uid_tuple = self.pending_uid
            self.pending_uid = None

            uid_hex = ":".join(
                "%02X" % b for b in uid_tuple
            )

            now = time.ticks_ms()

            if (
                self.last_uid is None
                or uid_tuple != self.last_uid
                or time.ticks_diff(now, self.last_seen_time) > 1000
            ):

                self.last_uid = uid_tuple
                self.last_seen_time = now

                print("TAG:", uid_hex)

                if self.status_label:
                    try:
                        self.status_label.set_text(
                            "Tag found!"
                        )
                    except Exception:
                        pass

                if self.uid_label:
                    try:
                        self.uid_label.set_text(
                            uid_hex
                        )
                    except Exception:
                        pass

        # RESET DISPLAY AFTER NO TAG
        now = time.ticks_ms()

        if (
            self.last_seen_time
            and time.ticks_diff(
                now,
                self.last_seen_time
            ) > 4000
        ):

            self.last_uid = None

            if self.status_label:
                try:
                    self.status_label.set_text(
                        "Tap a card..."
                    )
                except Exception:
                    pass

            if self.uid_label:
                try:
                    self.uid_label.set_text("")
                except Exception:
                    pass

    # BACKGROUND
    def run_background(self):
        pass

    # CLEANUP
    def switch_to_background(self):

        print("Stopping NFC app")

        # Stop async loop
        self.running = False

        # Cancel task
        if self.nfc_task:

            try:
                self.nfc_task.cancel()

            except Exception as e:
                print("Task cancel error:", e)

            self.nfc_task = None

        # Delete LVGL objects safely
        if self.uid_label:

            try:
                self.uid_label.delete()
            except Exception:
                pass

            self.uid_label = None

        if self.status_label:

            try:
                self.status_label.delete()
            except Exception:
                pass

            self.status_label = None

        self.badge.display.clear()

        super().switch_to_background()
