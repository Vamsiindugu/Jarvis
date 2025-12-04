import sys
import asyncio
import threading
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QObject, Slot, QByteArray
from PySide6.QtGui import QFont, QColor, QPalette, QImage, QPixmap, QPainter

from visualizer import AudioVisualizer
import ada

# Signal helper for async updates
class Signaller(QObject):
    frame_signal = Signal(object)
    audio_signal = Signal(bytes)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS AI Assistant")
        self.resize(1000, 800)
        
        # Sci-Fi Theme
        self.apply_theme()
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("SYSTEM ONLINE")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Orbitron", 24, QFont.Weight.Bold)) # Futuristic font if available
        header.setStyleSheet("color: #00ffff; letter-spacing: 5px;")
        layout.addWidget(header)
        
        # Video Feed
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid #00ffff; background-color: #001111;")
        layout.addWidget(self.video_label)
        
        # Audio Visualizer
        self.visualizer = AudioVisualizer()
        layout.addWidget(self.visualizer)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.quit_btn = QPushButton("TERMINATE")
        self.quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff0000;
                border: 1px solid #ff0000;
                padding: 10px;
                font-family: 'Orbitron';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #550000;
            }
        """)
        self.quit_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.quit_btn)
        layout.addLayout(controls_layout)
        
        # Signals
        self.signaller = Signaller()
        self.signaller.frame_signal.connect(self.update_frame)
        self.signaller.audio_signal.connect(self.update_audio)
        
        # Start Backend
        self.start_backend()

    def apply_theme(self):
        # Dark Palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(10, 10, 20))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 255))
        self.setPalette(palette)
        
        # Font (fallback to generic sans-serif)
        font = QFont("Segoe UI", 10)
        self.setFont(font)

    def start_backend(self):
        # Run asyncio loop in a separate thread
        self.backend_thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.backend_thread.start()

    def run_async_loop(self):
        # Initialize and run the ada.py AudioLoop
        # We need to modify ada.py to accept callbacks
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.audio_loop = ada.AudioLoop(
                video_mode="camera",
                on_audio_data=self.on_audio_data_callback,
                on_video_frame=self.on_video_frame_callback
            )
            
            loop.run_until_complete(self.audio_loop.run())
        except Exception as e:
            print(f"Backend error: {e}")

    def on_audio_data_callback(self, data):
        self.signaller.audio_signal.emit(data)

    def on_video_frame_callback(self, frame_rgb):
        self.signaller.frame_signal.emit(frame_rgb)

    @Slot(object)
    def update_frame(self, frame_rgb):
        # Convert numpy/opencv image to QPixmap
        # frame_rgb is already RGB from ada.py
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))

    @Slot(bytes)
    def update_audio(self, data):
        self.visualizer.update_audio_data(data)

    def closeEvent(self, event):
        # Cleanup
        # Ideally we should signal the async loop to stop
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
