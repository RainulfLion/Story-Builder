# standalone_map_editor.py
import pygame
import pygame_gui
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import sys
import uuid
import shutil
import json
from pathlib import Path

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database import Database

class StandaloneMapEditor:
    def __init__(self):
        pygame.init()
        
        # Screen setup
        self.screen = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
        pygame.display.set_caption("Gemini TTS - Map Editor")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # UI Manager
        self.gui_manager = pygame_gui.UIManager((1200, 800))
        
        # Database connection
        self.db = Database()
        
        # Map editor state
        self.current_map = None
        self.map_image = None
        self.map_surface = None
        self.map_name = "Untitled Map"
        self.map_id = None
        
        # Grid settings
        self.grid_size = 50
        self.grid_visible = True
        self.grid_color = pygame.Color(128, 128, 128)
        self.grid_opacity = 128
        
        # Camera and view
        self.camera_x = 0
        self.camera_y = 0
        self.zoom_level = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 3.0
        
        # Drawing tools
        self.current_tool = "select"  # select, wall, door, erase, location
        self.walls = set()
        self.doors = set()
        self.locations = []
        
        # UI state
        self.is_panning = False
        self.last_mouse_pos = None
        self.drawing = False
        
        # Define UI areas
        self.toolbar_height = 60
        self.sidebar_width = 250
        self.map_area = pygame.Rect(0, self.toolbar_height, 1200 - self.sidebar_width, 800 - self.toolbar_height)
        self.sidebar_area = pygame.Rect(1200 - self.sidebar_width, self.toolbar_height, self.sidebar_width, 800 - self.toolbar_height)
        
        self.create_ui()
        
    def create_ui(self):
        """Create the UI elements for the map editor."""
        # Toolbar buttons
        button_width = 80
        button_height = 40
        button_y = 10
        x_pos = 10
        
        # File operations
        self.new_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='New',
            manager=self.gui_manager,
            object_id='#new_map_button'
        )
        x_pos += button_width + 10
        
        self.load_image_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Load Image',
            manager=self.gui_manager,
            object_id='#load_image_button'
        )
        x_pos += button_width + 10
        
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Save',
            manager=self.gui_manager,
            object_id='#save_map_button'
        )
        x_pos += button_width + 10
        
        self.load_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Load Map',
            manager=self.gui_manager,
            object_id='#load_map_button'
        )
        x_pos += button_width + 20
        
        # Tools
        self.select_tool_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Select',
            manager=self.gui_manager,
            object_id='#select_tool_button'
        )
        x_pos += button_width + 10
        
        self.wall_tool_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Wall',
            manager=self.gui_manager,
            object_id='#wall_tool_button'
        )
        x_pos += button_width + 10
        
        self.door_tool_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Door',
            manager=self.gui_manager,
            object_id='#door_tool_button'
        )
        x_pos += button_width + 10
        
        self.location_tool_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Location',
            manager=self.gui_manager,
            object_id='#location_tool_button'
        )
        x_pos += button_width + 10
        
        self.erase_tool_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x_pos, button_y, button_width, button_height),
            text='Erase',
            manager=self.gui_manager,
            object_id='#erase_tool_button'
        )
        
        # Sidebar elements
        sidebar_y = 10
        
        # Map name input
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, sidebar_y, 200, 20),
            text='Map Name:',
            manager=self.gui_manager,
            container=None
        )
        sidebar_y += 25
        
        self.map_name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 200, 30),
            manager=self.gui_manager,
            initial_text=self.map_name,
            object_id='#map_name_input'
        )
        sidebar_y += 40
        
        # Help text
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 230, 80),
            text='<b>Controls:</b><br>'
                 '• Right-click/Middle-click: Pan<br>'
                 '• Space + Left-click: Pan<br>'
                 '• Mouse wheel: Zoom<br>'
                 '• Left-click: Use tool',
            manager=self.gui_manager
        )
        sidebar_y += 90
        
        # Grid settings
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 200, 20),
            text='Grid Settings:',
            manager=self.gui_manager
        )
        sidebar_y += 30
        
        # Grid size slider
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 100, 20),
            text=f'Grid Size: {self.grid_size}',
            manager=self.gui_manager,
            object_id='#grid_size_label'
        )
        sidebar_y += 25
        
        self.grid_size_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 200, 20),
            start_value=self.grid_size,
            value_range=(10, 200),
            manager=self.gui_manager,
            object_id='#grid_size_slider'
        )
        sidebar_y += 30
        
        # Grid visibility toggle
        self.grid_toggle = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 100, 30),
            text='Grid: ON' if self.grid_visible else 'Grid: OFF',
            manager=self.gui_manager,
            object_id='#grid_toggle_button'
        )
        sidebar_y += 40
        
        # Layers panel
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 200, 20),
            text='Layers:',
            manager=self.gui_manager
        )
        sidebar_y += 30
        
        # Layer list (walls, doors, locations)
        self.layer_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(1200 - self.sidebar_width + 10, self.toolbar_height + sidebar_y, 200, 150),
            item_list=['Walls', 'Doors', 'Locations'],
            manager=self.gui_manager,
            object_id='#layer_list'
        )
        
    def handle_events(self):
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_s and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    self.save_map()
                elif event.key == pygame.K_o and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    self.load_map_dialog()
                elif event.key == pygame.K_n and pygame.key.get_pressed()[pygame.K_LCTRL]:
                    self.new_map()
                    
            # Handle mouse events for map interaction
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.map_area.collidepoint(event.pos):
                    self.handle_map_click(event)
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                # Stop panning on any mouse button release
                if event.button in [1, 2, 3]:  # Left, middle, or right mouse button
                    self.is_panning = False
                    self.drawing = False
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.is_panning and self.map_area.collidepoint(event.pos):
                    if self.last_mouse_pos:
                        dx = event.pos[0] - self.last_mouse_pos[0]
                        dy = event.pos[1] - self.last_mouse_pos[1]
                        self.camera_x -= dx / self.zoom_level
                        self.camera_y -= dy / self.zoom_level
                    self.last_mouse_pos = event.pos
                elif self.drawing and self.current_tool in ["wall", "door", "erase"]:
                    # Allow continuous drawing/erasing while holding mouse button
                    if self.map_area.collidepoint(event.pos):
                        map_x, map_y = self.screen_to_map_coords(event.pos)
                        grid_x, grid_y = self.map_to_grid_coords(map_x, map_y)
                        
                        if self.current_tool == "wall":
                            self.walls.add((grid_x, grid_y))
                        elif self.current_tool == "door":
                            self.doors.add((grid_x, grid_y))
                        elif self.current_tool == "erase":
                            self.walls.discard((grid_x, grid_y))
                            self.doors.discard((grid_x, grid_y))
                    
            elif event.type == pygame.MOUSEWHEEL:
                if self.map_area.collidepoint(pygame.mouse.get_pos()):
                    # Zoom in/out
                    old_zoom = self.zoom_level
                    if event.y > 0:
                        self.zoom_level = min(self.max_zoom, self.zoom_level * 1.1)
                    else:
                        self.zoom_level = max(self.min_zoom, self.zoom_level * 0.9)
                    
                    # Adjust camera to zoom towards mouse position
                    if old_zoom != self.zoom_level:
                        mouse_pos = pygame.mouse.get_pos()
                        map_mouse_x = (mouse_pos[0] - self.map_area.left) / old_zoom + self.camera_x
                        map_mouse_y = (mouse_pos[1] - self.map_area.top) / old_zoom + self.camera_y
                        
                        self.camera_x = map_mouse_x - (mouse_pos[0] - self.map_area.left) / self.zoom_level
                        self.camera_y = map_mouse_y - (mouse_pos[1] - self.map_area.top) / self.zoom_level
            
            # Handle UI events
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                self.handle_ui_button(event)
                
            elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.grid_size_slider:
                    self.grid_size = int(event.value)
                    # Update label
                    for element in self.gui_manager.get_root_container().elements:
                        if hasattr(element, 'object_id') and element.object_id == '#grid_size_label':
                            element.set_text(f'Grid Size: {self.grid_size}')
                            
            elif event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
                if event.ui_element == self.map_name_input:
                    self.map_name = event.text
            
            self.gui_manager.process_events(event)
            
    def handle_ui_button(self, event):
        """Handle UI button presses."""
        # Use event.ui_object_id for button identification
        if event.ui_object_id == '#new_map_button':
            self.new_map()
        elif event.ui_object_id == '#load_image_button':
            self.load_image()
        elif event.ui_object_id == '#save_map_button':
            self.save_map()
        elif event.ui_object_id == '#load_map_button':
            self.load_map_dialog()
        elif event.ui_object_id == '#select_tool_button':
            self.current_tool = "select"
            self.update_tool_buttons()
        elif event.ui_object_id == '#wall_tool_button':
            self.current_tool = "wall"
            self.update_tool_buttons()
        elif event.ui_object_id == '#door_tool_button':
            self.current_tool = "door"
            self.update_tool_buttons()
        elif event.ui_object_id == '#location_tool_button':
            self.current_tool = "location"
            self.update_tool_buttons()
        elif event.ui_object_id == '#erase_tool_button':
            self.current_tool = "erase"
            self.update_tool_buttons()
        elif event.ui_object_id == '#grid_toggle_button':
            self.grid_visible = not self.grid_visible
            event.ui_element.set_text('Grid: ON' if self.grid_visible else 'Grid: OFF')
            
    def update_tool_buttons(self):
        """Update the visual state of tool buttons."""
        tools = {
            'select': self.select_tool_button,
            'wall': self.wall_tool_button,
            'door': self.door_tool_button,
            'location': self.location_tool_button,
            'erase': self.erase_tool_button
        }
        
        for tool_name, button in tools.items():
            if tool_name == self.current_tool:
                button.background_colour = pygame.Color(100, 150, 200)
            else:
                button.background_colour = pygame.Color(128, 128, 128)
            button.rebuild()
            
    def handle_map_click(self, event):
        """Handle mouse clicks on the map area."""
        # Check for panning modes
        keys = pygame.key.get_pressed()
        
        # Middle mouse button or right mouse button - start panning
        if event.button == 2 or event.button == 3:
            self.is_panning = True
            self.last_mouse_pos = event.pos
            return
            
        # Spacebar + left click - start panning
        if event.button == 1 and (keys[pygame.K_SPACE] or self.current_tool == "select"):
            self.is_panning = True
            self.last_mouse_pos = event.pos
            return
            
        if event.button == 1:  # Left mouse button for drawing
            # Convert screen coordinates to map coordinates
            map_x, map_y = self.screen_to_map_coords(event.pos)
            grid_x, grid_y = self.map_to_grid_coords(map_x, map_y)
            
            if self.current_tool == "wall":
                self.drawing = True
                wall_pos = (grid_x, grid_y)
                if wall_pos in self.walls:
                    self.walls.remove(wall_pos)
                else:
                    self.walls.add(wall_pos)
                    
            elif self.current_tool == "door":
                self.drawing = True
                door_pos = (grid_x, grid_y)
                if door_pos in self.doors:
                    self.doors.remove(door_pos)
                else:
                    self.doors.add(door_pos)
                    
            elif self.current_tool == "location":
                self.create_location(map_x, map_y)
                
            elif self.current_tool == "erase":
                self.drawing = True
                # Remove both walls and doors at this position
                self.walls.discard((grid_x, grid_y))
                self.doors.discard((grid_x, grid_y))
                
    def screen_to_map_coords(self, screen_pos):
        """Convert screen coordinates to map coordinates."""
        map_x = (screen_pos[0] - self.map_area.left) / self.zoom_level + self.camera_x
        map_y = (screen_pos[1] - self.map_area.top) / self.zoom_level + self.camera_y
        return int(map_x), int(map_y)
        
    def map_to_grid_coords(self, map_x, map_y):
        """Convert map coordinates to grid coordinates."""
        grid_x = map_x // self.grid_size
        grid_y = map_y // self.grid_size
        return int(grid_x), int(grid_y)
        
    def create_location(self, x, y):
        """Create a location at the specified coordinates."""
        root = tk.Tk()
        root.withdraw()
        
        location_name = simpledialog.askstring("Location Name", "Enter location name:", parent=root)
        if location_name:
            location_type = simpledialog.askstring("Location Type", "Enter location type (city, inn, dungeon, etc.):", 
                                                 initialvalue="generic", parent=root)
            
            location = {
                'name': location_name,
                'type': location_type or "generic",
                'x': x,
                'y': y,
                'notes': '',
                'audio_file': None,
                'sub_map_id': None
            }
            
            self.locations.append(location)
            
        root.destroy()
        
    def new_map(self):
        """Create a new map."""
        if self.has_unsaved_changes():
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Continue anyway?"):
                return
                
        self.current_map = None
        self.map_image = None
        self.map_surface = None
        self.map_name = "Untitled Map"
        self.map_id = None
        self.walls.clear()
        self.doors.clear()
        self.locations.clear()
        self.camera_x = 0
        self.camera_y = 0
        self.zoom_level = 1.0
        
        self.map_name_input.set_text(self.map_name)
        
    def load_image(self):
        """Load a background image for the map."""
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="Select Map Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ],
            parent=root
        )
        
        root.destroy()
        
        if file_path:
            try:
                self.map_image = pygame.image.load(file_path).convert_alpha()
                self.map_surface = self.map_image.copy()
                
                # Center the camera on the image
                self.camera_x = 0
                self.camera_y = 0
                
                print(f"Loaded image: {file_path}")
                
            except pygame.error as e:
                messagebox.showerror("Error", f"Could not load image: {e}")
                
    def save_map(self):
        """Save the current map to the database."""
        if not self.map_image:
            messagebox.showwarning("No Image", "Please load an image first.")
            return
            
        if not self.map_name.strip():
            messagebox.showwarning("No Name", "Please enter a map name.")
            return
            
        try:
            # Save image to data directory
            os.makedirs("data/images", exist_ok=True)
            
            if self.map_id:
                image_filename = f"map_{self.map_id}.png"
            else:
                image_filename = f"map_{uuid.uuid4().hex[:8]}.png"
                
            image_path = os.path.join("data/images", image_filename)
            pygame.image.save(self.map_image, image_path)
            
            # Prepare map data
            map_data = {
                'id': self.map_id,
                'name': self.map_name.strip(),
                'image_path': image_path,
                'grid_size': self.grid_size,
                'grid_enabled': self.grid_visible,
                'width': self.map_image.get_width(),
                'height': self.map_image.get_height(),
                'grid_color': f"#{self.grid_color.r:02x}{self.grid_color.g:02x}{self.grid_color.b:02x}",
                'map_scale': 1.0,
                'grid_style': 'solid',
                'grid_opacity': self.grid_opacity / 255.0
            }
            
            # Save to database
            saved_id = self.db.save_or_update_map(map_data)
            
            if saved_id:
                self.map_id = saved_id
                
                # Save walls
                self.db.cursor.execute("DELETE FROM map_walls WHERE map_id = ?", (self.map_id,))
                for wall_x, wall_y in self.walls:
                    self.db.cursor.execute(
                        "INSERT INTO map_walls (map_id, grid_x, grid_y) VALUES (?, ?, ?)",
                        (self.map_id, wall_x, wall_y)
                    )
                
                # Save doors
                self.db.cursor.execute("DELETE FROM map_doors WHERE map_id = ?", (self.map_id,))
                for door_x, door_y in self.doors:
                    self.db.cursor.execute(
                        "INSERT INTO map_doors (map_id, grid_x, grid_y) VALUES (?, ?, ?)",
                        (self.map_id, door_x, door_y)
                    )
                
                # Save locations
                self.db.cursor.execute("DELETE FROM map_locations WHERE map_id = ?", (self.map_id,))
                for location in self.locations:
                    self.db.cursor.execute(
                        "INSERT INTO map_locations (map_id, x, y, name) VALUES (?, ?, ?, ?)",
                        (self.map_id, location['x'], location['y'], location['name'])
                    )
                
                self.db.conn.commit()
                
                messagebox.showinfo("Success", f"Map '{self.map_name}' saved successfully!")
                
            else:
                messagebox.showerror("Error", "Failed to save map to database.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save map: {e}")
            
    def load_map_dialog(self):
        """Show dialog to load a map from the database."""
        try:
            maps = self.db.get_all_maps()
            if not maps:
                messagebox.showinfo("No Maps", "No maps found in database.")
                return
                
            # Create selection dialog
            root = tk.Tk()
            root.title("Load Map")
            root.geometry("400x300")
            
            tk.Label(root, text="Select a map to load:").pack(pady=10)
            
            listbox = tk.Listbox(root)
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            map_dict = {}
            for map_data in maps:
                map_id, name = map_data[0], map_data[1]
                display_name = f"{name} (ID: {map_id})"
                listbox.insert(tk.END, display_name)
                map_dict[display_name] = map_id
            
            def on_load():
                selection = listbox.curselection()
                if selection:
                    selected_item = listbox.get(selection[0])
                    map_id = map_dict[selected_item]
                    root.destroy()
                    self.load_map(map_id)
                else:
                    messagebox.showwarning("No Selection", "Please select a map to load.")
            
            def on_cancel():
                root.destroy()
            
            button_frame = tk.Frame(root)
            button_frame.pack(pady=10)
            
            tk.Button(button_frame, text="Load", command=on_load).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            root.mainloop()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load map list: {e}")
            
    def load_map(self, map_id):
        """Load a map from the database."""
        try:
            # Get map data
            map_data = self.db.get_map_by_id(map_id)
            if not map_data:
                messagebox.showerror("Error", f"Map with ID {map_id} not found.")
                return
                
            # Load image
            image_path = map_data['image_path']
            if not os.path.exists(image_path):
                messagebox.showerror("Error", f"Map image not found: {image_path}")
                return
                
            self.map_image = pygame.image.load(image_path).convert_alpha()
            self.map_surface = self.map_image.copy()
            
            # Set map properties
            self.map_id = map_data['id']
            self.map_name = map_data['name']
            self.grid_size = map_data['grid_size']
            self.grid_visible = map_data['grid_enabled']
            
            # Update UI
            self.map_name_input.set_text(self.map_name)
            self.grid_size_slider.set_current_value(self.grid_size)
            self.grid_toggle.set_text('Grid: ON' if self.grid_visible else 'Grid: OFF')
            
            # Load walls
            self.walls.clear()
            walls = self.db.get_map_walls(map_id)
            for wall_x, wall_y in walls:
                self.walls.add((wall_x, wall_y))
                
            # Load doors
            self.doors.clear()
            doors = self.db.get_map_doors(map_id)
            for door_x, door_y in doors:
                self.doors.add((door_x, door_y))
                
            # Load locations
            self.locations.clear()
            locations = self.db.get_map_locations(map_id)
            for loc_id, x, y, name in locations:
                self.locations.append({
                    'id': loc_id,
                    'name': name,
                    'x': x,
                    'y': y,
                    'type': 'generic',
                    'notes': '',
                    'audio_file': None,
                    'sub_map_id': None
                })
            
            # Reset camera
            self.camera_x = 0
            self.camera_y = 0
            self.zoom_level = 1.0
            
            print(f"Loaded map: {self.map_name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load map: {e}")
            
    def has_unsaved_changes(self):
        """Check if there are unsaved changes."""
        # This is a simplified check - in a real application you'd track changes more precisely
        return self.map_image is not None
        
    def draw(self):
        """Draw the map editor interface."""
        # Clear screen
        self.screen.fill((40, 40, 40))
        
        # Draw map area background
        pygame.draw.rect(self.screen, (50, 50, 50), self.map_area)
        pygame.draw.rect(self.screen, (100, 100, 100), self.map_area, 2)
        
        # Draw map if loaded
        if self.map_image:
            self.draw_map()
            
        # Draw sidebar background
        pygame.draw.rect(self.screen, (60, 60, 60), self.sidebar_area)
        pygame.draw.rect(self.screen, (100, 100, 100), self.sidebar_area, 2)
        
        # Draw toolbar background
        toolbar_rect = pygame.Rect(0, 0, 1200, self.toolbar_height)
        pygame.draw.rect(self.screen, (70, 70, 70), toolbar_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), toolbar_rect, 2)
        
        # Draw UI elements
        self.gui_manager.draw_ui(self.screen)
        
        # Draw current tool indicator
        font = pygame.font.Font(None, 24)
        tool_text = font.render(f"Tool: {self.current_tool.capitalize()}", True, (255, 255, 255))
        self.screen.blit(tool_text, (10, 770))
        
        pygame.display.flip()
        
    def draw_map(self):
        """Draw the map with all its elements."""
        if not self.map_image:
            return
            
        # Calculate visible area
        visible_rect = pygame.Rect(
            self.camera_x,
            self.camera_y,
            self.map_area.width / self.zoom_level,
            self.map_area.height / self.zoom_level
        )
        
        # Clip to image bounds
        image_rect = self.map_image.get_rect()
        visible_rect = visible_rect.clip(image_rect)
        
        if visible_rect.width <= 0 or visible_rect.height <= 0:
            return
            
        # Get the portion of the image to draw
        map_portion = self.map_image.subsurface(visible_rect)
        
        # Scale the portion
        scaled_size = (
            int(visible_rect.width * self.zoom_level),
            int(visible_rect.height * self.zoom_level)
        )
        
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_portion = pygame.transform.scale(map_portion, scaled_size)
            
            # Calculate position to draw
            draw_x = self.map_area.left
            draw_y = self.map_area.top
            
            # Adjust for partial visibility
            if self.camera_x < 0:
                draw_x -= self.camera_x * self.zoom_level
            if self.camera_y < 0:
                draw_y -= self.camera_y * self.zoom_level
                
            self.screen.blit(scaled_portion, (draw_x, draw_y))
            
            # Draw grid
            if self.grid_visible:
                self.draw_grid()
                
            # Draw walls and doors
            self.draw_walls_and_doors()
            
            # Draw locations
            self.draw_locations()
            
    def draw_grid(self):
        """Draw the grid overlay."""
        if not self.grid_visible or self.grid_size <= 0:
            return
            
        grid_size_scaled = self.grid_size * self.zoom_level
        
        if grid_size_scaled < 2:  # Don't draw if too small
            return
            
        # Calculate grid starting positions
        start_x = self.map_area.left - (self.camera_x * self.zoom_level) % grid_size_scaled
        start_y = self.map_area.top - (self.camera_y * self.zoom_level) % grid_size_scaled
        
        # Draw vertical lines
        x = start_x
        while x < self.map_area.right:
            if x >= self.map_area.left:
                pygame.draw.line(
                    self.screen, 
                    self.grid_color, 
                    (x, self.map_area.top), 
                    (x, self.map_area.bottom), 
                    1
                )
            x += grid_size_scaled
            
        # Draw horizontal lines
        y = start_y
        while y < self.map_area.bottom:
            if y >= self.map_area.top:
                pygame.draw.line(
                    self.screen, 
                    self.grid_color, 
                    (self.map_area.left, y), 
                    (self.map_area.right, y), 
                    1
                )
            y += grid_size_scaled
            
    def draw_walls_and_doors(self):
        """Draw walls and doors on the map."""
        if not self.map_image:
            return
            
        grid_size_scaled = self.grid_size * self.zoom_level
        
        # Draw walls (red squares)
        for wall_x, wall_y in self.walls:
            screen_x = self.map_area.left + (wall_x * self.grid_size - self.camera_x) * self.zoom_level
            screen_y = self.map_area.top + (wall_y * self.grid_size - self.camera_y) * self.zoom_level
            
            if (self.map_area.left <= screen_x < self.map_area.right and 
                self.map_area.top <= screen_y < self.map_area.bottom):
                
                wall_rect = pygame.Rect(screen_x, screen_y, grid_size_scaled, grid_size_scaled)
                pygame.draw.rect(self.screen, (255, 0, 0, 128), wall_rect)
                pygame.draw.rect(self.screen, (200, 0, 0), wall_rect, 2)
                
        # Draw doors (blue squares)
        for door_x, door_y in self.doors:
            screen_x = self.map_area.left + (door_x * self.grid_size - self.camera_x) * self.zoom_level
            screen_y = self.map_area.top + (door_y * self.grid_size - self.camera_y) * self.zoom_level
            
            if (self.map_area.left <= screen_x < self.map_area.right and 
                self.map_area.top <= screen_y < self.map_area.bottom):
                
                door_rect = pygame.Rect(screen_x, screen_y, grid_size_scaled, grid_size_scaled)
                pygame.draw.rect(self.screen, (0, 0, 255, 128), door_rect)
                pygame.draw.rect(self.screen, (0, 0, 200), door_rect, 2)
                
    def draw_locations(self):
        """Draw location markers on the map."""
        if not self.map_image:
            return
            
        font = pygame.font.Font(None, 20)
        
        for location in self.locations:
            screen_x = self.map_area.left + (location['x'] - self.camera_x) * self.zoom_level
            screen_y = self.map_area.top + (location['y'] - self.camera_y) * self.zoom_level
            
            if (self.map_area.left <= screen_x < self.map_area.right and 
                self.map_area.top <= screen_y < self.map_area.bottom):
                
                # Draw location marker (green circle)
                pygame.draw.circle(self.screen, (0, 255, 0), (int(screen_x), int(screen_y)), 8)
                pygame.draw.circle(self.screen, (0, 200, 0), (int(screen_x), int(screen_y)), 8, 2)
                
                # Draw location name
                text_surface = font.render(location['name'], True, (255, 255, 255))
                text_rect = text_surface.get_rect()
                text_rect.center = (screen_x, screen_y - 15)
                
                # Draw text background
                bg_rect = text_rect.inflate(4, 2)
                pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect)
                
                self.screen.blit(text_surface, text_rect)
                
    def run(self):
        """Main editor loop."""
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0
            
            self.handle_events()
            self.gui_manager.update(time_delta)
            self.draw()
            
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'db'):
            self.db.close()
        pygame.quit()


if __name__ == "__main__":
    editor = StandaloneMapEditor()
    editor.run()
