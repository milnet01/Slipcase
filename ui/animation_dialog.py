"""Animation export settings dialog."""

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QLabel, QSpinBox, QVBoxLayout,
)


class AnimationDialog(QDialog):
    """Dialog for configuring animation export parameters."""

    def __init__(self, current_width: int = 512, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Animation")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Angle range
        angle_group = QGroupBox("Angle Range")
        angle_layout = QFormLayout()

        self.start_angle = QSpinBox()
        self.start_angle.setRange(5, 60)
        self.start_angle.setValue(10)
        self.start_angle.setSuffix("\u00b0")
        angle_layout.addRow("Start angle:", self.start_angle)

        self.end_angle = QSpinBox()
        self.end_angle.setRange(5, 60)
        self.end_angle.setValue(50)
        self.end_angle.setSuffix("\u00b0")
        angle_layout.addRow("End angle:", self.end_angle)

        self.bounce_check = QCheckBox("Bounce (ping-pong)")
        self.bounce_check.setChecked(True)
        self.bounce_check.setToolTip("Animate forward then reverse for a smooth loop")
        angle_layout.addRow(self.bounce_check)

        angle_group.setLayout(angle_layout)
        layout.addWidget(angle_group)

        # Frames
        frames_group = QGroupBox("Frames")
        frames_layout = QFormLayout()

        self.frame_count = QSpinBox()
        self.frame_count.setRange(5, 120)
        self.frame_count.setValue(24)
        frames_layout.addRow("Frame count:", self.frame_count)

        self.frame_delay = QSpinBox()
        self.frame_delay.setRange(10, 500)
        self.frame_delay.setValue(50)
        self.frame_delay.setSuffix(" ms")
        self.frame_delay.setToolTip("Delay between frames (50ms = ~20fps)")
        frames_layout.addRow("Frame delay:", self.frame_delay)

        frames_group.setLayout(frames_layout)
        layout.addWidget(frames_group)

        # Output
        output_group = QGroupBox("Output")
        output_layout = QFormLayout()

        self.output_width = QSpinBox()
        self.output_width.setRange(64, 2048)
        self.output_width.setValue(min(current_width, 512))
        self.output_width.setSuffix(" px")
        output_layout.addRow("Width:", self.output_width)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["APNG", "GIF"])
        output_layout.addRow("Format:", self.format_combo)

        self.info_label = QLabel(
            "<small>APNG supports transparency. "
            "GIF uses a solid background.</small>"
        )
        self.info_label.setWordWrap(True)
        output_layout.addRow(self.info_label)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_params(self) -> dict:
        """Return animation parameters as a dict."""
        return {
            "start_angle": self.start_angle.value(),
            "end_angle": self.end_angle.value(),
            "frame_count": self.frame_count.value(),
            "frame_delay": self.frame_delay.value(),
            "bounce": self.bounce_check.isChecked(),
            "fmt": self.format_combo.currentText(),
            "output_width": self.output_width.value(),
        }
