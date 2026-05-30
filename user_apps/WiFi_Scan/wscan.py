import lvgl
import network
import os
import time

from apps.base_app import BaseApp
from ui.page import Page


AUTH_MAP = {
    0: "OPEN",
    1: "WEP",
    2: "WPA",
    3: "WPA2",
    4: "WPA/WPA2",
    5: "WPA3",
}


class Wscan(BaseApp):

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        self.page = None

        self.networks = []
        self.selected = 0
        self.offset = 0
        self.max_visible = 8

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

        self.connected = False
        self.connected_ssid = None

        self.connecting = False
        self.pending_ssid = None

        self.in_info_screen = False

        self.widgets = []

        # MODAL POPUP
        self.modal_root = None
        self.modal_box = None
        self.modal_until = 0

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def switch_to_foreground(self):
        super().switch_to_foreground()

        self.page = Page()
        self.page.create_content()

        self.page.create_menubar([
            "Scan",
            "Save",
            "Clear",
            "Connect",
            "Exit"
        ])

        self._draw_empty()
        self.page.replace_screen()

    def switch_to_background(self):
        self._cleanup()
        self.page = None
        super().switch_to_background()

    def _cleanup(self):
        for w in self.widgets:
            try:
                w.delete()
            except:
                pass
        self.widgets = []

    # --------------------------------------------------
    # MODAL POPUP (TRUE OVERLAY FIX)
    # --------------------------------------------------
    def _popup(self, text):

        try:

            if self.modal_root:
                try:
                    self.modal_root.delete()
                except:
                    pass

            scr = self.page.scr

            # overlay scuro
            self.modal_root = lvgl.obj(scr)
            self.modal_root.set_size(
                lvgl.pct(100),
                lvgl.pct(100)
            )

            self.modal_root.set_style_bg_color(
                lvgl.color_hex(0x000000),
                0
            )

            self.modal_root.set_style_bg_opa(
                lvgl.OPA._70,
                0
            )

            # finestra
            self.modal_box = lvgl.obj(self.modal_root)

            self.modal_box.set_size(220, 90)

            self.modal_box.align(
                lvgl.ALIGN.CENTER,
                0,
                0
            )

            self.modal_box.set_style_bg_color(
                lvgl.color_hex(0xFFFFFF),
                0
            )

            self.modal_box.set_style_bg_opa(
                lvgl.OPA.COVER,
                0
            )

            self.modal_box.set_style_border_width(
                2,
                0
            )

            self.modal_box.set_style_border_color(
                lvgl.color_hex(0x000000),
                0
            )

            lbl = lvgl.label(self.modal_box)

            lbl.set_text(text)

            # FORZA testo nero
            lbl.set_style_text_color(
                lvgl.color_hex(0x000000),
                0
            )

            lbl.set_style_text_font(
                lvgl.font_montserrat_16,
                0
            )

            lbl.align(
                lvgl.ALIGN.CENTER,
                0,
                0
            )

            self.modal_until = (
                time.ticks_ms() + 1500
            )

        except Exception as e:
            print("popup error:", e)

    def _popup_update(self):
        if self.modal_root and time.ticks_ms() > self.modal_until:
            try:
                self.modal_root.delete()
            except:
                pass
            self.modal_root = None
            self.modal_box = None

    # --------------------------------------------------
    # SCAN
    # --------------------------------------------------
    def _scan(self):

        try:
            raw = self.wlan.scan()
        except Exception as e:
            print("scan error:", e)
            return

        self.networks = []

        for ssid, bssid, channel, rssi, auth, hidden in raw:

            try:
                ssid = ssid.decode() if isinstance(ssid, bytes) else str(ssid)
            except:
                ssid = ""

            ssid_str = "HIDDEN" if ssid == "" else ssid
            bssid_str = ":".join("{:02x}".format(x) for x in bssid)
            auth_str = AUTH_MAP.get(auth, str(auth))

            self.networks.append((rssi, auth_str, bssid_str, ssid_str))

        self.networks.sort(key=lambda x: x[0], reverse=True)

        self.selected = 0
        self.offset = 0
        self._draw()

    # --------------------------------------------------
    # DRAW LIST
    # --------------------------------------------------
    def _draw(self):

        for w in self.widgets:
            try:
                w.delete()
            except:
                pass
        self.widgets = []

        if not self.networks:
            self._draw_empty()
            return

        self._ensure_visible()

        y = 0
        end = min(self.offset + self.max_visible, len(self.networks))

        for i in range(self.offset, end):

            rssi, auth, bssid, ssid = self.networks[i]

            line = f"{rssi:>4}  {auth:<8}  {bssid}  {ssid}"

            lbl = lvgl.label(self.page.content)
            lbl.set_text(line)

            if i == self.selected:
                lbl.set_style_bg_color(lvgl.color_hex(0x222222), 0)
                lbl.set_style_bg_opa(lvgl.OPA.COVER, 0)
                lbl.set_style_text_color(lvgl.color_hex(0xFFFFFF), 0)
            else:
                lbl.set_style_bg_opa(lvgl.OPA.TRANSP, 0)
                lbl.set_style_text_color(lvgl.color_hex(0x000000), 0)

            lbl.align(lvgl.ALIGN.TOP_LEFT, 5, y)
            y += 14

            self.widgets.append(lbl)

    def _draw_empty(self):
        lbl = lvgl.label(self.page.content)
        lbl.set_text("Press F1 to scan WiFi")
        lbl.align(lvgl.ALIGN.CENTER, 0, 0)
        self.widgets.append(lbl)

    # --------------------------------------------------
    # SCROLL FIX (ROBUST + ALWAYS VISIBLE)
    # --------------------------------------------------
    def _ensure_visible(self):

        if len(self.networks) == 0:
            self.selected = 0
            self.offset = 0
            return

        # clamp selected
        if self.selected < 0:
            self.selected = 0
        if self.selected >= len(self.networks):
            self.selected = len(self.networks) - 1

        # HARD RULE: selected must always stay inside viewport
        if self.selected < self.offset:
            self.offset = self.selected

        elif self.selected >= self.offset + self.max_visible:
            self.offset = self.selected - self.max_visible + 1

        # clamp offset range
        max_offset = max(0, len(self.networks) - self.max_visible)
        if self.offset < 0:
            self.offset = 0
        if self.offset > max_offset:
            self.offset = max_offset

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    def _save(self):
        try:
            os.makedirs("/notes")
        except:
            pass

        try:
            with open("/notes/Wscan.txt", "a") as f:
                for rssi, auth, bssid, ssid in self.networks:
                    f.write(f"{rssi},{auth},{bssid},{ssid}\n")

            self._popup("SAVED")

        except Exception as e:
            print("save error:", e)
            self._popup("ERROR")

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------
    def _clear(self):
        self.networks = []
        self.selected = 0
        self.offset = 0
        self._draw()

    # --------------------------------------------------
    # NAV
    # --------------------------------------------------
    def _up(self):
        if self.selected > 0:
            self.selected -= 1
        self._ensure_visible()
        self._draw()

    def _down(self):
        if self.selected < len(self.networks) - 1:
            self.selected += 1
        self._ensure_visible()
        self._draw()

    # --------------------------------------------------
    # CONNECT
    # --------------------------------------------------
    def _connect(self):

        if not self.networks:
            return

        ssid = self.networks[self.selected][3]

        if self.connected:
            try:
                self.wlan.disconnect()
            except:
                pass

            self.connected = False
            self.connected_ssid = None
            self.page.set_menubar_button_label(3, "Connect")
            return

        self.connecting = True
        self.pending_ssid = ssid

        self.page.create_text_box(default_text="", one_line=True)

    def _final_connect(self, password):

        try:
            self.wlan.connect(self.pending_ssid, password)

            for _ in range(20):
                if self.wlan.isconnected():
                    break
                time.sleep_ms(200)

            if self.wlan.isconnected():
                self.connected = True
                self.connected_ssid = self.pending_ssid
                self.page.set_menubar_button_label(3, "Disconnect")
                self._popup("CONNECTED")
                self._show_info_screen()
                return

            self._popup("FAILED")

        except Exception as e:
            print(e)
            self._popup("FAILED")

        self.connecting = False

    # --------------------------------------------------
    # INFO SCREEN
    # --------------------------------------------------
    def _show_info_screen(self):

        self.in_info_screen = True

        try:
            self.page.scr.clean()
        except:
            pass

        scr = self.page.scr

        ssid = self.connected_ssid or "unknown"

        try:
            ip = self.wlan.ifconfig()[0]
        except:
            ip = "0.0.0.0"

        lvgl.label(scr).set_text("WiFi Connected")
        lvgl.label(scr).align(lvgl.ALIGN.TOP_MID, 0, 10)

        l1 = lvgl.label(scr)
        l1.set_text(f"SSID: {ssid}")
        l1.align(lvgl.ALIGN.TOP_LEFT, 10, 40)

        l2 = lvgl.label(scr)
        l2.set_text(f"IP: {ip}")
        l2.align(lvgl.ALIGN.TOP_LEFT, 10, 60)

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------
    def run_foreground(self):

        self._popup_update()

        kb = self.badge.keyboard

        if self.in_info_screen:
            if kb.f5():
                self.switch_to_background()
            return

        if self.connecting:

            key, text = self.page.text_box_type(kb)

            if kb.f1() or key == kb.ENTER:
                pwd = self.page.close_text_box()
                self._final_connect(pwd.strip())

            elif kb.f5() or kb.escape_pressed:
                self.connecting = False
                self.page.close_text_box()

            return

        key = kb.read_key()

        if key == kb.UP:
            self._up()

        elif key == kb.DOWN:
            self._down()

        elif kb.f1():
            self._scan()

        elif kb.f2():
            self._save()

        elif kb.f3():
            self._clear()

        elif kb.f4():
            self._connect()

        elif kb.f5():
            self.switch_to_background()
