import sys
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.screen import MDScreen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.texture import Texture

import computer_vision

Window.size = (480, 800)

KV = '''
MDScreen:
    md_bg_color: 0, 0, 0, 1  # Black background

    # 1. THE CAMERA DISPLAY
    Image:
        id: cam_display
        source: "" 
        allow_stretch: True
        keep_ratio: True
        pos_hint: {"center_x": 0.5, "center_y": 0.5}
        size_hint: 1, 1

    # 2. STATUS LABEL (On top)
    MDLabel:
        id: status_label
        text: "Status: Ready"
        halign: "center"
        pos_hint: {"center_x": 0.5, "top": 0.98}
        size_hint: 1, 0.05
        theme_text_color: "Custom"
        text_color: 1, 1, 1, 1
        
        canvas.before:
            Color:
                rgba: 0, 0, 0, 0.5
            Rectangle:
                pos: self.pos
                size: self.size

    # 3. CONTROLS (Bottom)
    MDBoxLayout:
        orientation: "vertical"
        pos_hint: {"center_x": 0.5, "y": 0.02}
        size_hint: 0.9, 0.25
        spacing: "15dp"

        # Row 1
        MDBoxLayout:
            orientation: "horizontal"
            spacing: "15dp"
            MDButton:
                style: "filled"
                md_bg_color: 0, 0.5, 1, 1
                size_hint_x: 0.5
                on_release: app.switch_mode("stream")
                MDButtonText:
                    text: "STREAM"
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
            MDButton:
                style: "filled"
                md_bg_color: 1, 0.2, 0.2, 1
                size_hint_x: 0.5
                on_release: app.switch_mode("stop")
                MDButtonText:
                    text: "STOP"
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}

        # Row 2
        MDBoxLayout:
            orientation: "horizontal"
            spacing: "15dp"
            MDButton:
                style: "filled"
                md_bg_color: 0.2, 0.8, 0.2, 1
                size_hint_x: 0.5
                on_release: app.switch_mode("detect")
                MDButtonText:
                    text: "DETECT"
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
            MDButton:
                style: "filled"
                md_bg_color: 0.6, 0.2, 0.8, 1
                size_hint_x: 0.5
                on_release: app.switch_mode("pose")
                MDButtonText:
                    text: "POSE"
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
'''

class AICameraApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_mode = "None"
        self.update_event = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def on_start(self):
        # Start the camera update loop (30 FPS)
        self.update_event = Clock.schedule_interval(self.update_texture, 1.0 / 30.0)
        self.switch_mode("stream")

    def on_stop(self):
        if self.update_event:
            self.update_event.cancel()
        computer_vision.stop_task()

    def update_texture(self, dt):
        """Called every frame. Fetches image from computer_vision thread."""
        frame = computer_vision.get_latest_frame()
        
        if frame is not None:
            # Note: GStreamer/OpenCV is often BGR, but Kivy needs RGB.
            # Depending on the Hailo output, you might need to flip colors.
            # If colors look blue/weird, uncomment the next line:
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Flip for Kivy display if needed (vertical flip)
            # frame = cv2.flip(frame, 0) 

            # Create Texture
            h, w = frame.shape[:2]
            texture = Texture.create(size=(w, h), colorfmt='rgb')
            texture.blit_buffer(frame.flatten(), colorfmt='rgb', bufferfmt='ubyte')
            
            # Apply to widget
            self.root.ids.cam_display.texture = texture

    def switch_mode(self, mode):
        status_label = self.root.ids.status_label
        if mode == self.active_mode: return

        status_label.text = f"Switching to {mode.upper()}..."
        if mode == "stop":
            computer_vision.stop_task()
            status_label.text = "Status: Stopped"
            self.active_mode = "stop"
            return

        target_func = None
        if mode == "stream": target_func = computer_vision.run_raw_camera_app
        elif mode == "detect": target_func = computer_vision.run_detection_app
        elif mode == "pose": target_func = computer_vision.run_pose_app

        if target_func:
            computer_vision.start_task(target_func)
            status_label.text = f"Status: Running {mode.upper()}"
            self.active_mode = mode

if __name__ == "__main__":
    AICameraApp().run()