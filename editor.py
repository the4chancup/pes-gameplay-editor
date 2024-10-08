import importlib
import io
import json
import math
import struct
import sys

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSpinBox,
    QWidget,
)

from pes_ai.utils import conv_to_bytes


class SectionItem(QListWidgetItem):
    def __init__(self, offset=None, length=None):
        super().__init__()
        self.offset = offset
        self.length = length


class ValueWidget(QWidget):
    def __init__(self, name: str, value: int | float | bool, disabled=False):
        super().__init__()
        self.name = name
        self.value = value

        self.resize(448, 48)
        self.setMinimumSize(QSize(448, 48))
        self.setMaximumSize(QSize(448, 48))

        self.ui_name = QLabel()
        self.ui_name.setText(self.name)

        match type(self.value).__name__:
            case "int":
                self.ui_value = QSpinBox()
                self.ui_value.setMaximum(65535)
                self.ui_value.setValue(self.value)
            case "float":
                self.ui_value = QDoubleSpinBox()
                self.ui_value.setMaximum(9999.99)
                self.ui_value.setMinimum(-9999.99)
                self.ui_value.setValue(self.value)
                if math.isnan(self.value):
                    disabled = True
            case "bool":
                self.ui_value = QCheckBox()
                self.ui_value.setChecked(self.value)
            case _:
                self.ui_value = QSpinBox()
                self.ui_value.setValue(0)
                disabled = True

        if disabled:
            self.ui_value.setReadOnly(True)
            self.ui_value.setEnabled(False)

        layout = QHBoxLayout()
        layout.addWidget(self.ui_name)
        layout.addStretch()
        layout.addWidget(self.ui_value)
        self.setLayout(layout)

        match type(value).__name__:
            case "bool":
                self.ui_value.toggled.connect(self.update_value)
            case _:
                self.ui_value.setFixedSize(QSize(75, 22))
                self.ui_value.valueChanged.connect(self.update_value)

    def update_value(self, value):
        self.value = value


