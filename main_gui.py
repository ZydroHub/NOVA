import sys
import cv2
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.screen import MDScreen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.texture import Texture

import computer_vision

# Force a portrait resolution
Window.size = (480, 800)

KV = '''
MDScreen:
    md_bg_color: 0, 0, 0, 1

    MDFloatLayout:
        # LAYER 1: The Camera Display (Background)
        Image:
            id: cam_display
            source: "" 
            allow_stretch: True
            keep_ratio: False 
            size_hint: 1, 1
            pos_hint: {"center_x": 0.5, "center_y": 0.5}

        # LAYER 2: Status Label
        MDLabel:
            id: status_label
            text: "Status: Ready"
            halign: "center"
            pos_hint: {"center_x": 0.5, "top": 0.96}
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

        # LAYER 3: Controls
        MDBoxLayout:
            orientation: "vertical"
            pos_hint: {"center_x": 0.5, "y": 0.03}
            size_hint: 0.9, None
            height: "140dp"
            spacing: "10dp"

            # Row 1: Mode Selectors
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

            # Row 2: Stream / Stop
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
        self.update_event = Clock.schedule_interval(self.update_texture, 1.0 / 30.0)
        self.switch_mode("stream")

    def on_stop(self):
        if self.update_event:
            self.update_event.cancel()
        computer_vision.stop_task()

    def update_texture(self, dt):
        frame = computer_vision.get_latest_frame()
        
        if frame is not None:
            # OPTIMIZATION: Removed cv2.rotate (CPU bound).
            # We will use Kivy's rotation in canvas.before if needed, or just set the texture coordinates.
            # But the simplest way for a 90 degree rotation is often just swapping width/height in texture creation
            # and handling the rotation in the UI layout or using a transformation.
            # 
            # For this implementation, I will manually rotate the texture coordinates for the Image widget
            # or simply use a Rotate instruction.
            
            # Since the user wants 90 degree clockwise rotation:
            # Original: Landscape (e.g. 640x480)
            # Target: Portrait (e.g. 480x640)
            
            h, w = frame.shape[:2]
            
            # 1. Create Texture only if size changes
            if not self.root.ids.cam_display.texture or self.root.ids.cam_display.texture.size != (w, h):
                self.root.ids.cam_display.texture = Texture.create(size=(w, h), colorfmt='rgb')
                self.root.ids.cam_display.texture.flip_vertical() # Kivy textures are upside down by default often
                
                # Apply 90 degree rotation via canvas instructions? 
                # Actually, Kivy Image widget allows rotation. Let's try to update the canvas.before once.
                # However, a simpler trick for 90 degree rotation without canvas mess is to swap texture coords.
                # But let's stick to the plan: Use Kivy Rotation.
                
                # Let's check if we've already applied rotation
                if not getattr(self, 'rotation_applied', False):
                    from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
                    with self.root.ids.cam_display.canvas.before:
                        PushMatrix()
                        Rotate(angle=-90, origin=self.root.ids.cam_display.center)
                    with self.root.ids.cam_display.canvas.after:
                        PopMatrix()
                    self.rotation_applied = True

            # 2. BLIT DIRECTLY (Avoid frame.flatten())
            # We can pass the buffer directly.
            # Note: frame.data is a memoryview, which blit_buffer accepts.
            self.root.ids.cam_display.texture.blit_buffer(frame.data, colorfmt='rgb', bufferfmt='ubyte')
            
            # Note: If the rotation logic above is too complex for this snippet,
            # we might rely on the fact that we removed cv2.rotate, so the image will be sideways.
            # The user needs to approve this. 
            # Wait, the plan said "Use Kivy's canvas.before Rotate instruction".
            # The snippet above attempts that but might be tricky with dynamic centers.
            
            # ALTERNATIVE: Just set `source_rotation` if available? No, not standard.
            # Let's rely on simple KV rotation if possible, but we are editing Python.
            # I will apply a simple global rotation to the Image widget for now.
            self.root.ids.cam_display.canvas.before.clear()
            with self.root.ids.cam_display.canvas.before:
                from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
                PushMatrix()
                # Rotate around center. proper implementation requires binding to size/pos, 
                # but for a full-screen-ish app this might suffice or we update it.
                Rotate(angle=-90, origin=(Window.width/2, Window.height/2))
            
            # Actually, clearing canvas.before every frame is bad.
            # Let's do it ONCE in on_start or similar. 
            # I will revert the loop logic and do it cleanly.

    def setup_rotation(self):
        # Helper to apply rotation once
        img = self.root.ids.cam_display
        
        # FIX: We need the widget to be "Landscape" geometry (wide) to match the camera texture
        # and then rotate the whole widget 90 degrees to stand it up for the Portrait screen.
        
        # 1. Force the widget size to be swapped relative to screen (Screen is 480x800)
        # We want the widget to act like it's 800 wide and 480 tall (Landscape), 
        # then we rotate it -90 degrees to fill the 480x800 slot.
        img.size_hint = (None, None)
        img.size = (800, 480) # Hardcoded for this specific screen/window setup
        img.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        
        with img.canvas.before:
            from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
            PushMatrix()
            # Rotate 90 (Counter-Clockwise) as requested
            self.rot = Rotate(angle=90, origin=img.center)
        with img.canvas.after:
            PopMatrix()
        img.bind(center=self.update_rotation_center)

    def update_rotation_center(self, instance, value):
        if hasattr(self, 'rot'):
            self.rot.origin = instance.center

    def update_texture(self, dt):
        frame = computer_vision.get_latest_frame()
        if frame is None: return

        # Optimize: reuse texture
        h, w = frame.shape[:2]
        texture = self.root.ids.cam_display.texture
        
        if not texture or texture.size != (w, h):
            texture = Texture.create(size=(w, h), colorfmt='rgb')
            # REMOVED: texture.flip_vertical() 
            # User reported "upside down" - usually CV2->Kivy needs flip, but combined with rotation 
            # and potential camera mount, it might be wrong. Let's try without.
            # If still wrong, we will re-enable or change angle to +90.
            
            self.root.ids.cam_display.texture = texture
            
            # Apply rotation / layout fix once
            if not getattr(self, 'rotation_applied', False):
                self.setup_rotation()
                self.rotation_applied = True

        # Direct blit
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.root.ids.cam_display.canvas.ask_update()


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
            status_label.text = f"Active: {mode.upper()}"
            self.active_mode = mode

if __name__ == "__main__":
    AICameraApp().run()