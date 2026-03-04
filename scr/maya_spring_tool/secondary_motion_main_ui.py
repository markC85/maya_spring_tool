from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIntValidator, QDoubleValidator
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QScrollArea,
    QWidget,
    QPushButton,
    QLabel
)
from maya import OpenMayaUI, cmds
from shiboken6 import wrapInstance
from maya_spring_tool.scr.maya_spring_tool.secondary_motion_backend import apply_secondary_motion_additive, delete_anim_layer_by_name
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


def get_maya_main_window() -> None:
    """
    Attach the QTWidgets to the maya main window
    so that it will act like it belongs to maya
    to help prevent bugs and crashes
    """
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def show_ui() -> None:
    """
    Buld the UI and delete it if its there
    """
    global simple_button_ui

    try:
        simple_button_ui.close()
        simple_button_ui.deleteLater()
    except:
        pass

    simple_button_ui = SecondaryMotionUI()
    simple_button_ui.show()

class AboutDialog(QDialog):
    def __init__(self, version: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About Secondary Motion Tool")
        self.setFixedSize(420, 300)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("<b>Secondary Motion Tool</b>")
        version = QLabel(f"Version {version}")
        author = QLabel("Author: Mark Conrad")

        description = QLabel(
            "This is a tool to help create secondary motion on a joint chain using an additive animation layer. "
            "It simulates spring dynamics based on the rotation of the parent joint with a lag, allowing for more "
            "natural and dynamic motion. "
            "The resulting motion is applied as an additive delta on a separate animation layer, preserving the "
            "original animation. "
            "\n\n"
            "If it looks too stiff: Lower damping\n"
            "If it jitters: Increase damping\n"
            "If it feels weak: Increase spring_strength\n"
            "If it explodes: Lower clamp or increase damping"
        )
        description.setWordWrap(True)

        links = QLabel(
            """
            <a href="https://github.com/markC85">GitHub</a><br>
            <a href="https://mark_conrad.artstation.com">Animation Portfolio</a>
            <a href="http://www.linkedin.com/in/markaconrad">Linkedin Profile</a>
            """
        )
        links.setOpenExternalLinks(True)
        links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        links.setCursor(Qt.PointingHandCursor)

        email = QLabel("Email: markconrad.animator@gmail.com")
        email.setTextInteractionFlags(Qt.TextBrowserInteraction)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(author)
        layout.addWidget(description)
        layout.addSpacing(10)
        layout.addWidget(links)
        layout.addWidget(email)
        layout.addStretch()
        layout.addWidget(close_btn)

class SecondaryMotionUI(QtWidgets.QMainWindow):
    """
    Build the secondary motion UI
    """

    def __init__(self, parent=None) -> None:
        if parent is None:
            parent = get_maya_main_window()
        super().__init__(parent)

        self.version = "1.0.0"
        self.setWindowTitle(f"mc Secondary Motion Tool {self.version}")
        self.resize(550, 800)

        self._build_ui()
        self._create_menu()
        self._create_connections()

    def _create_menu(self) -> None:
        """
        Create the menu bar with File -> Exit
        """
        # Create the menu bar
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        help_menu = menu_bar.addMenu("Help")

        # about menu options
        self.about_project = QAction("About", self)
        self.about_project.setStatusTip("About this project")

        # exit action
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit the application")
        file_menu.addAction(self.exit_action)

        # Add the action to the About menu
        help_menu.addAction(self.about_project)

    def _build_ui(self) -> None:
        """
        UI fields and layout
        """
        # Main layout of the dialog
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        #main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # optional, removes extra spacing

        # Scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Container for scroll area
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # Form layout handles label + field pairs automatically
        form_layout = QFormLayout(content_widget)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        # Buttons
        self.run_simulation_btn = QPushButton("Run the Secondary Motion Simulation")
        self.run_simulation_btn.setStyleSheet("color: white; background-color: green; font-weight: bold;")

        self.delete_animation_layere_btn = QPushButton("Delete animation layer by name")
        self.delete_animation_layere_btn.setStyleSheet("color: white; background-color: blue; font-weight: bold;")

        # Fields
        description_label = QtWidgets.QLabel(
            "This tool applies a secondary motion simulation to a joint chain using an additive animation layer. "
            "\n\n"
            "Lag Frames: Higher values create more delay, making the motion feel looser. "
            "Lower values make it more responsive and stiff."
            "\n\n"
            "Spring Strength: Higher values create a stronger spring effect, making the motion more pronounced. "
            "Lower values create a softer, more subtle motion."
            "\n\n"
            "Damping: Higher values reduce oscillation faster, making the motion settle quicker. "
            "Lower values allow for more oscillation, creating a bouncier effect."
            "\n\n"
            "Max Rotation: Clamps the maximum rotation change per frame to prevent instability. "
            "Lower values can prevent explosive motion but may feel less dynamic. "
            "Higher values allow for more extreme motion but can lead to instability if set too high."
        )
        description_label.setWordWrap(True)  # allows the text to wrap to multiple lines
        description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.lag_frames = QLineEdit()
        self.lag_frames.setValidator(QIntValidator())
        self.lag_frames.setText("2")

        self.spring_strength = QLineEdit()
        self.spring_strength.setValidator(QDoubleValidator())
        self.spring_strength.setText("0.25")

        self.damping = QLineEdit()
        self.damping.setValidator(QDoubleValidator())
        self.damping.setText("0.90")

        self.max_rotation = QLineEdit()
        self.max_rotation.setValidator(QIntValidator())
        self.max_rotation.setText("20")

        self.layer_name = QLineEdit()
        self.layer_name.setText("secondaryMotion_Add")

        # Add Fields
        form_layout.addRow(description_label)
        form_layout.addRow("Lag Frames:", self.lag_frames)
        form_layout.addRow("Spring Strength:", self.spring_strength)
        form_layout.addRow("Dampaning:", self.damping)
        form_layout.addRow("Max Rotation:", self.max_rotation)
        form_layout.addRow("Animation Layer Name:", self.layer_name)

        # Set the content widget as the scroll area's widget
        main_layout.addWidget(scroll_area)

        main_layout.addWidget(self.run_simulation_btn)
        main_layout.addWidget(self.delete_animation_layere_btn)

    def _create_connections(self) -> None:
        """
        Connect UI button logic
        """
        self.run_simulation_btn.clicked.connect(
            lambda: apply_secondary_motion_additive(
                joints=cmds.ls(selection=True),
                lag_frames=int(self.lag_frames.text()),
                spring_strength=float(self.spring_strength.text()),
                damping=float(self.damping.text()),
                max_rotation_clamp=int(self.max_rotation.text()),
                layer_name=str(self.layer_name.text()),
            )
        )
        self.delete_animation_layere_btn.clicked.connect(
            lambda: delete_anim_layer_by_name(
                target_name=self.layer_name.text(),
            )
        )
        self.exit_action.triggered.connect(self.close)
        self.about_project.triggered.connect(self._show_about_dialog)

    def _show_about_dialog(self):
        dlg = AboutDialog(self.version, self)
        dlg.exec()