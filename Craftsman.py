import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from tkinter.colorchooser import askcolor
from PIL import Image, ImageDraw, ImageTk, ImageColor, ImageFont
import os
import random
from collections import deque
import shutil
import math
import vlc

class KP2:
    def __init__(self, root):
        self.root = root
        self.root.title("Craftsman")
        image = Image.open("icon.png")
        photo = ImageTk.PhotoImage(image)
        root.iconphoto(True, photo)
        root.config(bg="#ece9d8") 

        # Ensure required directories exist
        os.makedirs("cache", exist_ok=True)
        os.makedirs("stamps", exist_ok=True)
        os.makedirs("gui", exist_ok=True)

        # Initial state
        self.saved = 1
        self.curpath = "NULL"
        self.current_tool = "pen"
        self.brush_size = 3
        self.colors = [
            "#000000", "#FFFFFF", "#A1A192", "#E6EAD8", "#980000", "#FF3300",
            "#E68B2C", "#FFAA00", "#9B6600", "#FFFF00", "#008D00", "#00FF00",
            "#003399", "#14A5F4", "#6487DC", "#FF00FF"
        ]
        self.oldcolors = [
            "#000000", "#FFFFFF", "#d4cfc7", "#c0c0c0", "#800000",
            "#FF0000", "#fb8046", "#844101", "#7a8305", "#FFFF00",
            "#008000", "#00FF00", "#008080", "#00FFFF", "#0000FF",
            "#0e7dcb", "#800080", "#FF00FF"
        ]
        self.current_color = "#000000"

        self.stamps_dir = "stamps"
        self.stamp_images = {}
        self.current_stamp = None

        # Canvas size
        self.image_width, self.image_height = 800, 600
        self.image = Image.new("RGBA", (self.image_width, self.image_height), "white")
        self.draw = ImageDraw.Draw(self.image)

        # Undo/redo stacks
        self.undo_stack = deque(maxlen=20)
        self.redo_stack = deque(maxlen=20)

        # Load resources
        self.load_stamps()
        self.gui_dir = "gui"
        self.load_gui_icons()

        # Build UI
        self.build_ui()

        # Drawing state
        self.last_x = self.last_y = None
        self.start_x = self.start_y = None
        self.temp_preview_image = None

        # Bindings
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_paint)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

        self.create_menu()
        self.update_bottom_panel()
        self.save_undo()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # VLC player instance
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.loop = True
        self.is_playing = False
        self.updating_slider = False  # Flag to avoid conflict during slider update

    def load_gui_icons(self):
        self.icons = {}
        icon_files = {
            "pen": "pen.png",
            "line": "line.png",
            "square": "square.png",
            "circle": "circle.png",
            "spray": "spray.png",
            "paintbucket": "paintbucket.png",
            "text": "text.png",
            "stamp": "stamp.png",
            "eraser": "eraser.png",
            "undo": "undo.png",
            "redo": "redo.png",
            "addcustom": "add.png",
        }
        for tool, filename in icon_files.items():
            path = os.path.join(self.gui_dir, filename)
            try:
                img = Image.open(path).resize((32, 32))
                self.icons[tool] = ImageTk.PhotoImage(img)
            except Exception:
                self.icons[tool] = None

        brush_icons = {
            "small": "small.png",
            "medium": "medium.png",
            "large": "large.png"
        }
        self.brush_icons = {}
        for size, filename in brush_icons.items():
            path = os.path.join(self.gui_dir, filename)
            try:
                img = Image.open(path).resize((32, 32))
                self.brush_icons[size] = ImageTk.PhotoImage(img)
            except Exception:
                self.brush_icons[size] = None

        color_icon_path = os.path.join(self.gui_dir, "color.png")
        try:
            img = Image.open(color_icon_path).resize((32, 32))
            self.color_icon = ImageTk.PhotoImage(img)
        except Exception:
            self.color_icon = None

    def build_ui(self):
        self.main_frame = tk.Frame(self.root, bg="#ece9d8")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Sidebar for tools
        self.sidebar = tk.Frame(self.main_frame, width=100, bg="#ece9d8")
        self.sidebar.pack(side=tk.LEFT)
        self.setup_sidebar()

        # Main drawing canvas
        self.canvas = tk.Canvas(self.main_frame, bg="white",
                                width=self.image_width, height=self.image_height)
        self.canvas.pack(side=tk.LEFT, anchor="nw", fill=None, expand=False)
        self.canvas.pack(side=tk.TOP)
        self.img_for_tk = ImageTk.PhotoImage(self.image)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor="nw", image=self.img_for_tk)

        # Bottom panel for colors, brush sizes, stamps
        self.bottom_panel = tk.Frame(self.root, height=50, bg="#ece9d8")
        self.bottom_panel.pack(side=tk.BOTTOM, fill=tk.X)
        self.setup_bottom_panel()

    def setup_sidebar(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # Create a frame just for tool buttons
        tools_frame = tk.Frame(self.sidebar, bg="#ece9d8")
        tools_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        btns = [
            ("pen", self.use_pen),
            ("spray", self.use_spray),
            ("line", self.use_line),
            ("square", self.use_square),
            ("circle", self.use_circle),
            ("paintbucket", self.use_paintbucket),
            ("text", self.use_text),
            ("stamp", self.use_stamps),
            ("eraser", self.use_eraser),
            ("undo", self.undo),
            ("redo", self.redo)
        ]

        for name, cmd in btns:
            icon = self.icons.get(name)
            if icon:
                btn = tk.Button(self.sidebar, image=icon, command=cmd, bg="#ece9d8")
            else:
                btn = tk.Button(self.sidebar, text=name.capitalize(), command=cmd, bg="#ece9d8")
            btn.pack(side=tk.TOP, pady=2, fill=tk.X)

        # Create a frame for brush sizes below tools
        brush_frame = tk.Frame(self.sidebar, bg="#ece9d8")
        brush_frame.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        tk.Label(brush_frame, text="Brush Size:", bg="#ece9d8").pack(pady=(0, 3))

        for name, size in [("small", 1), ("medium", 5), ("large", 10)]:
            icon = self.brush_icons.get(name)
            if icon:
                btn = tk.Button(brush_frame, image=icon, command=lambda s=size: self.set_brush_size(s), bg="#ece9d8")
            else:
                btn = tk.Button(brush_frame, text=name.capitalize(), command=lambda s=size: self.set_brush_size(s), bg="#ece9d8")
            btn.pack(pady=2, fill=tk.X)

    def setup_bottom_panel(self):
        for widget in self.bottom_panel.winfo_children():
            widget.destroy()

        self.color_frame = tk.Frame(self.bottom_panel, bg="#ece9d8")
        self.color_frame.pack(fill=tk.X, expand=True)

        self.eraser_frame = tk.Frame(self.bottom_panel, bg="#ece9d8")

        # Basic Eraser button (can expand if needed)
        eraser_icon = self.icons.get("eraser")
        if eraser_icon:
            tk.Button(
                self.eraser_frame,
                image=eraser_icon,
                command=lambda: self.set_brush_size(10),
                bg="#ece9d8"
            ).pack(padx=5, pady=5)
        else:
            tk.Button(
                self.eraser_frame,
                text="Basic Eraser",
                command=lambda: self.set_brush_size(10),
                bg="#ece9d8"
            ).pack(padx=5, pady=5)

        self.stamps_frame = tk.Frame(self.bottom_panel, bg="#ece9d8")

        self.stamp_photoimages = {}
        for stamp_name, pil_img in self.stamp_images.items():
            btn_img = pil_img.resize((32, 32))
            photo_img = ImageTk.PhotoImage(btn_img)
            self.stamp_photoimages[stamp_name] = photo_img
            btn = tk.Button(self.stamps_frame, image=photo_img,
                            command=lambda name=stamp_name: self.select_stamp(name), bg="#ece9d8")
            btn.pack(side=tk.LEFT, padx=3, pady=5)

        # Add button to load custom stamp
        add_stamp_icon = self.icons.get("addcustom")
        if add_stamp_icon:
            add_stamp_btn = tk.Button(self.stamps_frame, image=add_stamp_icon,
                                      command=self.add_custom_stamp, bg="#ece9d8")
        else:
            add_stamp_btn = tk.Button(self.stamps_frame, text="+ Add Custom Stamp",
                                      command=self.add_custom_stamp, bg="#ece9d8")
        add_stamp_btn.pack(side=tk.LEFT, padx=5, pady=5)

        if self.color_icon:
            tk.Button(self.bottom_panel, image=self.color_icon, command=self.ask_custom_color, bg="#ece9d8").pack(side=tk.RIGHT, padx=5, pady=5)
        else:
            tk.Button(self.bottom_panel, text="Custom Color", command=self.ask_custom_color, bg="#ece9d8").pack(side=tk.RIGHT, padx=5, pady=5)

    def add_custom_stamp(self):
        path = filedialog.askopenfilename(
            title="Select Custom Stamp Image",
            filetypes=[("Image files", "*.png")]
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            # Resize to max 64x64 keeping aspect ratio
            img.thumbnail((64, 64), Image.LANCZOS)

            # Use file basename as key, add a number suffix if duplicate
            base_name = os.path.basename(path)
            name = base_name
            count = 1
            while name in self.stamp_images:
                name = f"{os.path.splitext(base_name)[0]}_{count}{os.path.splitext(base_name)[1]}"
                count += 1

            self.stamp_images[name] = img
            self.update_bottom_panel()
            self.current_stamp = name
            self.use_stamps()
            messagebox.showinfo("Stamp Added", f"Custom stamp '{name}' added successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load custom stamp:\n{e}")


    def ask_custom_color(self):
        color_code = askcolor(title="Choose custom color")
        if color_code and color_code[1]:
            self.set_color(color_code[1])

    def update_bottom_panel(self):
        # Hide all frames first
        for frame in [self.color_frame, self.eraser_frame, self.stamps_frame]:
            frame.pack_forget()

        if self.current_tool in ["pen", "spray", "line", "square", "circle", "paintbucket", "text"]:
            self.color_frame.pack(fill=tk.X, expand=True)
            # Clear previous color buttons
            for widget in self.color_frame.winfo_children():
                widget.destroy()
            # Add color buttons
            for c in self.colors:
                btn = tk.Button(self.color_frame, bg=c, width=2,
                                command=lambda col=c: self.set_color(col))
                btn.pack(side=tk.LEFT, padx=1, pady=5)
        elif self.current_tool == "eraser":
            self.eraser_frame.pack(fill=tk.X)
        elif self.current_tool == "stamps":
            self.stamps_frame.pack(fill=tk.X)

    def select_stamp(self, name):
        if name in self.stamp_images:
            self.current_stamp = name

    def create_menu(self):
        menubar = tk.Menu(self.root, bg="#ece9d8")
        file_menu = tk.Menu(menubar, tearoff=0, bg="#ece9d8")
        file_menu.add_command(label="New", command=self.new_canvas)
        file_menu.add_command(label="Open", command=self.open_canvas)
        file_menu.add_command(label="Save", command=self.normalsave_canvas)
        file_menu.add_command(label="Save As", command=self.save_canvas)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0, bg="#ece9d8")
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", "Craftsman Beta\nVersion: 0.9.0\nCreated by: Daniel Armstrong\n(C)2025 Daniel Armstrong"))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def new_canvas(self):
        if (self.saved == 0):
            response = messagebox.askyesnocancel("Save", "Do you want to save?")
            if response is True:  # Yes
                self.normalsave_canvas()
            elif response is False:  # No
                dummyvalue = 69
            elif response is None:  # Cancel
                return  # or whatever you want to do for cancel
        self.image = Image.new("RGBA", (self.image_width, self.image_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas_image()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_undo()
        self.curpath = "NULL"
        self.saved = 1
        
    def open_canvas(self):
        if (self.saved == 0):
            response = messagebox.askyesnocancel("Save", "Do you want to save?")
            if response is True:  # Yes
                self.normalsave_canvas()
            elif response is False:  # No
                dummyvalue = 69
            elif response is None:  # Cancel
                return  # or whatever you want to do for cancel
        path = filedialog.askopenfilename(filetypes=[("Portable Network Graphics", "*.png")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            self.curpath = path
            self.saved = 1
        except Exception as e:
            messagebox.showerror("Open Error", f"Cannot open image:\n{e}")
            return

        # Resize image with aspect ratio and center it
        img.thumbnail((self.image_width, self.image_height), Image.LANCZOS)
        new_img = Image.new("RGBA", (self.image_width, self.image_height), "white")
        offset = ((self.image_width - img.width) // 2, (self.image_height - img.height) // 2)
        new_img.paste(img, offset)
        self.image = new_img
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas_image()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_undo()
    def save_canvas(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if path: 
            try:
                self.image.save(path, "PNG")
                self.curpath = path
            except Exception as e:
                messagebox.showerror("Save Error", f"Cannot save image:\n{e}")

    def normalsave_canvas(self):
        if (self.curpath == "NULL"):
            self.save_canvas()
        else:
            try:
                self.image.save(self.curpath, "PNG")
            except Exception as e:
                messagebox.showerror("Save Error", f"Cannot save image:\n{e}")


    # TOOL SELECTORS
    def use_pen(self): self.current_tool = "pen"; self.update_bottom_panel()
    def use_spray(self): self.current_tool = "spray"; self.update_bottom_panel()
    def use_line(self): self.current_tool = "line"; self.update_bottom_panel()
    def use_square(self): self.current_tool = "square"; self.update_bottom_panel()
    def use_circle(self): self.current_tool = "circle"; self.update_bottom_panel()
    def use_paintbucket(self): self.current_tool = "paintbucket"; self.update_bottom_panel()
    def use_text(self): self.current_tool = "text"; self.update_bottom_panel()
    def use_stamps(self): self.current_tool = "stamps"; self.update_bottom_panel()
    def use_eraser(self): self.current_tool = "eraser"; self.update_bottom_panel()

    def set_brush_size(self, size):
        self.brush_size = size

    def set_color(self, color):
        self.current_color = color

    def load_stamps(self):
        self.stamp_images = {}
        for file in os.listdir(self.stamps_dir):
            if file.lower().endswith((".png")):
                try:
                    img = Image.open(os.path.join(self.stamps_dir, file)).convert("RGBA")
                    self.stamp_images[file] = img
                except Exception:
                    pass

    def on_button_press(self, event):
        self.saved = 0
        self.last_x, self.last_y = event.x, event.y
        self.start_x, self.start_y = event.x, event.y
        if self.current_tool == "paintbucket":
            self.paint_bucket(event.x, event.y)
            self.apply_stamp(event.x, event.y)
            player = vlc.MediaPlayer("audio/paintbucket.wav")
            player.play()
        elif self.current_tool == "text":
            self.insert_text(event.x, event.y)
            self.apply_stamp(event.x, event.y)
            player = vlc.MediaPlayer("audio/text.wav")
            player.play()
        elif self.current_tool == "stamps" and self.current_stamp:
            self.apply_stamp(event.x, event.y)
            player = vlc.MediaPlayer("audio/stamp.wav")
            player.play()
            self.save_undo()
        elif self.current_tool == "eraser":
            self.erase(event.x, event.y)
            self.save_undo()
        elif self.current_tool == "pen":
            self.draw.line([(self.last_x, self.last_y), (event.x, event.y)], fill=self.current_color, width=self.brush_size)
            self.update_canvas_image()
            player = vlc.MediaPlayer("audio/pen.wav")
            player.play()
            player.get_media().add_option("input-repeat=-1")
        elif self.current_tool == "spray":
            self.spray(event.x, event.y)
            self.update_canvas_image()
            player = vlc.MediaPlayer("audio/spray.wav")
            player.play()
            player.get_media().add_option("input-repeat=-1")
            


    def on_paint(self, event):
        if self.current_tool == "pen":
            self.draw.line([(self.last_x, self.last_y), (event.x, event.y)], fill=self.current_color, width=self.brush_size)
            self.last_x, self.last_y = event.x, event.y
            self.update_canvas_image()
        elif self.current_tool == "spray":
            self.spray(event.x, event.y)
            self.update_canvas_image()
        else:
            # For shape tools, draw a preview
            self.draw_preview(event.x, event.y)

    def on_button_release(self, event):
        if self.current_tool in ["line", "square", "circle"]:
            self.draw_shape(self.start_x, self.start_y, event.x, event.y)
            self.update_canvas_image()
            self.save_undo()
        elif self.current_tool == "pen":
            self.save_undo()
        elif self.current_tool == "spray":
            self.save_undo()
        elif self.current_tool == "eraser":
            self.save_undo()

        self.last_x = self.last_y = None
        self.start_x = self.start_y = None
        self.temp_preview_image = None

    def draw_preview(self, x, y):
        # Draw a temporary preview on canvas for shapes without affecting the image
        if self.temp_preview_image:
            self.canvas.delete(self.temp_preview_image)
        preview_img = self.image.copy()
        preview_draw = ImageDraw.Draw(preview_img)
        if self.current_tool == "line":
            preview_draw.line([(self.start_x, self.start_y), (x, y)], fill=self.current_color, width=self.brush_size)
        elif self.current_tool == "square":
            preview_draw.rectangle([self.start_x, self.start_y, x, y], outline=self.current_color, width=self.brush_size)
        elif self.current_tool == "circle":
            preview_draw.ellipse([self.start_x, self.start_y, x, y], outline=self.current_color, width=self.brush_size)
        tk_img = ImageTk.PhotoImage(preview_img)
        self.temp_preview_image = self.canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self.canvas.image = tk_img  # keep reference

    def draw_shape(self, x1, y1, x2, y2):
        if self.current_tool == "line":
            self.draw.line([(x1, y1), (x2, y2)], fill=self.current_color, width=self.brush_size)
        elif self.current_tool == "square":
            self.draw.rectangle([x1, y1, x2, y2], outline=self.current_color, width=self.brush_size)
        elif self.current_tool == "circle":
            self.draw.ellipse([x1, y1, x2, y2], outline=self.current_color, width=self.brush_size)
        self.player = vlc.MediaPlayer("audio/shape.wav")
        self.player.play()

    def spray(self, x, y):
        for _ in range(self.brush_size * 10):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, self.brush_size)
            dx = int(radius * math.cos(angle))
            dy = int(radius * math.sin(angle))
            px, py = x + dx, y + dy
            if 0 <= px < self.image_width and 0 <= py < self.image_height:
                self.draw.point((px, py), fill=self.current_color)

    def paint_bucket(self, x, y):
        target_color = self.image.getpixel((x, y))
        fill_color = ImageColor.getrgb(self.current_color)

        if target_color[:3] == fill_color[:3]:
            return  # no need to fill if same color

        pixels = self.image.load()
        width, height = self.image.size
        edge = [(x, y)]
        while edge:
            nx, ny = edge.pop()
            if 0 <= nx < width and 0 <= ny < height:
                current_color = pixels[nx, ny]
                if current_color[:3] == target_color[:3]:
                    pixels[nx, ny] = fill_color + (255,)
                    edge.extend([(nx+1, ny), (nx-1, ny), (nx, ny+1), (nx, ny-1)])

        self.update_canvas_image()
        self.save_undo()

    def insert_text(self, x, y):
        text = simpledialog.askstring("Text", "Enter text:")
        if not text: return
        size = simpledialog.askinteger("Text Tool", "Enter text size:", minvalue=8, maxvalue=200)
        if not size: return

        try:
            font = ImageFont.truetype("arial.ttf", size)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size)
            except:
                font = ImageFont.load_default()

        bbox = self.draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        self.draw.text((x - w // 2, y - h // 2), text, fill=self.current_color, font=font)
        self.update_canvas_image()


    def apply_stamp(self, x, y):
        if not self.current_stamp or self.current_stamp not in self.stamp_images:
            return
        stamp = self.stamp_images[self.current_stamp]
        w, h = stamp.size
        pos = (x - w // 2, y - h // 2)
        self.image.paste(stamp, pos, stamp)
        self.update_canvas_image()

    def erase(self, x, y):
        bbox = [x - self.brush_size, y - self.brush_size, x + self.brush_size, y + self.brush_size]
        self.draw.ellipse(bbox, fill="white")
        self.update_canvas_image()

    def update_canvas_image(self):
        self.img_for_tk = ImageTk.PhotoImage(self.image)
        self.canvas.itemconfig(self.image_on_canvas, image=self.img_for_tk)
        self.canvas.image = self.img_for_tk  # keep reference

    def save_undo(self):
        if len(self.undo_stack) >= 20:
            self.undo_stack.popleft()
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            last = self.undo_stack.pop()
            self.redo_stack.append(self.image.copy())
            self.image = last
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas_image()

    def redo(self):
        if self.redo_stack:
            last = self.redo_stack.pop()
            self.undo_stack.append(self.image.copy())
            self.image = last
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas_image()

    def on_close(self):
        try:
            if (self.saved == 0):
                response = messagebox.askyesnocancel("Save", "Do you want to save?")
            if response is True:  # Yes
                self.normalsave_canvas()
            elif response is False:  # No
                dummyvalue = 69
            elif response is None:  # Cancel
                return  # or whatever you want to do for cancel
            else:
                dummyvalue = 69
        except:
            dummyvalue = 69
        os.rmdir("cache")
        self.root.destroy()


def main():
    root = tk.Tk()
    app = KP2(root)
    root.mainloop()

if __name__ == "__main__":
    main()
##
