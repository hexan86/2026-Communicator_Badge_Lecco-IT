import network
import time
import urequests
import ujson
from collections import deque
import lvgl

from apps.base_app import BaseApp
from net.net import MY_ADDRESS
from ui.chat import Chat


# -------------------------------------------------
# CONFIG LOADER
# -------------------------------------------------
def load_config(path="/data/cnf.ai"):
    cfg = {}

    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()

        print("[AI_BOT] Config loaded")

    except Exception as e:
        print("[AI_BOT] Config error:", e)

    return cfg


# -------------------------------------------------
# APP
# -------------------------------------------------
class AI_Bot(BaseApp):

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        self.cfg = load_config("/data/cnf.ai")

        self.channels = {1: deque([], 100)}
        self.active_channel = 1

        self.ai_queue = deque([], 10)
        self.ai_response_queue = deque([], 10)
        self.ai_busy = False

        self.page = None
        self.channel_messages_updated = True

        self.input_active = False

        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)

    # -------------------------------------------------
    # WIFI
    # -------------------------------------------------
    def connect_wifi(self):

        ssid = self.cfg.get("SSID")
        password = self.cfg.get("PASS")

        if not ssid or not password:
            print("[AI_BOT] Missing WiFi config")
            return False

        print("[AI_BOT] Connecting WiFi...")
        self.wifi.connect(ssid, password)

        for _ in range(8):
            if self.wifi.isconnected():
                print("[AI_BOT] WiFi OK:", self.wifi.ifconfig())
                return True
            time.sleep(1)

        print("[AI_BOT] WiFi FAILED")
        return False

    # -------------------------------------------------
    # AI CALL (ROBUST PARSER)
    # -------------------------------------------------
    def ask_ai(self, prompt: str) -> str:

        url = "https://api.openai.com/v1/responses"

        headers = {
            "Authorization": "Bearer " + self.cfg.get("API_KEY", ""),
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-5.4-mini",
            "input": prompt,
            "max_output_tokens": 120
        }

        try:
            r = urequests.post(url, headers=headers, data=ujson.dumps(payload))
            data = r.json()
            r.close()

            if "output" in data:
                try:
                    return data["output"][0]["content"][0]["text"]
                except:
                    pass

            if "choices" in data:
                try:
                    return data["choices"][0]["message"]["content"]
                except:
                    pass

            if "error" in data:
                return "API_ERROR: " + str(data["error"])

            return str(data)

        except Exception as e:
            return "EXC: " + str(e)

    # -------------------------------------------------
    # SEND MESSAGE
    # -------------------------------------------------
    def send(self, text):

        self.channels[self.active_channel].append(
            (MY_ADDRESS, "You", text)
        )

        self.ai_queue.append(text)
        self.channel_messages_updated = True

    # -------------------------------------------------
    # AI WORKER
    # -------------------------------------------------
    def ai_worker(self):

        if self.ai_busy:
            return

        if not self.ai_queue:
            return

        if not self.wifi.isconnected():
            return

        self.ai_busy = True

        prompt = self.ai_queue.popleft()

        reply = self.ask_ai(prompt)

        self.ai_response_queue.append(reply)

        self.ai_busy = False

    # -------------------------------------------------
    # F3 RESET CHAT
    # -------------------------------------------------
    def _reset_chat(self):

        self.channels[self.active_channel] = deque([], 100)

        self.channel_messages_updated = True

        if not self.page:
            return

        try:
            if hasattr(self.page, "message_rows"):
                self.page.message_rows.delete()

            self.page.add_message_rows(1)

            lvgl.screen_active().invalidate()

        except Exception as e:
            print("[AI_BOT] UI reset error:", e)

        print("[AI_BOT] Chat reset OK")

    # -------------------------------------------------
    # SCROLL FIX (NEW)
    # -------------------------------------------------
    def handle_scroll(self):

        key = self.badge.keyboard.read_key()

        if key is None:
            return

        scroll = 20

        if self.badge.keyboard.shift_pressed:
            scroll = 60

        if key == self.badge.keyboard.UP:
            if self.page:
                self.page.scroll_up(scroll)

        elif key == self.badge.keyboard.DOWN:
            if self.page:
                self.page.scroll_down(scroll)

    # -------------------------------------------------
    # UI INIT
    # -------------------------------------------------
    def switch_to_foreground(self):
        super().switch_to_foreground()

        self.page = Chat(
            infobar_contents=("AI Chat", "OFFLINE"),
            menubar_labels=("F1 WiFi", "F2 Input", "F3 Clear", "", "F5 Exit"),
            messages=[]
        )

        self.page.add_message_rows(1)
        self.page.replace_screen()

        self.page.content.set_style_border_width(6, 0)
        self.page.content.set_style_border_color(lvgl.color_hex(0x3A3A3A), 0)
        self.page.content.set_style_bg_color(lvgl.color_hex(0x1B1B1B), 0)

    # -------------------------------------------------
    # INPUT
    # -------------------------------------------------
    def handle_input(self):

        if self.badge.keyboard.f2():
            self.input_active = True
            self.page.create_text_box(
                default_text="",
                one_line=True,
                char_limit=120
            )

        if not self.input_active:
            return

        key, text = self.page.text_box_type(self.badge.keyboard)

        if self.badge.keyboard.escape_pressed:
            self.page.close_text_box()
            self.input_active = False
            return

        if key == self.badge.keyboard.ENTER:
            msg = self.page.close_text_box()
            self.input_active = False

            if msg:
                self.send(msg)

    # -------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------
    def run_foreground(self):

        if self.badge.keyboard.f5():
            self.switch_to_background()
            return

        if self.badge.keyboard.f1():
            self.connect_wifi()

        if self.badge.keyboard.f3():
            self._reset_chat()

        if self.page:
            status = "WiFi" if self.wifi.isconnected() else "OFF"
            self.page.infobar_right.set_text(status)

        self.handle_input()

        # NEW: scroll handler
        self.handle_scroll()

        self.ai_worker()

        if self.ai_response_queue:

            reply = self.ai_response_queue.popleft()

            self.channels[self.active_channel].append(
                (MY_ADDRESS, "AI", reply)
            )

            self.channel_messages_updated = True

        if self.page and self.channel_messages_updated:

            msgs = self.channels[self.active_channel]

            display = [(m[1], m[2]) for m in msgs]

            self.page.populate_message_rows(display)

            self.channel_messages_updated = False