class Editor(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editor")
        self.resize(1150, 720)
        self.setMinimumSize(QSize(1150, 720))
        self.setMaximumSize(QSize(1150, 720))
        self.act_load_18 = QAction(self)
        self.act_load_18.setObjectName("act_load_18")
        self.act_load_sect = QAction(self)
        self.act_load_sect.setObjectName("act_load_sect")
        self.act_save = QAction(self)
        self.act_save.setObjectName("act_save")
        self.act_save_as = QAction(self)
        self.act_save_as.setObjectName("act_save_as")
        self.act_save_sect = QAction(self)
        self.act_save_sect.setObjectName("act_save_sect")
        self.act_find = QAction(self)
        self.act_find.setObjectName("act_find")
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")
        self.section_list = QListWidget(self.central_widget)
        self.section_list.setObjectName("section_list")
        self.section_list.setGeometry(QRect(10, 45, 200, 640))
        self.value_list = QListWidget(self.central_widget)
        self.value_list.setObjectName("value_list")
        self.value_list.setGeometry(QRect(220, 10, 920, 675))
        self.value_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.value_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.value_list.setFlow(QListView.Flow.LeftToRight)
        self.value_list.setProperty("isWrapping", True)
        self.value_list.setGridSize(QSize(448, 48))
        self.file_list = QComboBox(self.central_widget)
        self.file_list.setObjectName("file_list")
        self.file_list.setGeometry(QRect(10, 10, 200, 25))
        self.setCentralWidget(self.central_widget)
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setObjectName("menu_bar")
        self.menu_bar.setGeometry(QRect(0, 0, 1280, 22))
        self.menu_load = QMenu(self.menu_bar)
        self.menu_load.setObjectName("menu_load")
        self.menu_save = QMenu(self.menu_bar)
        self.menu_save.setObjectName("menu_save")
        self.menu_search = QMenu(self.menu_bar)
        self.menu_search.setObjectName("menu_search")
        self.setMenuBar(self.menu_bar)

        self.menu_bar.addAction(self.menu_load.menuAction())
        self.menu_bar.addAction(self.menu_save.menuAction())
        self.menu_bar.addAction(self.menu_search.menuAction())
        self.menu_load.addAction(self.act_load_18)
        self.menu_load.addSeparator()
        self.menu_load.addAction(self.act_load_sect)
        self.menu_save.addAction(self.act_save)
        self.menu_save.addAction(self.act_save_as)
        self.menu_save.addSeparator()
        self.menu_save.addAction(self.act_save_sect)
        self.menu_search.addAction(self.act_find)

        self.re_translate_ui()

        QMetaObject.connectSlotsByName(self)

        self.act_load_18.triggered.connect(self.load_18_bin)
        self.act_load_sect.triggered.connect(self.load_section_json)
        self.act_save.triggered.connect(self.save_bin)
        self.act_save_sect.triggered.connect(self.save_section_json)
        self.act_find.triggered.connect(self.find_value)
        self.section_list.currentItemChanged.connect(self.load_section)

        self.buffer: io.BytesIO | None = None
        self.filename: str = ""
        self.module = None
        self.head_len: int = 0
        self.idx_len: int = 0
        self.subsections: dict = {}

    def re_translate_ui(self):
        window_title = QCoreApplication.translate("editor", "PES Gameplay Editor", None)
        self.setWindowTitle(window_title)
        load_18_txt = QCoreApplication.translate("editor", "Load 18 Files", None)
        load_18_short = QCoreApplication.translate("editor", "Ctrl+8", None)
        self.act_load_18.setText(load_18_txt)
        self.act_load_18.setShortcut(load_18_short)
        load_sect_txt = QCoreApplication.translate("editor", "Load Section...", None)
        load_sect_short = QCoreApplication.translate("editor", "Ctrl+Shift+L", None)
        self.act_load_sect.setText(load_sect_txt)
        self.act_load_sect.setShortcut(load_sect_short)
        save_txt = QCoreApplication.translate("editor", "Save", None)
        save_short = QCoreApplication.translate("editor", "Ctrl+S", None)
        self.act_save.setText(save_txt)
        self.act_save.setShortcut(save_short)
        save_as_txt = QCoreApplication.translate("editor", "Save As...", None)
        save_as_short = QCoreApplication.translate("editor", "Ctrl+Alt+S", None)
        self.act_save_as.setText(save_as_txt)
        self.act_save_as.setShortcut(save_as_short)
        save_sect_txt = QCoreApplication.translate("editor", "Save Section...", None)
        save_sect_short = QCoreApplication.translate("editor", "Ctrl+Shift+S", None)
        self.act_save_sect.setText(save_sect_txt)
        self.act_save_sect.setShortcut(save_sect_short)
        find_txt = QCoreApplication.translate("editor", "Find", None)
        find_short = QCoreApplication.translate("editor", "Ctrl+F", None)
        self.act_find.setText(find_txt)
        self.act_find.setShortcut(find_short)
        menu_load_title = QCoreApplication.translate("editor", "Load", None)
        self.menu_load.setTitle(menu_load_title)
        menu_save_title = QCoreApplication.translate("editor", "Save", None)
        self.menu_save.setTitle(menu_save_title)
        menu_search_title = QCoreApplication.translate("editor", "Search", None)
        self.menu_search.setTitle(menu_search_title)

    def get_filename(self):
        filters = "Bin file (*.bin);;CPK file (*.cpk)"
        f = QFileDialog.getOpenFileName(self, "CPK file", filter=filters)
        self.filename = f[0]

    def load_bin(self):
        if not self.filename.replace(" ", ""):
            return

        with open(self.filename, "rb") as f:
            self.buffer = io.BytesIO(f.read())

        sect_offs = []
        sect_lens = []
        for i in range(math.ceil(self.head_len / 12) - 1):
            sect_len, _, sect_off = struct.unpack("<3i", self.buffer.read(12))
            sect_lens.append(sect_len)
            sect_offs.append(sect_off)

        del sect_lens[0]
        sect_lens.append(len(self.buffer.getvalue()) - sect_offs[-1])

        self.buffer.seek(self.head_len)
        i = 0
        self.subsections.clear()
        for enc_str in self.buffer.read(self.idx_len).split(b"\x00"):
            if not enc_str:
                continue

            sect_name = enc_str.decode("utf-8")
            sect_dict = {"offset": sect_offs[i], "length": sect_lens[i]}
            self.subsections[sect_name] = sect_dict
            i += 1

        self.section_list.clear()
        for k, v in self.subsections.items():
            item = SectionItem(offset=v["offset"], length=v["length"])
            item.setText(k)
            self.section_list.addItem(item)

    def load_18_bin(self):
        self.get_filename()
        if "constant_match" in self.filename:
            self.module = importlib.import_module("pes_ai.eighteen.match")
            self.head_len = 296
            self.idx_len = 392
        if "constant_player" in self.filename:
            self.module = importlib.import_module("pes_ai.eighteen.player")
            self.head_len = 440
            self.idx_len = 456
        if "constant_team" in self.filename:
            self.module = importlib.import_module("pes_ai.eighteen.team")
            self.head_len = 200
            self.idx_len = 218

        if self.head_len != 0 and self.idx_len != 0:
            self.load_bin()

    def save_section(self, sect: SectionItem):
        if (val_count := self.value_list.count()) in [0, 1]:
            return
        if not getattr(sect, "offset", None):
            return

        sub_chk = 16 if sect.text()[:-2] == "subConcept" else 0
        self.buffer.seek(sect.offset + sub_chk)
        for i in range(val_count):
            val = self.value_list.itemWidget(self.value_list.item(i))
            name = getattr(val, "name")
            value = getattr(val, "value")
            if "null" in name and value == 0:
                data = conv_to_bytes(None)
            else:
                bool_list = getattr(self.module, "one_byte_bools")
                if isinstance(value, bool) and name not in bool_list:
                    data = conv_to_bytes(int(value))
                else:
                    data = conv_to_bytes(value)
            self.buffer.write(data)

    def save_section_json(self):
        if not self.subsections:
            return

        if (val_count := self.value_list.count()) in [0, 1]:
            return

        item = self.section_list.currentItem()
        filename = f"{item.text()[:-2]}.json"
        filters = "JSON file (*.json)"
        f = QFileDialog.getSaveFileName(self, "JSON file", filename, filter=filters)

        if not f[0].replace(" ", ""):
            return

        dict_out = {}
        for i in range(val_count):
            val = self.value_list.itemWidget(self.value_list.item(i))
            dict_out[getattr(val, "name")] = getattr(val, "value")

        with open(f[0], "w") as f:
            json.dump({item.text(): dict_out}, f, indent=4)

    def save_bin(self):
        if not self.subsections:
            return
        # noinspection PyTypeChecker
        self.save_section(self.section_list.currentItem())
        with open(self.filename, "wb") as f:
            self.buffer.seek(0)
            f.write(self.buffer.read())

    def add_value_widget(self, name: str, value: float | int | bool, disabled=False):
        item = QListWidgetItem()
        widget = ValueWidget(name, value, disabled)
        self.value_list.insertItem(self.value_list.count(), item)
        self.value_list.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())

    def load_section(self, curr: SectionItem | None, prev: SectionItem | None):
        if prev:
            self.save_section(prev)

        self.value_list.clear()

        if not curr:
            return
        if not (func := getattr(self.module, f"map_{curr.text()[:-2]}", None)):
            return self.add_value_widget(str(curr.length), curr.offset, True)

        vals = func(self.buffer, curr.offset, curr.length)
        for k, v in vals.items():
            disabled = True if "padding" in k else False
            self.add_value_widget(k, v, disabled)

    def load_section_json(self):
        if not self.subsections:
            return

        filters = "JSON file (*.json)"
        f = QFileDialog.getOpenFileName(self, "JSON file", filter=filters)
        if not f[0].replace(" ", ""):
            return

        with open(f[0], "r") as f:
            data: dict = json.load(f)

        if (sect_name := next(iter(data))) != self.section_list.currentItem().text():
            item = self.section_list.findItems(sect_name, Qt.MatchFlag.MatchExactly)[0]
            index = self.section_list.indexFromItem(item)
            self.section_list.setCurrentIndex(index)

        if (val_count := self.value_list.count()) in [0, 1]:
            return

        for i in range(val_count):
            val = self.value_list.itemWidget(self.value_list.item(i))
            if (name := getattr(val, "name")) not in data[sect_name]:
                continue
            if (value := data[sect_name][name]) == getattr(val, "value"):
                continue

            setattr(val, "value", value)
            match type(value).__name__:
                case "bool":
                    getattr(val, "ui_value").setChecked(value)
                case "NoneType":
                    getattr(val, "ui_value").setValue(0)
                case _:
                    getattr(val, "ui_value").setValue(value)

    def find_value(self):
        if not self.subsections:
            return

        text, ok = QInputDialog.getText(self, "Find", "Find what:")
        if not text.replace(" ", "") and not ok:
            return

        val_count = self.value_list.count()
        for i in range(val_count):
            widget = self.value_list.itemWidget(self.value_list.item(i))
            if text.lower() in getattr(widget, "name").lower():
                self.value_list.setCurrentRow(i)
                getattr(widget, "ui_name").setStyleSheet("font-weight: bold")
                break


if __name__ == "__main__":
    p = QApplication(sys.argv)
    w = Editor()
    w.show()
    sys.exit(p.exec())
