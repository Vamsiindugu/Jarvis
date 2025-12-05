import sys
import math
import random
import os
# Fix for OpenCV on macOS: disable authorization request from background threads
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

import threading
import asyncio
import cv2
import time
from datetime import datetime
from dotenv import load_dotenv
import mediapipe as mp
import pyautogui
import math

# Optimize pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# PySide6 Imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QScrollArea, QPushButton,
                             QGraphicsDropShadowEffect, QSizePolicy, QProgressBar)
from PySide6.QtCore import (Qt, QTimer, QPointF, Signal, QSize, QPropertyAnimation, 
                            QEasingCurve, QThread, Slot, QObject, QEvent, QPoint)
from PySide6.QtGui import (QPainter, QColor, QPen, QRadialGradient, QBrush, 
                         QFont, QLinearGradient, QPainterPath, QGradient, QImage, QPixmap, QPolygonF)

from visualizer import VisualizerWidget
import ada

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
THEME = {
    'bg': '#000000',
    'cyan': '#06b6d4',      # Cyan-500
    'cyan_dim': '#155e75',  # Cyan-900
    'cyan_glow': '#22d3ee', # Cyan-400
    'text': '#cffafe',      # Cyan-100
    'red': '#ef4444',
    'green': '#22c55e'
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {THEME['bg']};
}}
QLabel {{
    color: {THEME['text']};
    font-family: 'Menlo', 'Courier New', 'Monospace';
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: {THEME['bg']};
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {THEME['cyan_dim']};
    border-radius: 4px;
}}
/* Progress Bar Styling */
QProgressBar {{
    border: 1px solid {THEME['cyan_dim']};
    background-color: #050505;
    text-align: center;
    color: {THEME['text']};
    font-family: 'Menlo';
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {THEME['cyan']};
    width: 10px; 
    margin: 1px;
}}
"""

# Signal helper for async updates
class Signaller(QObject):
    frame_signal = Signal(object)
    audio_signal = Signal(bytes)

class GuiAudioLoop(ada.AudioLoop):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = asyncio.Event()

    async def send_text(self):
        # Override to avoid blocking input()
        await self.stop_event.wait()
        # When stopped, we can just return or send a quit signal if needed
        # But since we are cancelling tasks in run(), this might be enough.
        
    def stop(self):
        self.stop_event.set()

class RippleWidget(QWidget):
    def __init__(self, parent=None, center=QPoint()):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.radius = 0
        self.max_radius = 30
        self.opacity = 0.8
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16) # ~60 fps
        
        # Size enough to hold the max radius circle
        size = self.max_radius * 2 + 10
        self.resize(size, size)
        # Center the widget on the click point relative to parent
        self.move(center.x() - size // 2, center.y() - size // 2)
        self.show()

    def animate(self):
        self.radius += 2
        self.opacity -= 0.05
        if self.opacity <= 0:
            self.timer.stop()
            self.deleteLater()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        color = QColor(THEME['cyan'])
        color.setAlphaF(max(0, self.opacity))
        painter.setBrush(color)
        
        # Draw circle at center of widget
        center = self.rect().center()
        painter.drawEllipse(center, self.radius, self.radius)

class VideoThread(QThread):
    frame_signal = Signal(object)
    fps_signal = Signal(float)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open video device.")
            return

        # MediaPipe Hands setup
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        
        # Screen size for mouse control
        screen_width, screen_height = pyautogui.size()
        is_clicking = False
        
        with mp_hands.Hands(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as hands:
            
            last_time = time.time()
            while self._running:
                ret, frame = cap.read()
                if ret:

                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Process hand tracking
                    frame_rgb.flags.writeable = False
                    results = hands.process(frame_rgb)
                    frame_rgb.flags.writeable = True

                    # Draw landmarks
                    if results.multi_hand_landmarks:
                        for hand_landmarks in results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(
                                frame_rgb,
                                hand_landmarks,
                                mp_hands.HAND_CONNECTIONS
                            )
                            
                            # --- Gesture Control ---
                            # Index Finger Tip (8)
                            index_tip = hand_landmarks.landmark[8]
                            # Thumb Tip (4)
                            thumb_tip = hand_landmarks.landmark[4]
                            
                            # Move Mouse (Index Finger)
                            # Map 0-1 to screen coordinates
                            # Use a margin to reach edges easier? For now direct mapping.
                            target_x = int(index_tip.x * screen_width)
                            target_y = int(index_tip.y * screen_height)
                            
                            # Smooth movement could be added here, but direct for responsiveness first
                            pyautogui.moveTo(target_x, target_y)
                            
                            # Click Gesture (Pinch)
                            # Calculate distance between index tip and thumb tip
                            # Coordinates are normalized 0-1, so distance is relative
                            # We can use Euclidean distance
                            distance = math.sqrt(
                                (index_tip.x - thumb_tip.x)**2 + 
                                (index_tip.y - thumb_tip.y)**2
                            )
                            
                            # Threshold for click (experimentally determined, e.g. 0.05)
                            if distance < 0.05:
                                if not is_clicking:
                                    pyautogui.click()
                                    is_clicking = True
                            else:
                                is_clicking = False

                    self.frame_signal.emit(frame_rgb)
                
                current_time = time.time()
                dt = current_time - last_time
                if dt > 0:
                    fps = 1.0 / dt
                    self.fps_signal.emit(fps)
                last_time = current_time

                # ~60 FPS target (16ms), but we need to account for processing time
                # Simple sleep is okay for now as long as we measure actual time for FPS
                time.sleep(0.016)

        cap.release()

    def stop(self):
        self._running = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("O.L.L.I.E Interface")
        self.resize(800, 600)
        self.setStyleSheet(STYLESHEET)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_header()
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        self.main_layout.addLayout(content_layout)

        # --- VISUALIZER AREA ---
        self.visualizer = VisualizerWidget()
        content_layout.addWidget(self.visualizer)

        footer_line = QFrame()
        footer_line.setFixedHeight(2)
        footer_line.setStyleSheet(f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:0.5 {THEME['cyan_dim']}, stop:1 black);")
        self.main_layout.addWidget(footer_line)

        # --- VIDEO OVERLAY ---
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(320, 240)
        self.video_label.setStyleSheet(f"background-color: black; border: 1px solid {THEME['cyan_dim']};")
        self.video_label.hide() # Hide initially until first frame


        # Signals
        self.signaller = Signaller()
        # self.signaller.frame_signal.connect(self.update_frame) # No longer needed from backend
        self.signaller.audio_signal.connect(self.update_audio)
        
        # Start Video Thread
        self.video_thread = VideoThread()
        self.video_thread.frame_signal.connect(self.update_frame)
        self.video_thread.fps_signal.connect(self.update_fps)
        self.video_thread.start()

        # Start Backend
        self.start_backend()

        # Install event filter to capture clicks globally in the app
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            # Map global position to MainWindow coordinates
            if isinstance(event, QEvent): # Just to be safe with types
                # For mouse events, we can get global pos
                # But event might be generic QEvent if we don't cast, but Python is dynamic.
                # QMouseEvent has globalPos() or globalPosition() in newer Qt
                try:
                    # PySide6 uses globalPosition() which returns QPointF, or globalPos() for QPoint
                    pos = event.globalPos()
                    local_pos = self.mapFromGlobal(pos)
                    
                    # Create ripple
                    RippleWidget(self, local_pos)
                except:
                    pass
        return super().eventFilter(obj, event)

    def setup_header(self):
        header = QFrame()
        header.setStyleSheet(f"background-color: rgba(0, 0, 0, 100); border-bottom: 1px solid {THEME['cyan_dim']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel("O.L.L.I.E.")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {THEME['text']}; letter-spacing: 4px;")
        
        self.status_label = QLabel(" ONLINE // V.4.0.3")
        self.status_label.setStyleSheet(f"color: {THEME['green']}; font-size: 10px; letter-spacing: 2px;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet(f"color: {THEME['cyan_dim']}; font-weight: bold; margin-left: 15px;")
        header_layout.addWidget(self.fps_label)

        # Camera Toggle Button
        self.cam_button = QPushButton("CAM")
        self.cam_button.setCheckable(True)
        self.cam_button.setChecked(True)
        self.cam_button.setFixedSize(50, 25)
        self.cam_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['cyan_dim']};
                color: {THEME['text']};
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-left: 15px;
            }}
            QPushButton:checked {{
                background-color: {THEME['cyan']};
                color: black;
            }}
            QPushButton:hover {{
                background-color: {THEME['cyan_glow']};
            }}
        """)
        self.cam_button.clicked.connect(self.toggle_camera)
        header_layout.addWidget(self.cam_button)

        self.main_layout.addWidget(header)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position video at bottom right with some padding
        padding = 20
        x = self.width() - self.video_label.width() - padding
        y = self.height() - self.video_label.height() - padding
        self.video_label.move(x, y)
        self.video_label.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        # Stop video thread
        if hasattr(self, 'video_thread'):
            self.video_thread.stop()

        if hasattr(self, 'audio_loop') and self.audio_loop:
            # Signal the loop to stop
            if hasattr(self.audio_loop, 'stop'):
                 # We need to do this in a thread-safe way if possible, 
                 # but since stop_event is asyncio, we might need to use call_soon_threadsafe
                 # However, setting the event from this thread might not work directly if the loop is in another thread.
                 # Actually, asyncio.Event is not thread-safe.
                 # Better approach: The backend is in a separate thread.
                 # We can just let the thread die or try to cancel it.
                 # But to be clean, let's try to set the event.
                 # Since we are in a different thread, we should use the loop's call_soon_threadsafe.
                 # We need access to the loop.
                 pass
        
        # Force exit to ensure all threads are killed
        # This is a bit aggressive but ensures "shutdowns the whole program"
        os._exit(0)


    # --- Backend Integration ---
    def start_backend(self):
        self.backend_thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.backend_thread.start()

    def run_async_loop(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.audio_loop = GuiAudioLoop(
                video_mode="none",
                on_audio_data=self.on_audio_data_callback,
                on_video_frame=None # We handle video separately
            )
            
            loop.run_until_complete(self.audio_loop.run())
        except Exception as e:
            print(f"Backend error: {e}")

    def on_audio_data_callback(self, data):
        self.signaller.audio_signal.emit(data)

    def on_video_frame_callback(self, frame_rgb):
        pass
        # self.signaller.frame_signal.emit(frame_rgb)

    @Slot(object)
    def update_frame(self, frame_rgb):
        if frame_rgb is not None:
            height, width, channel = frame_rgb.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            # Scale to fit label keeping aspect ratio
            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            self.video_label.setPixmap(scaled_pixmap)
            if self.video_label.isHidden():
                self.video_label.show()
                # Re-trigger resize to ensure correct position if needed
                self.resizeEvent(None)

    @Slot(float)
    def update_fps(self, fps):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    @Slot()
    def toggle_camera(self):
        if self.cam_button.isChecked():
            self.video_label.show()
            # Re-trigger resize to ensure correct position
            self.resizeEvent(None)
        else:
            self.video_label.hide()

    @Slot(bytes)
    def update_audio(self, data):
        self.visualizer.update_audio_data(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
