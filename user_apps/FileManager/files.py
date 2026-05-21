import os
import lvgl

from apps.base_app import BaseApp
from ui.page import Page


class Files(BaseApp):

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        # UI
        self.page = None
        self.widgets = []

        # filesystem
        self.path = "/"
        self.items = []

        # navigation
        self.selected = 0
        self.offset = 0
        self.max_visible = 8

        # clipboard
        self.clipboard = None

        # rename state
        self.rename_target = None
        self.rename_active = False

    # --------------------------------------------------
    # APP LIFECYCLE
    # --------------------------------------------------
    def switch_to_foreground(self):

        super().switch_to_foreground()

        self.page = Page()
        self.page.create_content()

        # F1 Open
        # F2 Copy / Shift+F2 Paste
        # F3 Delete / Shift+F3 Rename
        # F5 Exit
        self.page.create_menubar([
            "Open",
            "Copy/Paste",
            "Del/Ren",
            "",
            "Exit"
        ])

        self._load()
        self._create_overlay()
        self._draw()

        self.page.replace_screen()

    def switch_to_background(self):

        self._cleanup()
        self.page = None

        super().switch_to_background()

    # --------------------------------------------------
    # CLEANUP
    # --------------------------------------------------
    def _cleanup(self):

        try:
            for w in self.widgets:
                try:
                    w.delete()
                except:
                    pass
        except:
            pass

        self.widgets = []

        for attr in [
            "scroll_label",
            "path_label",
        ]:
            if hasattr(self, attr):
                try:
                    getattr(self, attr).delete()
                except:
                    pass

    # --------------------------------------------------
    # OVERLAY
    # --------------------------------------------------
    def _create_overlay(self):

        # counter
        self.scroll_label = lvgl.label(self.page.scr)

        self.scroll_label.set_style_text_color(
            lvgl.color_hex(0x000000),
            0
        )

        self.scroll_label.align(
            lvgl.ALIGN.TOP_RIGHT,
            -5,
            5
        )

        # path
        self.path_label = lvgl.label(self.page.scr)

        self.path_label.set_style_text_color(
            lvgl.color_hex(0x000000),
            0
        )

        self.path_label.align(
            lvgl.ALIGN.TOP_LEFT,
            5,
            5
        )

    # --------------------------------------------------
    # FILESYSTEM
    # --------------------------------------------------
    def _load(self):

        try:
            self.items = sorted(os.listdir(self.path))
        except:
            self.items = []

        if self.path != "/":
            self.items.insert(0, "..")

        self.selected = 0
        self.offset = 0

    def _full(self, name):

        if name == "..":

            if self.path == "/":
                return "/"

            parts = self.path.rstrip("/").split("/")

            if len(parts) <= 1:
                return "/"

            return "/".join(parts[:-1]) or "/"

        if self.path == "/":
            return "/" + name

        return self.path.rstrip("/") + "/" + name

    def _is_dir(self, path):

        try:
            return (os.stat(path)[0] & 0x4000) != 0
        except:
            return False

    # --------------------------------------------------
    # SCROLL LIMITS
    # --------------------------------------------------
    def _clamp_scroll(self):

        if len(self.items) <= 0:
            self.selected = 0
            self.offset = 0
            return

        if self.selected < 0:
            self.selected = 0

        if self.selected >= len(self.items):
            self.selected = len(self.items) - 1

        max_offset = max(
            0,
            len(self.items) - self.max_visible
        )

        if self.offset < 0:
            self.offset = 0

        if self.offset > max_offset:
            self.offset = max_offset

    # --------------------------------------------------
    # DRAW
    # --------------------------------------------------
    def _draw(self):

        try:

            # clear rows
            for w in self.widgets:
                try:
                    w.delete()
                except:
                    pass

            self.widgets = []

            y = 0

            end = min(
                self.offset + self.max_visible,
                len(self.items)
            )

            for i in range(self.offset, end):

                name = self.items[i]
                full = self._full(name)

                prefix = "[D] " if self._is_dir(full) else "    "

                text = prefix + name

                lbl = lvgl.label(self.page.content)

                lbl.set_text(text)

                # selected row
                if i == self.selected:

                    lbl.set_style_bg_color(
                        lvgl.color_hex(0x222222),
                        0
                    )

                    lbl.set_style_bg_opa(
                        lvgl.OPA.COVER,
                        0
                    )

                    lbl.set_style_text_color(
                        lvgl.color_hex(0xFFFFFF),
                        0
                    )

                else:

                    lbl.set_style_bg_opa(
                        lvgl.OPA.TRANSP,
                        0
                    )

                    lbl.set_style_text_color(
                        lvgl.color_hex(0x000000),
                        0
                    )

                lbl.align(
                    lvgl.ALIGN.TOP_LEFT,
                    5,
                    y
                )

                y += 14

                self.widgets.append(lbl)

            # path
            self.path_label.set_text(self.path)

            # counter
            total = len(self.items)

            if total <= 0:
                pos = 0
            else:
                pos = self.selected + 1

            self.scroll_label.set_text(
                f"{pos}/{total}"
            )

        except Exception as e:
            print("draw error:", e)

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------
    def _move_up(self):

        if self.selected > 0:

            self.selected -= 1

            if self.selected < self.offset:
                self.offset = self.selected

        self._clamp_scroll()
        self._draw()

    def _move_down(self):

        if self.selected < len(self.items) - 1:

            self.selected += 1

            if self.selected >= self.offset + self.max_visible:

                self.offset = (
                    self.selected
                    - self.max_visible
                    + 1
                )

        self._clamp_scroll()
        self._draw()

    # --------------------------------------------------
    # OPEN
    # --------------------------------------------------
    def _open(self):

        if not self.items:
            return

        name = self.items[self.selected]
        path = self._full(name)

        # go up
        if name == "..":

            self.path = path

            self._load()
            self._draw()

            return

        # enter dir
        try:

            if self._is_dir(path):

                self.path = path

                self._load()
                self._draw()

                return

        except:
            return

        # open file
        try:

            with open(path, "r") as f:
                data = f.read(2000)

        except:
            data = "Cannot open file"

        try:

            self.page.create_text_box(
                default_text=data,
                one_line=False
            )

        except:
            pass

    # --------------------------------------------------
    # COPY
    # --------------------------------------------------
    def _copy(self):

        if not self.items:
            return

        name = self.items[self.selected]

        if name == "..":
            return

        self.clipboard = (
            "copy",
            self._full(name)
        )

    # --------------------------------------------------
    # PASTE
    # --------------------------------------------------
    def _paste(self):

        if not self.clipboard:
            return

        mode, src = self.clipboard

        name = src.rstrip("/").split("/")[-1]

        dst = self._full(name)

        try:

            if self._is_dir(src):
                self._copy_dir(src, dst)
            else:
                self._copy_file(src, dst)

        except Exception as e:
            print("paste error:", e)

        self._load()
        self._draw()

    def _copy_file(self, src, dst):

        with open(src, "rb") as f:
            data = f.read()

        with open(dst, "wb") as f:
            f.write(data)

    def _copy_dir(self, src, dst):

        try:
            os.mkdir(dst)
        except:
            pass

        try:

            for item in os.listdir(src):

                s = src.rstrip("/") + "/" + item
                d = dst.rstrip("/") + "/" + item

                try:

                    if self._is_dir(s):
                        self._copy_dir(s, d)
                    else:
                        self._copy_file(s, d)

                except:
                    pass

        except:
            pass

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------
    def _delete(self):

        if not self.items:
            return

        name = self.items[self.selected]

        if name == "..":
            return

        path = self._full(name)

        try:

            if self._is_dir(path):
                self._delete_dir(path)
            else:
                os.remove(path)

        except Exception as e:
            print("delete error:", e)

        self._load()
        self._draw()

    def _delete_dir(self, path):

        try:

            for item in os.listdir(path):

                p = path.rstrip("/") + "/" + item

                try:

                    if self._is_dir(p):
                        self._delete_dir(p)
                    else:
                        os.remove(p)

                except:
                    pass

            os.rmdir(path)

        except:
            pass

    # --------------------------------------------------
    # RENAME
    # --------------------------------------------------
    def _rename(self):

        if not self.items:
            return

        name = self.items[self.selected]

        if name == "..":
            return

        self.rename_target = self._full(name)

        try:

            self.page.create_text_box(
                default_text=name,
                one_line=True
            )

            self.rename_active = True

        except Exception as e:
            print("rename textbox error:", e)

    def _finalize_rename(self, new_name):

        if not self.rename_target:
            return

        base = "/".join(
            self.rename_target.rstrip("/").split("/")[:-1]
        )

        new_path = base + "/" + new_name

        try:

            os.rename(
                self.rename_target,
                new_path
            )

        except Exception as e:
            print("rename error:", e)

        self.rename_target = None
        self.rename_active = False

        self._load()
        self._draw()

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------
    def run_foreground(self):

        try:

            kb = self.badge.keyboard

            # ------------------------------------------
            # RENAME TEXT INPUT MODE
            # ------------------------------------------
            if self.rename_active:

                key, text = self.page.text_box_type(kb)

                # confirm rename
                if kb.f1() or key == kb.ENTER:

                    try:

                        new_name = self.page.close_text_box()

                        self._finalize_rename(
                            new_name.strip()
                        )

                    except Exception as e:
                        print("rename finalize error:", e)

                # cancel
                elif kb.f5() or kb.escape_pressed:

                    try:
                        self.page.close_text_box()
                    except:
                        pass

                    self.rename_target = None
                    self.rename_active = False

                return

            # ------------------------------------------
            # NORMAL MODE
            # ------------------------------------------
            key = kb.read_key()

            shift = kb.shift_pressed

            # UP
            if key == kb.UP:
                self._move_up()

            # DOWN
            elif key == kb.DOWN:
                self._move_down()

            # OPEN
            elif kb.f1():
                self._open()

            # COPY / PASTE
            elif kb.f2():

                if shift:
                    self._paste()
                else:
                    self._copy()

            # DELETE / RENAME
            elif kb.f3():

                if shift:
                    self._rename()
                else:
                    self._delete()

            # reserved
            elif kb.f4():
                pass

            # EXIT
            elif kb.f5():
                self.switch_to_background()

        except Exception as e:
            print("files crash:", e)
