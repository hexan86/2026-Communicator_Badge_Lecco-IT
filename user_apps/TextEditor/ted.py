import os
import lvgl

from apps.base_app import BaseApp
from ui.page import Page


EDITOR_DIR = "/notes"

MODE_BROWSER = 0
MODE_EDITOR = 1
MODE_SAVE_AS = 2


class TEd(BaseApp):

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        # UI
        self.page = None
        self.widgets = []

        # filesystem
        self.items = []
        self.selected = 0

        # editor state
        self.filename = None
        self.modified = False
        self.cached_text = ""

        # start in editor
        self.mode = MODE_EDITOR

    # --------------------------------------------------
    # LIFECYCLE
    # --------------------------------------------------
    def switch_to_foreground(self):
        super().switch_to_foreground()

        self.page = Page()
        self.page.create_infobar(("Text Editor", "Untitled"))
        self.page.create_content()

        # Menubar STATICA: creata una volta sola qui e mai più rigenerata
        self.page.create_menubar([
            "F1 Open",
            "F2 Save",
            "F3 SaveAs",
            "F4 New",
            "F5 Exit"
        ])

        self._open_editor("")
        self.page.replace_screen()

    def switch_to_background(self):
        self._clear_widgets()
        self.page = None
        super().switch_to_background()

    # --------------------------------------------------
    # FILESYSTEM
    # --------------------------------------------------
    def _ensure_dir(self):
        try:
            os.mkdir(EDITOR_DIR)
        except:
            pass

    def _load_files(self):
        self._ensure_dir()
        try:
            self.items = sorted(os.listdir(EDITOR_DIR))
        except:
            self.items = []
        self.selected = 0

    def _full(self, name):
        return f"{EDITOR_DIR}/{name}"

    def _is_printable_char(self, key, kb):
        if key is None:
            return False
        # Evita che i tasti di controllo hardware vengano scritti come testo nel file
        if key in (kb.UP, kb.DOWN, kb.LEFT, kb.RIGHT, kb.ENTER, kb.BS, kb.TAB):
            return False
        if isinstance(key, str) and (key.startswith("F") and key[1:].isdigit()):
            return False
        return isinstance(key, str) and len(key) == 1

    # --------------------------------------------------
    # BROWSER
    # --------------------------------------------------
    def _open_browser(self):
        # Salviamo lo stato del testo corrente nell'editor prima di entrare nel browser
        if hasattr(self.page, "text_box") and self.page.text_box:
            self.cached_text = self.page.text_box.get_text()

        self.mode = MODE_BROWSER
        self._load_files()
        self._draw_browser()

    def _draw_browser(self):
        self._clear_widgets()

        if not self.items:
            lbl = lvgl.label(self.page.content)
            lbl.set_text("<empty>")
            lbl.align(lvgl.ALIGN.TOP_LEFT, 5, 10)
            self.widgets.append(lbl)
            
            self.page.infobar_left.set_text("Browser")
            self.page.infobar_right.set_text("F1 Back")
            return

        y = 10
        for i, name in enumerate(self.items):
            lbl = lvgl.label(self.page.content)
            lbl.set_text(name)

            lbl.set_style_text_color(lvgl.color_hex(0x000000), 0)
            lbl.set_style_bg_opa(lvgl.OPA.TRANSP, 0)

            if i == self.selected:
                lbl.set_style_bg_color(lvgl.color_hex(0x222222), 0)
                lbl.set_style_bg_opa(lvgl.OPA.COVER, 0)
                lbl.set_style_text_color(lvgl.color_hex(0xFFFFFF), 0)

            lbl.align(lvgl.ALIGN.TOP_LEFT, 5, y)
            y += 14

            self.widgets.append(lbl)

        self.page.infobar_left.set_text(f"Files: {len(self.items)}")
        self.page.infobar_right.set_text("ENTER Open | F1 Back")

    def _move_up(self):
        if self.selected > 0:
            self.selected -= 1
        self._draw_browser()

    def _move_down(self):
        if self.selected < len(self.items) - 1:
            self.selected += 1
        self._draw_browser()

    def _open(self):
        if not self.items:
            return

        name = self.items[self.selected]
        path = self._full(name)

        try:
            with open(path, "r") as f:
                data = f.read()
        except:
            data = ""

        self.filename = name
        self.cached_text = data
        self.modified = False
        self._open_editor(data)

    # --------------------------------------------------
    # EDITOR
    # --------------------------------------------------
    def _open_editor(self, text=""):
        self.mode = MODE_EDITOR
        self._clear_widgets()

        self.page.create_text_box(
            default_text=text,
            one_line=False
        )

        self.page.text_box.set_width(lvgl.pct(98))
        self.page.text_box.set_height(lvgl.pct(90))

        self._update_header()

    def _update_header(self):
        if not self._ui_ok():
            return

        name = self.filename or "Untitled"
        if self.modified:
            name = "*" + name

        self.page.infobar_left.set_text(name)
        self.page.infobar_right.set_text("F1 Open | F2 Save | F3 SaveAs")

    def _ui_ok(self):
        return self.page is not None and hasattr(self.page, "content")

    def _clear_widgets(self):
        for w in self.widgets:
            try:
                w.delete()
            except:
                pass
        self.widgets = []

    def _new(self):
        self.filename = None
        self.modified = False
        self.cached_text = ""
        self._open_editor("")

    # --------------------------------------------------
    # SAVE & SAVE AS
    # --------------------------------------------------
    def _save(self):
        if not self.filename:
            self._save_as()
            return

        try:
            path = self._full(self.filename)
            with open(path, "w") as f:
                f.write(self.page.text_box.get_text())

            self.modified = False
            self._update_header()
        except Exception as e:
            print("SAVE ERROR:", e)

    def _save_as(self):
        self.mode = MODE_SAVE_AS
        self.cached_text = self.page.text_box.get_text()

        self._clear_widgets()

        self.page.create_text_box(
            default_text=self.filename or "new.txt",
            one_line=True
        )

        self.page.infobar_left.set_text("Save As")
        self.page.infobar_right.set_text("ENTER Save | F5 Cancel")

    def _save_as_finalize(self, name):
        if not name:
            self._open_editor(self.cached_text)
            return

        if not name.endswith(".txt"):
            name += ".txt"

        self.filename = name
        self.mode = MODE_EDITOR
        self._open_editor(self.cached_text)
        self._save()

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------
    def run_foreground(self):
        try:
            if not self._ui_ok():
                return

            kb = self.badge.keyboard

            # INTERCETTAZIONE DI DI REFRESH/SHORTCUTS (Previene ghosting dei tasti)
            if kb.f5():
                if self.mode == MODE_SAVE_AS or self.mode == MODE_BROWSER:
                    self.mode = MODE_EDITOR
                    self._open_editor(self.cached_text)
                else:
                    self.switch_to_background()
                return

            # ---------------- MODALITÀ: EDITOR ----------------
            if self.mode == MODE_EDITOR:
                if kb.f1():
                    self._open_browser()
                    return
                elif kb.f2():
                    self._save()
                    return
                elif kb.f3():
                    self._save_as()
                    return
                elif kb.f4():
                    self._new()
                    return

                key = kb.read_key()
                if key is not None:
                    current = self.page.text_box.get_text()

                    if key == kb.BS:
                        self.page.text_box.set_text(current[:-1])
                    elif key == kb.ENTER:
                        self.page.text_box.set_text(current + "\n")
                    elif self._is_printable_char(key, kb):
                        self.page.text_box.set_text(current + key)

                    self.modified = True
                    self._update_header()
                return

            # ---------------- MODALITÀ: BROWSER ----------------
            if self.mode == MODE_BROWSER:
                if kb.f1():  # Torna all'editor recuperando la cache
                    self.mode = MODE_EDITOR
                    self._open_editor(self.cached_text)
                    return

                key = kb.read_key()
                if key == kb.UP:
                    self._move_up()
                elif key == kb.DOWN:
                    self._move_down()
                elif key == kb.ENTER:
                    self._open()
                return

            # ---------------- MODALITÀ: SAVE AS ----------------
            if self.mode == MODE_SAVE_AS:
                key = kb.read_key()
                if key is not None:
                    if key == kb.ENTER:
                        name = self.page.text_box.get_text().strip()
                        self._save_as_finalize(name)
                    elif key == kb.BS:
                        current = self.page.text_box.get_text()
                        self.page.text_box.set_text(current[:-1])
                    elif self._is_printable_char(key, kb):
                        current = self.page.text_box.get_text()
                        self.page.text_box.set_text(current + key)
                return

        except Exception as e:
            print("EDITOR ERROR:", e)
