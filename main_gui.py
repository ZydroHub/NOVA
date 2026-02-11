import sys
import cv2
import threading
import time
import psutil
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.screen import MDScreen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Line, InstructionGroup, Rectangle
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel

import computer_vision
from speech_to_text import STTEngine
from chatbot import ChatBot

# Force a portrait resolution
Window.size = (480, 800)

class DetectionOverlay(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.box_color = (0, 1, 0, 1) # Green
        self.text_color = (0, 1, 0, 1)

    def update(self, metadata):
        self.canvas.after.clear()
        
        if not metadata:
            return

        with self.canvas.after:
            # 1. Detections
            if "detections" in metadata:
                Color(*self.box_color)
                for det in metadata["detections"]:
                    # det["bbox"] is [xmin, ymin, xmax, ymax] (normalized 0-1)
                    # We need to scale to widget size
                    bbox = det["bbox"]
                    
                    # Flip Y because Kivy (0,0) is bottom-left, but Hailo/OpenCV (0,0) is top-left usually?
                    # GStreamer videoconvert might flipped it? 
                    # Usually, standard image coords: (0,0) top-left.
                    # Kivy coords: (0,0) bottom-left.
                    # We rotated the image 90 degrees in `setup_rotation`! 
                    # IMPORTANT: The metadata coordinates are relative to the *buffer* (which is landscape 640x480).
                    # But the *display* is rotated 90 degrees to 480x800.
                    # This is tricky. 
                    
                    # Let's assume for a moment the Image widget handles the rotation context visually,
                    # but our overlay is just a widget on top.
                    # Validating the rotation:
                    # `self.rot = Rotate(angle=90, origin=img.center)`
                    # This rotates the *texture* inside the Image widget.
                    # If we draw on top, we either:
                    # A) Draw in normal coords and apply same rotation to our canvas?
                    # B) Transform coords manually.
                    
                    # Approach A is easiest. Apply rotation to this widget context too?
                    # Or simpler: The Image widget is sized 800x480 (landscape logic) but rotated 90 deg visually?
                    # No, `Image` size is set to (800, 480) in `setup_rotation`.
                    
                    # Let's try to map to the `cam_display` widget's apparent coordinates.
                    # Since `cam_display` is rotated, we should probably apply the same rotation to the overlay logic.
                    # OR, we can just attach this Overlay Widget AS A CHILD of the same rotated context?
                    # No, `Image` doesn't easily accept children like that in KV.
                    
                    # Let's manually map.
                    # Image (Landscape Buffer) -> Display (Portrait).
                    # (x, y) in Buffer -> (y, 1-x) in Portrait? 
                    # Rotation 90 deg counter-clockwise: (x, y) -> (y, -x) (relative to center)
                    
                    # Simpler path: Apply same rotation to this widget's canvas.
                    pass 

    def update_draw(self, metadata, source_size):
        """
        metadata: dict with 'detections' or 'pose'
        source_size: (w, h) of the camera buffer (e.g. 640x480)
        """
        self.canvas.after.clear()
        if not metadata: return
        
        # We assume this widget covers the same area as the camera image.
        # But wait, the camera image is Rotated. 
        # If we draw in "screen coordinates" (Portrait 480x800), we need to transform.
        # Detection (x, y, w, h) in 640x480.
        
        # TRANSFORMATION LOGIC:
        # Camera: 640x480 (Landscape)
        # Screen: 480x800 (Portrait)
        # The `cam_display` is rotated 90 degrees.
        # So Camera X becomes Screen Y. Camera Y becomes Screen -X (or similar).
        
        norm_w, norm_h = self.size # This widget's size (should match screen/layout)
        
        with self.canvas.after:
            
            # --- DETECTIONS ---
            if "detections" in metadata:
                Color(0, 1, 0, 1)
                for det in metadata["detections"]:
                    xmin, ymin, xmax, ymax = det["bbox"]
                    
                    # ROTATION TRANSFORM (90 deg CCW)
                    # Camera (Landscape) -> Screen (Portrait)
                    # Camera X (0..1) -> Screen Y (1..0)  (Inverted relation: X decr = Y incr)
                    # Camera Y (0..1) -> Screen X (1..0)  (Inverted relation based on user feedback)
                    
                    # Point 1 (Bottom-Left on Screen)
                    # Screen X = 1.0 - Camera Ymin? 
                    # Let's check: Move Left -> Cam Y increases/decreases?
                    # Let's apply [1.0 - value] to both based on analysis.
                    
                    # Logic:
                    # Screen X = 1.0 - Camera Y
                    # Screen Y = 1.0 - Camera X
                    
                    # Since we are drawing a Box, we need min/max correct.
                    # If we invert, min becomes max.
                    
                    # Original Buffer: xmin, xmax, ymin, ymax.
                    
                    # Mapped:
                    # sx1 = 1.0 - ymin
                    # sx2 = 1.0 - ymax
                    # sy1 = 1.0 - xmin
                    # sy2 = 1.0 - xmax
                    
                    # Bounding Box needs (x, y, w, h) or (min, min, max, max).
                    # X Axis is CORRECT (User Verified): Screen X = 1.0 - Camera Y
                    # Y Axis is INVERTED (User Verified): Screen Y = 1.0 - Camera X -> Change to Screen Y = Camera X
                    
                    s_xmin = 1.0 - ymax
                    s_xmax = 1.0 - ymin
                    s_ymin = xmin
                    s_ymax = xmax
                    
                    # Scale
                    p1x = s_xmin * norm_w
                    # p1y corresponds to s_ymin
                    p1y = s_ymin * norm_h
                    p2x = s_xmax * norm_w
                    # p2y corresponds to s_ymax
                    p2y = s_ymax * norm_h
                    
                    # Draw Rect
                    # Rect pos is (x, y), size is (w, h)
                    # Kivy Rect: pos=(x,y), size=(w,h)
                    # Our Line rect should be (x, y, w, h)
                    # x = p1x, y = p1y
                    # w = p2x - p1x
                    # h = p2y - p1y
                    Line(rectangle=(p1x, p1y, p2x - p1x, p2y - p1y), width=1.5)
                    
                    # Draw Label
                    label_text = f"{det['label']} {det['confidence']:.2f}"
                    l = CoreLabel(text=label_text, font_size=20, color=(0, 1, 0, 1))
                    l.refresh()
                    tex = l.texture
                    
                    # Draw text above box (at p2y which is top)
                    Rectangle(texture=tex, pos=(p1x, p2y + 5), size=tex.size)

            # --- POSE ---
            if "pose" in metadata:
                for pose in metadata["pose"]:
                    # Keypoints
                    points = pose["keypoints"] # dict of "name": (x, y) normalized
                    
                    # Draw Skeleton first
                    Color(0, 0, 1, 1) # Blue
                    for start, end in pose["pairs"]:
                        if start in points and end in points:
                            x1, y1 = points[start]
                            x2, y2 = points[end]
                            
                            # Transform
                            # Screen X = 1.0 - Camera Y (y1/y2)
                            # Screen Y = Camera X (x1/x2)
                            sx1 = (1.0 - y1) * norm_w
                            sy1 = x1 * norm_h
                            sx2 = (1.0 - y2) * norm_w
                            sy2 = x2 * norm_h
                            
                            Line(points=[sx1, sy1, sx2, sy2], width=1.5)
                            
                    # Draw Points
                    Color(1, 1, 0, 1) # Yellow
                    for name, (px, py) in points.items():
                        sx = (1.0 - py) * norm_w
                        sy = px * norm_h
                        # Draw small circle (point)
                        Line(circle=(sx, sy, 3), width=1.5)
                        


KV = '''
MDScreen:
    md_bg_color: 0, 0, 0, 1

    MDFloatLayout:
        # LAYER 1: The Camera Display (Background)
        Image:
            id: cam_display
            source: "" 
            fit_mode: "fill"
            size_hint: 1, 1
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            opacity: 1 if app.active_mode != "voice" else 0.3

        # LAYER 1.5: Detection Overlay
        DetectionOverlay:
            id: overlay
            size_hint: 1, 1
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            opacity: 1 if app.active_mode != "voice" else 0


        # LAYER 2: Top Status Bar
        MDLabel:
            id: top_status_bar
            text: "CPU: 0% | RAM: 0% | TEMP: --°C | FPS: 0"
            halign: "center"
            pos_hint: {"center_x": 0.5, "top": 1.0}
            size_hint: 1, None
            height: "30dp"
            theme_text_color: "Custom"
            text_color: 0, 1, 0, 1
            font_style: "Label"
            bold: True
            canvas.before:
                Color:
                    rgba: 0, 0, 0, 0.5
                Rectangle:
                    pos: self.pos
                    size: self.size

        # LAYER 3: Main Status Label
        MDLabel:
            id: status_label
            text: "Status: Ready"
            halign: "center"
            pos_hint: {"center_x": 0.5, "top": 0.95}
            size_hint: 0.8, None
            height: "40dp"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            canvas.before:
                Color:
                    rgba: 0, 0, 0, 0.6
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [15]

        # LAYER 4: Voice Chat UI (Only visible in VOICE mode)
        MDFloatLayout:
            id: voice_ui
            opacity: 1 if app.active_mode == "voice" else 0
            disabled: True if app.active_mode != "voice" else False
            
            # Chat Display Area
            MDLabel:
                id: chat_display
                text: "Press Chat to Start..."
                halign: "center"
                valign: "middle"
                pos_hint: {"center_x": 0.5, "center_y": 0.6}
                size_hint: 0.9, 0.5
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                font_style: "Body"
            
            # Big Record Button
            MDButton:
                id: record_btn
                style: "filled"
                theme_bg_color: "Custom"
                md_bg_color: (1, 0, 0, 1) if app.is_recording else (0, 0.6, 1, 1)
                size_hint: None, None
                size: "100dp", "100dp"
                pos_hint: {"center_x": 0.5, "center_y": 0.25}
                radius: [50]
                on_release: app.toggle_voice_recording()
                
                MDButtonText:
                    text: "STOP" if app.is_recording else "CHAT"
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
                    font_style: "Title"

        # LAYER 5: Controls (Bottom)
        MDBoxLayout:
            orientation: "vertical"
            pos_hint: {"center_x": 0.5, "y": 0.03}
            size_hint: 0.95, None
            height: "140dp"
            spacing: "10dp"

            # Row 1: Mode Selectors
            MDBoxLayout:
                orientation: "horizontal"
                spacing: "10dp"
                MDButton:
                    style: "filled"
                    theme_bg_color: "Custom"
                    md_bg_color: 0.2, 0.8, 0.2, 1
                    size_hint_x: 0.33
                    on_release: app.switch_mode("detect")
                    MDButtonText:
                        text: "DETECT"
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}
                MDButton:
                    style: "filled"
                    theme_bg_color: "Custom"
                    md_bg_color: 0.6, 0.2, 0.8, 1
                    size_hint_x: 0.33
                    on_release: app.switch_mode("pose")
                    MDButtonText:
                        text: "POSE"
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}
                MDButton:
                    style: "filled"
                    theme_bg_color: "Custom"
                    md_bg_color: 1, 0.5, 0, 1
                    size_hint_x: 0.33
                    on_release: app.switch_mode("voice")
                    MDButtonText:
                        text: "VOICE"
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}

            # Row 2: Stream / Stop
            MDBoxLayout:
                orientation: "horizontal"
                spacing: "10dp"
                MDButton:
                    style: "filled"
                    theme_bg_color: "Custom"
                    md_bg_color: 0, 0.5, 1, 1
                    size_hint_x: 0.5
                    on_release: app.switch_mode("stream")
                    MDButtonText:
                        text: "STREAM"
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}
                MDButton:
                    style: "filled"
                    theme_bg_color: "Custom"
                    md_bg_color: 1, 0.2, 0.2, 1
                    size_hint_x: 0.5
                    on_release: app.switch_mode("stop")
                    MDButtonText:
                        text: "STOP"
                        pos_hint: {"center_x": 0.5, "center_y": 0.5}
'''

class AICameraApp(MDApp):
    active_mode = StringProperty("None")
    is_recording = BooleanProperty(False) # For KV binding

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_event = None
        self.stats_event = None
        
        # Engines
        self.stt_engine = STTEngine()
        self.chatbot = ChatBot(thinking=False)
        self.models_loaded = False
        
        # FPS calculation
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0

    def build(self):
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def on_start(self):
        # Start Status Bar Update Loop
        self.stats_event = Clock.schedule_interval(self.update_stats, 1.0)
        self.update_event = Clock.schedule_interval(self.update_texture, 1.0 / 30.0)
        
        # Default mode
        self.switch_mode("stream")
        
        # Background loading of models
        threading.Thread(target=self.load_models_background, daemon=True).start()

    def load_models_background(self):
        print("Starting background model loading...")
        # 1. Load Whisper
        self.stt_engine.load_model()
        # 2. Preload Ollama
        self.chatbot.preload_model()
        
        self.models_loaded = True
        Clock.schedule_once(lambda dt: self.update_status_label("Models Loaded & Ready"), 0)
        print("Models loaded.")

    def update_status_label(self, text):
        self.root.ids.status_label.text = text

    def on_stop(self):
        if self.update_event:
            self.update_event.cancel()
        if self.stats_event:
            self.stats_event.cancel()
        computer_vision.stop_task()
        self.stt_engine.terminate()

    def update_stats(self, dt):
        # Calculate FPS
        current_time = time.time()
        delta = current_time - self.last_time
        if delta > 0:
            current_fps = self.frame_count / delta
            self.fps = int(current_fps)
        self.frame_count = 0
        self.last_time = current_time
        
        # Get CPU Usage
        cpu_percent = psutil.cpu_percent()
        
        # Get RAM Usage
        ram_percent = psutil.virtual_memory().percent
        
        # Get CPU Temperature
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common sensor names
                for name in ['cpu_thermal', 'cpu-thermal', 'coretemp', 'soc_thermal']:
                    if name in temps:
                        cpu_temp = temps[name][0].current
                        break
                else:
                    # Use the first available sensor
                    first_key = next(iter(temps))
                    cpu_temp = temps[first_key][0].current
                temp_str = f"{cpu_temp:.0f}°C"
            else:
                temp_str = "N/A"
        except Exception:
            temp_str = "N/A"
        
        # Update Label
        self.root.ids.top_status_bar.text = f"CPU: {cpu_percent}% | RAM: {ram_percent}% | TEMP: {temp_str} | FPS: {self.fps}"

    def update_texture(self, dt):
        self.frame_count += 1
        # UNPACK TUPLE (Frame, Metadata)
        frame_data = computer_vision.get_latest_frame()
        if frame_data is None: 
            return
            
        frame, metadata = frame_data
        
        if frame is not None:
            h, w = frame.shape[:2]
            
            # Reuse texture if possible
            if not self.root.ids.cam_display.texture or self.root.ids.cam_display.texture.size != (w, h):
                self.root.ids.cam_display.texture = Texture.create(size=(w, h), colorfmt='rgb')
                # Setup rotation once
                if not getattr(self, 'rotation_applied', False):
                     self.setup_rotation()
                     self.rotation_applied = True
            
            self.root.ids.cam_display.texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            self.root.ids.cam_display.canvas.ask_update()
            
            # Update Overlay
            self.root.ids.overlay.update_draw(metadata, (w, h))

    def setup_rotation(self):
        img = self.root.ids.cam_display
        img.size_hint = (None, None)
        img.size = (800, 480) # Landscape logic size
        img.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        
        with img.canvas.before:
            from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
            PushMatrix()
            # Rotate 90 (Counter-Clockwise) to fit portrait
            self.rot = Rotate(angle=90, origin=img.center)
        with img.canvas.after:
            PopMatrix()
        img.bind(center=self.update_rotation_center)

    def update_rotation_center(self, instance, value):
        if hasattr(self, 'rot'):
            self.rot.origin = instance.center

    def toggle_voice_recording(self):
        if not self.models_loaded:
            self.update_status_label("Wait! Models loading...")
            return

        if not self.is_recording:
            # Start Recording
            self.is_recording = True
            self.root.ids.chat_display.text = "Listening..."
            self.stt_engine.start_capture()
        else:
            # Stop Recording
            self.is_recording = False
            self.root.ids.chat_display.text = "Processing Speech..."
            
            # Run processing in thread to not freeze UI
            threading.Thread(target=self.process_voice_interaction, daemon=True).start()

    def process_voice_interaction(self):
        # 1. Transcribe
        text = self.stt_engine.stop_and_transcribe()
        Clock.schedule_once(lambda dt: setattr(self.root.ids.chat_display, 'text', f"You: {text}\nThinking..."), 0)
        
        if not text:
            return

        # 2. Chatbot
        response = self.chatbot.generate_response(text)
        
        # 3. Update UI
        def update_ui(dt):
            self.root.ids.chat_display.text = f"You: {text}\n\nAI: {response}"
        
        Clock.schedule_once(update_ui, 0)

    def switch_mode(self, mode):
        # UI is handled by opacity bindings in KV essentially
        # But we need to update active_mode property
        
        status_label = self.root.ids.status_label
        if mode == self.active_mode: return

        status_label.text = f"Switching to {mode.upper()}..."
        
        # Stop previous tasks
        if self.active_mode != "stop":
            computer_vision.stop_task()

        self.active_mode = mode

        # Start new task
        if mode == "stop":
            status_label.text = "Status: Stopped"
            return
        
        target_func = None
        if mode == "stream": target_func = computer_vision.run_raw_camera_app
        elif mode == "detect": target_func = computer_vision.run_detection_app
        elif mode == "pose": target_func = computer_vision.run_pose_app
        elif mode == "voice": 
             # For voice, we might want a simple stream in background for visuals?
             # Or just pause camera? Let's keep stream running for cool vibes.
             target_func = computer_vision.run_raw_camera_app
        
        if target_func:
            computer_vision.start_task(target_func)
            status_label.text = f"Active: {mode.upper()}"

if __name__ == "__main__":
    AICameraApp().run()