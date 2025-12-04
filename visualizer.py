import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

class AudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.audio_data = np.zeros(1024)
        self.decay = np.zeros(1024)
        
        # Sci-Fi Colors
        self.bar_color = QColor(0, 255, 255, 200)  # Cyan
        self.peak_color = QColor(255, 0, 255, 255) # Magenta
        
        # Timer for smooth animation decay
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_decay)
        self.timer.start(16)  # ~60 FPS

    def update_audio_data(self, data):
        """
        Update the visualizer with new audio data.
        data: bytes object containing PCM audio data (int16)
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(data, dtype=np.int16)
            
            # Normalize and take absolute value
            if len(audio_array) > 0:
                # Resample or slice to fit visualizer width if needed
                # For simplicity, we'll just take a slice or average
                # Here we just take the first N samples that fit
                self.audio_data = np.abs(audio_array) / 32768.0
                
                # Pad if data is shorter than expected (though we usually get fixed chunks)
                if len(self.audio_data) < 1024:
                    self.audio_data = np.pad(self.audio_data, (0, 1024 - len(self.audio_data)))
                else:
                    self.audio_data = self.audio_data[:1024]
                    
                self.update()
        except Exception as e:
            print(f"Error updating visualizer: {e}")

    def update_decay(self):
        # Simple decay effect
        self.decay = self.decay * 0.9
        self.audio_data = np.maximum(self.audio_data, self.decay)
        self.decay = self.audio_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background (transparent or dark)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        
        width = self.width()
        height = self.height()
        
        # Draw waveform or bars
        # Let's draw a mirrored center waveform for that "Jarvis" look
        
        center_y = height / 2
        
        # Downsample for drawing
        num_bars = 64
        chunk_size = len(self.audio_data) // num_bars
        
        bar_width = width / num_bars
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.bar_color))
        
        for i in range(num_bars):
            start = i * chunk_size
            end = (i + 1) * chunk_size
            val = np.mean(self.audio_data[start:end])
            
            bar_height = val * height
            
            # Draw mirrored bars from center
            x = i * bar_width
            
            # Top bar
            painter.drawRect(int(x), int(center_y - bar_height/2), int(bar_width - 1), int(bar_height))
            
            # Optional: Draw peak dots or lines
