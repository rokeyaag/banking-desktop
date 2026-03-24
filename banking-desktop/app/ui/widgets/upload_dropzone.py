from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Signal, Qt

class UploadDropzone(QLabel):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__("📄 Drop .txt file here\nor click to upload", parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(80)
        self.setStyleSheet("QLabel { background: #1e293b; border: 2px dashed #334155; border-radius: 10px; color: #64748b; font-size: 12px; padding: 10px; }")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
        else: e.ignore()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".txt"):
                self.file_dropped.emit(path)
                break
