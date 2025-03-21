"""
NewGAN Replacement Management Tool
"""
import toga
from toga.style.pack import COLUMN, ROW
import os
import logging
import shutil
from config_manager import Config_Manager
from profile_manager import Profile_Manager
from mapper import Mapper
from rtfparser import RTF_Parser
from reporter import Reporter
from xmlparser import XML_Parser
import webbrowser
import requests


class SourceSelection(toga.Selection):
    def __init__(self, id=None, style=None, items=None, on_change=None, enabled=True):
        super().__init__(
            id=id, style=style, items=items, on_change=on_change, enabled=enabled
        )

    def add_item(self, item):
        self._items.append(item)

    def remove_item(self, item):
        row = self._items.find(item)
        self._items.remove(row)


class NewGANManager(toga.App):
    def __init__(self):
        super().__init__()

    def startup(self):
        """
        Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        # Logging setup
        formatter = logging.Formatter("%(asctime)s | %(name)s: %(message)s")
        fh = logging.FileHandler(str(self.paths.app) + "/newgan.log")
        fh.setFormatter(formatter)
        self.logger = logging.getLogger("NewGAN App")
        self.logger.setLevel(logging.DEBUG)
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        self.logger.info(
            "Starting Application\n------------------------------------------------"
        )
        self.logger.info(str(self.paths.app))
        self.facepack_dirs = set(
            [
                "African",
                "Asian",
                "Caucasian",
                "Central European",
                "EECA",
                "Italmed",
                "MENA",
                "MESA",
                "SAMed",
                "Scandinavian",
                "Seasian",
                "South American",
                "SpanMed",
                "YugoGreek",
            ]
        )
        self.mode_info = {
            "Overwrite": "Overwrites already replaced faces",
            "Preserve": "Preserves already replaced faces",
            "Generate": "Generates mapping from scratch.",
        }
        os.makedirs(str(self.paths.app) + "/.config", exist_ok=True)
        if not os.path.isfile(str(self.paths.app) + "/.user/cfg.json"):
            shutil.copyfile(
                str(self.paths.app) + "/.user/default_cfg.json",
                str(self.paths.app) + "/.user/cfg.json",
            )

        self.logger.info("Loading current profile")
        self.profile_manager = Profile_Manager(
            Config_Manager().get_latest_prf(str(self.paths.app) + "/.user/cfg.json"),
            str(self.paths.app),
        )
        self.profile_manager.migrate_config()
        self.logger.info("Creating GUI")
        self.main_box = toga.Box()
        self.logger.info("Created main box")

        self.hook = "https://discord.com/api/webhooks/796137178328989768/ETMNtPVb-PHuZPayC5G5MZD24tdDi5jmG6jAgjZXg0FDOXjy-VIabATXPco05qLIr4ro"

        # CREATE MENUBAR
        troubleshooting = toga.Command(
            lambda e=None,
            u="https://github.com/Maradonna90/NewGAN-Manager/wiki/Troubleshooting": self.open_link(
                u
            ),
            text="Troubleshooting",
            group=toga.Group.HELP,
            section=1,
        )
        usage = toga.Command(
            lambda e=None,
            u="https://www.youtube.com/watch?v=iJqZNp0nomM": self.open_link(u),
            text="User Guide",
            group=toga.Group.HELP,
            section=0,
        )

        faq = toga.Command(
            lambda e=None,
            u="https://github.com/Maradonna90/NewGAN-Manager/wiki/FAQ": self.open_link(
                u
            ),
            text="FAQ",
            group=toga.Group.HELP,
            section=2,
        )

        discord = toga.Command(
            lambda e=None, u="https://discord.gg/UfRpJVc": self.open_link(u),
            text="Discord",
            group=toga.Group.HELP,
            section=3,
        )

        self.commands.add(discord, faq, troubleshooting, usage)

        label_width = 125
        # TOP Profiles
        prf_box = toga.Box()
        self.logger.info("Created prf_box")

        prf_inp = toga.TextInput()
        self.logger.info("Created prf_inp")

        self.prfsel_box = toga.Box()
        prf_lab = toga.Label(text="Create Profile: ")
        prf_lab.style.update(width=label_width)

        prfsel_lab = toga.Label(text="Select Profile: ")
        prfsel_lab.style.update(width=label_width)
        self.prfsel_lst = SourceSelection(
            items=list(self.profile_manager.config["Profile"].keys()),
            on_change=self._set_profile_status,
        )
        self.prfsel_lst.value = self.profile_manager.cur_prf
        prfsel_btn = toga.Button(
            text="Delete",
            on_press=lambda e=None, c=self.prfsel_lst: self._delete_profile(c),
        )
        prf_btn = toga.Button(
            text="Create",
            on_press=lambda e=None, d=prf_inp, c=self.prfsel_lst: self._create_profile(
                d, c
            ),
        )

        self.main_box.add(prf_box)
        prf_box.add(prf_lab)
        prf_box.add(prf_inp)
        prf_box.add(prf_btn)
        prf_lab.style.update(padding_top=7)
        prf_inp.style.update(direction=ROW, padding=(0, 20), flex=1)

        self.main_box.add(self.prfsel_box)
        self.prfsel_box.add(prfsel_lab)
        self.prfsel_box.add(self.prfsel_lst)
        self.prfsel_box.add(prfsel_btn)
        self.prfsel_lst.style.update(direction=ROW, padding=(0, 20), flex=1)
        prfsel_lab.style.update(padding_top=7)

        # MID Path selections
        dir_box = toga.Box()
        dir_lab = toga.Label(text="Select Image Directory: ")
        dir_lab.style.update(width=label_width)
        self.dir_inp = toga.TextInput(
            readonly=True, value=self.profile_manager.prf_cfg["img_dir"]
        )
        self.dir_inp.style.update(direction=ROW, padding=(0, 20), flex=1)
        self.dir_btn = toga.Button(
            text="...", on_press=self.action_select_folder_dialog, enabled=False
        )

        rtf_box = toga.Box()
        rtf_lab = toga.Label(text="RTF File: ")
        rtf_lab.style.update(width=label_width)
        self.rtf_inp = toga.TextInput(
            readonly=True, value=self.profile_manager.prf_cfg["rtf"]
        )
        self.rtf_inp.style.update(direction=ROW, padding=(0, 20), flex=1)
        self.rtf_btn = toga.Button(
            text="...", on_press=self.action_open_file_dialog, enabled=False
        )

        self.main_box.add(dir_box)
        self.main_box.add(rtf_box)
        dir_box.add(dir_lab)
        dir_box.add(self.dir_inp)
        dir_box.add(self.dir_btn)
        rtf_box.add(rtf_lab)
        rtf_box.add(self.rtf_inp)
        rtf_box.add(self.rtf_btn)
        dir_lab.style.update(padding_top=7)
        rtf_lab.style.update(padding_top=7)

        gen_mode_box = toga.Box()
        self.genmde_lab = toga.Label(text="Mode: ")
        self.genmde_lab.style.update(width=label_width)
        self.genmdeinfo_lab = toga.Label(text=self.mode_info["Generate"])
        self.gendup = toga.Switch(text="Allow Duplicates?", value=True)
        self.gen_with_r_prefix = toga.Switch(
            text="Append r- prefix? (needed for FM24)", value=True
        )
        self.genmde_lst = SourceSelection(
            items=list(self.mode_info.keys()), on_change=self.update_label
        )
        self.genmde_lst.value = "Generate"
        self.genmde_lst.style.update(direction=ROW, padding=(0, 20), flex=1)
        self.genmde_lab.style.update(padding_top=7)
        self.genmdeinfo_lab.style.update(padding_top=7)
        self.gendup.style.update(padding_top=7, padding_left=20)
        self.gen_with_r_prefix.style.update(padding_top=7, padding_left=20)

        gen_mode_box.add(self.genmde_lab)
        gen_mode_box.add(self.genmde_lst)
        gen_mode_box.add(self.genmdeinfo_lab)
        gen_mode_box.add(self.gendup)
        gen_mode_box.add(self.gen_with_r_prefix)
        self.main_box.add(gen_mode_box)
        # BOTTOM Generation
        gen_box = toga.Box()
        self.gen_btn = toga.Button(
            text="Replace Faces", on_press=self._replace_faces, enabled=False
        )
        self.gen_btn.style.update(padding_bottom=20)
        self.gen_lab = toga.Label(text="")

        self.gen_prg = toga.ProgressBar(max=100)
        # self.gen_prg = Progressbar(label=self.gen_lab)
        gen_box.add(self.gen_btn)
        gen_box.add(self.gen_lab)
        gen_box.add(self.gen_prg)
        self.main_box.add(gen_box)
        self.gen_prg.style.update(width=570, alignment="center")
        self.gen_lab.style.update(
            padding_top=20, padding_bottom=20, width=100, alignment="center"
        )

        # Report bad image
        rep_box = toga.Box()
        self.rep_lab = toga.Label(text="Player UID: ")
        self.rep_lab.style.update(width=label_width)
        self.rep_inp = toga.TextInput(on_change=self.change_image)
        self.rep_img = toga.ImageView(toga.Image("resources/logo.png"))
        self.rep_img.style.update(height=180)
        self.rep_img.style.update(width=180)
        self.rep_btn = toga.Button(
            text="Report", on_press=self.send_report, enabled=False
        )

        rep_box.add(self.rep_lab)
        rep_box.add(self.rep_inp)
        rep_box.add(self.rep_img)
        rep_box.add(self.rep_btn)
        self.main_box.add(rep_box)
        self.rep_lab.style.update(padding_top=10)
        self.rep_inp.style.update(direction=ROW, padding=(0, 20), flex=1)

        # END config
        self.prfsel_box.style.update(padding_bottom=20)
        dir_box.style.update(padding_bottom=20)
        prf_box.style.update(padding_bottom=20)
        rtf_box.style.update(padding_bottom=20)
        gen_mode_box.style.update(padding_bottom=20)
        rep_box.style.update(padding_top=20)
        gen_box.style.update(direction=COLUMN, alignment="center")
        self.main_box.style.update(direction=COLUMN, padding=30, alignment="center")

        self.main_window = toga.MainWindow(title=self.formal_name, size=(1000, 600))
        self.main_window.content = self.main_box
        self.main_window.show()

        # self.check_for_update()
        self.set_btns(True)

    def open_link(self, url):
        webbrowser.open(url)

    def update_label(self, widget):
        self.logger.info("Updating generation label")
        self.genmdeinfo_lab.text = self.mode_info[widget.value]

    def set_btns(self, value):
        if self.profile_manager.cur_prf == "No Profile":
            self.gen_btn.enabled = False
            self.dir_btn.enabled = False
            self.rtf_btn.enabled = False
            self.rep_btn.enabled = False
        else:
            self.gen_btn.enabled = value
            self.dir_btn.enabled = value
            self.rtf_btn.enabled = value
            self.rep_btn.enabled = value

    def _set_profile_status(self, e):
        self.logger.info("switch profile: {}".format(e.value))
        if e.value is None:
            self.logger.info("catch none {}".format(self.profile_manager.cur_prf))
        elif e.value == self.profile_manager.cur_prf:
            self.logger.info("catch same values")

        else:
            name = e.value
            self.profile_manager.load_profile(name)
            self._refresh_inp()
            self.set_btns(True)
            Config_Manager().save_config(
                str(self.paths.app) + "/.user/cfg.json", self.profile_manager.config
            )

    def _refresh_inp(self, clear=False):
        self.logger.info("Refresh Input Buttons")
        if clear:
            self.dir_inp.value = None
            self.rtf_inp.value = None
        else:
            self.dir_inp.value = self.profile_manager.prf_cfg["img_dir"]
            self.rtf_inp.value = self.profile_manager.prf_cfg["rtf"]

    def _create_profile(self, ent, c):
        name = ent.value
        self.profile_manager.create_profile(name)
        ent.value = None
        c.add_item(name)

    def _delete_profile(self, c):
        prf = c.value
        self.profile_manager.delete_profile(prf)
        c.remove_item(prf)
        self._refresh_inp(True)
        self.set_btns(False)

    async def _throw_error(self, msg):
        self.logger.info("Error window {}:".format(msg))
        await self.main_window.error_dialog("Error", msg)

    async def _show_info(self, msg):
        self.logger.info("Info window: {}".format(msg))
        info = await self.main_window.info_dialog("Info", msg)

    async def action_select_folder_dialog(self, widget):
        self.logger.info("Select Folder...")
        try:
            path_name = await self.main_window.select_folder_dialog(
                title="Select image root folder"
            )
            path_name = str(path_name)
            self.logger.info(path_name)
            self.dir_inp.value = path_name + "/"
            self.profile_manager.prf_cfg["img_dir"] = path_name + "/"
            Config_Manager().save_config(
                str(self.paths.app)
                + "/.user/"
                + self.profile_manager.cur_prf
                + ".json",
                self.profile_manager.prf_cfg,
            )

        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)
            pass

    async def action_open_file_dialog(self, widget):
        self.logger.info("Select File...")
        try:
            fname = await self.main_window.open_file_dialog(
                title="Open RTF file", multiple_select=False, file_types=["rtf"]
            )
            self.logger.info("Created file-dialog")
            if fname is not None:
                fname = str(fname)
                self.rtf_inp.value = fname
                self.profile_manager.prf_cfg["rtf"] = fname
                self.logger.info("RTF file: " + fname)
                Config_Manager().save_config(
                    str(self.paths.app)
                    + "/.user/"
                    + self.profile_manager.cur_prf
                    + ".json",
                    self.profile_manager.prf_cfg,
                )
            else:
                self.profile_manager.prf_cfg["rtf"] = ""
                self.rtf_inp.value = ""
                Config_Manager().save_config(
                    str(self.paths.app)
                    + "/.user/"
                    + self.profile_manager.cur_prf
                    + ".json",
                    self.profile_manager.prf_cfg,
                )
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)
            pass

    def _replace_faces(self, widget):
        self.logger.info("Start Replace Faces")
        # get values from UI elements
        rtf = self.profile_manager.prf_cfg["rtf"]
        img_dir = self.profile_manager.prf_cfg["img_dir"]
        profile = self.profile_manager.cur_prf
        mode = self.genmde_lst.value
        if not os.path.isfile(rtf):
            self._throw_error("The RTF file doesn't exist!")
            self.gen_prg.stop()
            self.profile_manager.prf_cfg["rtf"] = ""
            return
        if not os.path.isdir(img_dir):
            self._throw_error("The image directory doesn't exist!")
            self.gen_prg.stop()
            self.profile_manager.prf_cfg["img_dir"] = ""
            return
        # Check if valid image_directory contains all the needed subfolders
        img_dirs = set()
        for entry in os.scandir(img_dir):
            if entry.is_dir():
                img_dirs.add(entry.name)
        for fp_dir in self.facepack_dirs:
            if fp_dir not in img_dirs:
                self._throw_error(
                    "Folder {} is missing in the image directory".format(fp_dir)
                )
                self.gen_prg.stop()
                return
        self.logger.info("rtf: {}".format(rtf))
        self.logger.info("img_dir: {}".format(img_dir))
        self.logger.info("profile: {}".format(profile))
        self.logger.info("mode: {}".format(mode))
        self.set_btns(False)
        self.gen_prg.start()
        self.gen_lab.text = "Parsing RTF"
        yield 0.1
        rtf_parser = RTF_Parser()
        if not rtf_parser.is_rtf_valid(rtf):
            self._throw_error("The RTF file is invalid!")
            self.gen_prg.stop()
            return
        rtf_data = rtf_parser.parse_rtf(rtf)
        self.gen_prg.value += 20
        self.gen_lab.text = "Map player to ethnicity"
        yield 0.1
        mapping_data = Mapper(img_dir, self.profile_manager).generate_mapping(
            rtf_data, mode, self.gendup.value
        )
        self.gen_prg.value += 60
        self.gen_lab.text = "Generate config.xml"
        yield 0.1
        self.profile_manager.write_xml(mapping_data, self.gen_with_r_prefix.value)
        # save profile metadata (used pics and config.xml)
        self.gen_lab.text = "Save metadata for profile"
        self.gen_prg.value += 10
        yield 0.1
        Config_Manager().save_config(
            str(self.paths.app) + "/.user/" + profile + ".json",
            self.profile_manager.prf_cfg,
        )
        self.gen_prg.value += 10
        yield 0.1
        self.gen_lab.text = "Finished! :)"
        yield 0.1
        # self._show_info("Finished! :)")
        self.gen_prg.stop()
        self.gen_prg.value = 0
        self.gen_lab.text = ""
        self.set_btns(True)
        yield 0.1

    def change_image(self, id):
        self.logger.info("try to change image preview")
        uid = id.value
        if len(uid) >= 7:
            try:
                img_path = XML_Parser().get_imgpath_from_uid(
                    self.profile_manager.prf_cfg["img_dir"] + "config.xml", uid
                )
                img_path = self.profile_manager.prf_cfg["img_dir"] + img_path + ".png"
                self.rep_img.image = toga.Image(img_path)
                self.logger.info("change image preview to: {}".format(img_path))
            except Exception as e:
                self.logger.info("changing image preview failed!")
                self.logger.info(e)
                return
        return

    def send_report(self, e):
        uid = self.rep_inp.value
        if len(uid) >= 7:
            rep = Reporter(
                self.hook, self.profile_manager.prf_cfg["img_dir"] + "config.xml"
            )
            res = rep.send_report(uid)
            if res:
                self._show_info("Thanks for Reporting!")
                self.rep_img.image = toga.Image("resources/logo.png")
                self.rep_inp.value = ""
            else:
                self._throw_error("Player with ID {} doesn't exist!".format(uid))
                self.rep_img.image = toga.Image("resources/logo.png")
                self.rep_inp.value = ""

    def check_for_update(self):
        try:
            r = requests.get(
                "https://raw.githubusercontent.com/Maradonna90/NewGAN-Manager/master/version",
                timeout=1,
            )
        except:
            self.logger.info("check update timeout exceeded!")
            return
        if r.text.strip() != self.version:
            self._show_info("There is a new version. Please Update!")
            self.open_link(
                "https://github.com/Maradonna90/NewGAN-Manager/releases/latest"
            )


def main():
    return NewGANManager()
