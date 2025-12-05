import sys
import math
import os
import threading
import asyncio
import cv2
import time
import mediapipe as mp
from dotenv import load_dotenv

# PySide6 Imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, QSizePolicy, QStackedLayout, QComboBox)
from PySide6.QtCore import (Qt, QPoint, Signal, QThread, Slot, QRect, QSize)
from PySide6.QtGui import (QPainter, QColor, QPen, QImage, QPixmap)

# Import your existing modules
from visualizer import VisualizerWidget
import ada

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
THEME = {
    'bg': '#0a0a0a',
    'panel_bg': '#171717',
    'cyan': '#06b6d4',      # Cyan-500
    'cyan_dim': '#155e75',  # Cyan-900
    'cyan_glow': '#22d3ee', # Cyan-400
    'text': '#cffafe',      # Cyan-100
    'green': '#22c55e'
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {THEME['bg']};
}}
QWidget {{
    font-family: 'Segoe UI', 'Roboto', 'Helvetica', sans-serif;
    color: {THEME['text']};
}}
QLabel {{
    color: {THEME['text']};
    font-size: 16px;
}}
/* Large, Touch-friendly Buttons */
QPushButton {{
    background-color: {THEME['cyan_dim']};
    color: {THEME['text']};
    border: 2px solid {THEME['cyan_dim']};
    border-radius: 12px;
    padding: 15px;
    font-size: 18px;
    font-weight: bold;
    min-height: 50px;
}}
QPushButton:hover {{
    background-color: {THEME['cyan']};
    color: #000;
    border-color: {THEME['cyan_glow']};
}}
QPushButton:pressed {{
    background-color: {THEME['cyan_glow']};
}}
/* Focused state for Hand Tracking Snap */
QPushButton[snapped="true"] {{
    background-color: {THEME['cyan']};
    color: #000;
    border-color: #fff;
    border-width: 3px;
}}
QLineEdit {{
    background-color: {THEME['panel_bg']};
    border: 2px solid {THEME['cyan_dim']};
    border-radius: 12px;
    padding: 15px;
    font-size: 18px;
    color: {THEME['text']};
}}
QComboBox {{
    background-color: {THEME['panel_bg']};
    border: 2px solid {THEME['cyan_dim']};
    border-radius: 12px;
    padding: 5px 15px;
    font-size: 16px;
    color: {THEME['text']};
}}
QComboBox::drop-down {{
    border: none;
}}
"""

class GuiAudioLoop(ada.AudioLoop):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = asyncio.Event()
        self.text_queue = asyncio.Queue()

    async def send_text(self):
        while True:
            text = await self.text_queue.get()
            if text is None:
                break
            await self.session.send(input=text, end_of_turn=True)
        
    def stop(self):
        self.stop_event.set()
        self.text_queue.put_nowait(None)

class VideoThread(QThread):
    # Emits (x, y, is_pinching)
    hand_signal = Signal(float, float, bool)
    # Emits the actual video frame for display
    frame_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        # Fix for OpenCV on macOS
        os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"
        cap = cv2.VideoCapture(0)
        
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        
        with mp_hands.Hands(
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            max_num_hands=1) as hands:
            
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                # 1. Mirror the image (Flip Horizontal)
                # This ensures moving your hand RIGHT moves the cursor RIGHT on screen
                # frame = cv2.flip(frame, 1)
                
                # Convert to RGB for MediaPipe and Display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process Hands
                frame_rgb.flags.writeable = False
                results = hands.process(frame_rgb)
                frame_rgb.flags.writeable = True # Make writable for drawing
                
                is_pinching = False
                x, y = 0.5, 0.5 # Default center
                hand_detected = False

                if results.multi_hand_landmarks:
                    hand_detected = True
                    for hand_landmarks in results.multi_hand_landmarks:
                        # 2. Draw Landmarks on the feed
                        mp_drawing.draw_landmarks(
                            frame_rgb,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style())
                            
                        # Use Index Finger Tip (8)
                        index_tip = hand_landmarks.landmark[8]
                        thumb_tip = hand_landmarks.landmark[4]
                        
                        x = index_tip.x
                        y = index_tip.y
                        
                        # Calculate Pinch Distance
                        dist = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
                        if dist < 0.08: 
                            is_pinching = True

                # Emit frame for display (With drawings)
                self.frame_signal.emit(frame_rgb)

                if hand_detected:
                    self.hand_signal.emit(x, y, is_pinching)
                
                time.sleep(0.016) # ~60 FPS cap

        cap.release()

    def stop(self):
        self._running = False
        self.wait()

class MagneticCursorOverlay(QWidget):
    """
    Transparent overlay that draws the hand cursor and visualizes snapping.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.cursor_pos = QPoint(0, 0)
        self.is_pinching = False
        self.snapped_target_rect = None

    def update_state(self, pos, is_pinching, snapped_rect=None):
        self.cursor_pos = pos
        self.is_pinching = is_pinching
        self.snapped_target_rect = snapped_rect
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Draw Snap Highlight
        if self.snapped_target_rect:
            r = self.snapped_target_rect
            # Slightly larger highlight
            r.adjust(-8, -8, 8, 8)
            painter.setPen(QPen(QColor(THEME['cyan']), 3))
            painter.setBrush(QColor(6, 182, 212, 50)) 
            painter.drawRoundedRect(r, 15, 15)

        # 2. Draw Hand Cursor
        color = QColor(THEME['green']) if self.is_pinching else QColor(THEME['cyan'])
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(color)
        
        radius = 15 if self.is_pinching else 20
        painter.drawEllipse(self.cursor_pos, radius, radius)
        
        painter.setBrush(Qt.white)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.cursor_pos, 4, 4)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("O.L.L.I.E - Visualizer")
        self.resize(1920, 1080)
        self.setStyleSheet(STYLESHEET)
        
        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel("O.L.L.I.E.")
        title.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {THEME['cyan']}; letter-spacing: 5px;")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_settings = QPushButton("⚙️ SETTINGS")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setFixedWidth(160)
        self.btn_settings.clicked.connect(self.toggle_settings)
        header.addWidget(self.btn_settings)

        self.btn_cam = QPushButton("📷 CAM")
        self.btn_cam.setCheckable(True)
        self.btn_cam.setFixedWidth(120)
        self.btn_cam.clicked.connect(self.toggle_camera)
        header.addWidget(self.btn_cam)
        layout.addLayout(header)

        # 1.5 Settings Area (Hidden by default)
        self.settings_container = QWidget()
        self.settings_container.setStyleSheet(f"background-color: {THEME['panel_bg']}; border-radius: 12px; padding: 10px;")
        self.settings_container.hide()
        settings_layout = QHBoxLayout(self.settings_container)
        
        settings_layout.addWidget(QLabel("Microphone:"))
        self.combo_mic = QComboBox()
        self.combo_mic.currentIndexChanged.connect(self.change_audio_device)
        settings_layout.addWidget(self.combo_mic)
        
        settings_layout.addWidget(QLabel("Speaker:"))
        self.combo_speaker = QComboBox()
        self.combo_speaker.currentIndexChanged.connect(self.change_audio_device)
        settings_layout.addWidget(self.combo_speaker)
        
        layout.addWidget(self.settings_container)

        # 2. Main Display Area
        self.vis_container = QWidget()
        self.vis_container.setStyleSheet(f"background-color: {THEME['panel_bg']}; border-radius: 12px;")
        self.vis_layout = QHBoxLayout(self.vis_container)
        
        # Visualizer
        self.visualizer = VisualizerWidget()
        self.visualizer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.vis_layout.addWidget(self.visualizer)
        
        # Camera Label (Hidden by default)
        self.video_label = QLabel()
        self.video_label.setFixedSize(320, 240)
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #333; border-radius: 8px;")
        self.video_label.hide()
        self.vis_layout.addWidget(self.video_label)
        
        layout.addWidget(self.vis_container)

        # 3. Footer (Input)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Message...")
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field)

        # --- Overlay for Hand Cursor ---
        self.cursor_overlay = MagneticCursorOverlay(self)
        self.cursor_overlay.resize(self.size())
        self.cursor_overlay.show()
        self.cursor_overlay.raise_()

        # --- Logic Init ---
        self.video_thread = VideoThread()
        self.video_thread.hand_signal.connect(self.process_hand_input)
        self.video_thread.frame_signal.connect(self.update_video_frame)
        self.video_thread.start()
        
        self.start_backend()

        self.snapped_widget = None
        self.was_pinching = False

    def resizeEvent(self, event):
        self.cursor_overlay.resize(self.size())
        super().resizeEvent(event)

    def start_backend(self):
        if hasattr(self, 'audio_loop'):
            self.audio_loop.stop()
            
        input_idx = self.combo_mic.currentData()
        output_idx = self.combo_speaker.currentData()
        
        self.backend_thread = threading.Thread(target=self.run_async_loop, args=(input_idx, output_idx), daemon=True)
        self.backend_thread.start()

    def run_async_loop(self, input_idx, output_idx):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop
            
            self.audio_loop = GuiAudioLoop(
                video_mode="none",
                on_audio_data=self.on_audio_data_callback,
                input_device_index=input_idx,
                output_device_index=output_idx
            )
            loop.run_until_complete(self.audio_loop.run())
        except Exception as e:
            print(f"Backend error: {e}")

    @Slot(bytes)
    def on_audio_data_callback(self, data):
        self.visualizer.update_audio_data(data)

    @Slot(object)
    def update_video_frame(self, frame_rgb):
        # Only process if visible to save resources
        if self.video_label.isVisible():
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            # Scale to label size
            pixmap = QPixmap.fromImage(q_img).scaled(
                self.video_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(pixmap)

    def toggle_settings(self):
        if self.btn_settings.isChecked():
            self.settings_container.show()
            self.populate_audio_devices()
        else:
            self.settings_container.hide()

    def populate_audio_devices(self):
        self.combo_mic.blockSignals(True)
        self.combo_speaker.blockSignals(True)
        
        self.combo_mic.clear()
        self.combo_speaker.clear()
        
        try:
            inputs = ada.get_input_devices()
            for idx, name in inputs:
                self.combo_mic.addItem(name, idx)
                
            outputs = ada.get_output_devices()
            for idx, name in outputs:
                self.combo_speaker.addItem(name, idx)
        except Exception as e:
            print(f"Error listing devices: {e}")
            
        self.combo_mic.blockSignals(False)
        self.combo_speaker.blockSignals(False)

    def change_audio_device(self):
        # Restart backend with new devices
        self.start_backend()

    def toggle_camera(self):
        if self.btn_cam.isChecked():
            self.video_label.show()
        else:
            self.video_label.hide()

    def send_message(self):
        text = self.input_field.text()
        if text:
            self.input_field.clear()
            if hasattr(self, 'loop') and hasattr(self, 'audio_loop'):
                self.loop.call_soon_threadsafe(self.audio_loop.text_queue.put_nowait, text)

    @Slot(float, float, bool)
    def process_hand_input(self, norm_x, norm_y, is_pinching):
        # 1. Map Coordinates
        win_w = self.width()
        win_h = self.height()
        
        margin = 0.1
        raw_x = (norm_x - margin) / (1 - 2*margin)
        raw_y = (norm_y - margin) / (1 - 2*margin)
        
        cursor_x = int(max(0, min(1, raw_x)) * win_w)
        cursor_y = int(max(0, min(1, raw_y)) * win_h)
        cursor_pt = QPoint(cursor_x, cursor_y)

        # 2. Identify Buttons
        targets = []
        buttons = self.findChildren(QPushButton)
        for btn in buttons:
            if btn.isVisible() and btn.isEnabled():
                geo = btn.mapTo(self, QPoint(0,0))
                rect = QRect(geo, btn.size())
                targets.append((btn, rect))

        # --- STICKY SNAP LOGIC (Hysteresis) ---
        SNAP_ENTER_RADIUS = 80   # Distance to START snapping
        SNAP_EXIT_RADIUS = 160   # Distance to STOP snapping (Stickiness)
        
        closest_dist = float('inf')
        closest_target = None
        closest_rect = None

        # Find closest target
        for target, rect in targets:
            center = rect.center()
            dist = math.hypot(center.x() - cursor_x, center.y() - cursor_y)
            if dist < closest_dist:
                closest_dist = dist
                closest_target = target
                closest_rect = rect

        final_pos = cursor_pt
        new_snapped_widget = None
        new_snapped_rect = None

        # Logic: 
        # If we are ALREADY snapped to a widget, use the larger EXIT radius
        # If we are NOT snapped, use the smaller ENTER radius
        
        # Check if we are still close to the previously snapped widget
        if self.snapped_widget and self.snapped_widget.isVisible():
             # Find rect of currently snapped widget
             current_rect = None
             for t, r in targets:
                 if t == self.snapped_widget:
                     current_rect = r
                     break
             
             if current_rect:
                 center = current_rect.center()
                 dist_to_current = math.hypot(center.x() - cursor_x, center.y() - cursor_y)
                 
                 # If we are within EXIT radius of the CURRENT widget, hold it!
                 if dist_to_current < SNAP_EXIT_RADIUS:
                     new_snapped_widget = self.snapped_widget
                     new_snapped_rect = current_rect
                     final_pos = current_rect.center()

        # If we didn't hold the old snap, try to find a new one
        if not new_snapped_widget:
            if closest_dist < SNAP_ENTER_RADIUS and closest_target:
                new_snapped_widget = closest_target
                new_snapped_rect = closest_rect
                final_pos = closest_rect.center()

        # Update Visuals (Unpolish/Polish for style refresh)
        if self.snapped_widget != new_snapped_widget:
            # Unsnap old
            if self.snapped_widget:
                self.snapped_widget.setProperty("snapped", False)
                self.snapped_widget.style().unpolish(self.snapped_widget)
                self.snapped_widget.style().polish(self.snapped_widget)
            
            # Snap new
            if new_snapped_widget:
                new_snapped_widget.setProperty("snapped", True)
                new_snapped_widget.style().unpolish(new_snapped_widget)
                new_snapped_widget.style().polish(new_snapped_widget)
            
            self.snapped_widget = new_snapped_widget

        # 5. Handle Click
        if is_pinching and not self.was_pinching:
            if self.snapped_widget:
                print(f"Clicking widget: {self.snapped_widget}")
                self.snapped_widget.animateClick()
        
        self.was_pinching = is_pinching
        self.cursor_overlay.update_state(final_pos, is_pinching, new_snapped_rect)

    def closeEvent(self, event):
        self.video_thread.stop()
        if hasattr(self, 'audio_loop'):
            self.audio_loop.stop()
        os._exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
