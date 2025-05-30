import pygame
import pygame_gui
import os
import sys
import traceback

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from map_veiwer import EnhancedMapViewer # Corrected typo from map_veiwer.py to map_viewer.py if that's the case
import config # Import the config module # Corrected typo from map_veiwer.py to map_viewer.py if that's the case

# Configuration constants (since they are not in config.py for map area)
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
TOOLBAR_HEIGHT = 50
SIDEBAR_WIDTH = 0 # No sidebar in the viewer for now, map takes full width

MAP_AREA_LEFT = 0
MAP_AREA_TOP = TOOLBAR_HEIGHT
MAP_AREA_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH
MAP_AREA_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT

class StandaloneMapViewerApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RolePlay Sim - Map Viewer")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.gui_manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), 'theme.json') # Assuming a theme.json might exist or be created
        self.db = Database()

        # Create an object that can hold the config attributes for EnhancedMapViewer
        class AppRef:
            def __init__(self, gui_manager, db):
                self.gui_manager = gui_manager
                self.enhanced_db = db # EnhancedMapViewer expects app_ref.enhanced_db
                # Add other attributes if EnhancedMapViewer expects them from app_ref

        app_ref_instance = AppRef(self.gui_manager, self.db)
        self.map_viewer = EnhancedMapViewer(app_ref_instance)

        # Pass the map_area_rect to the map_viewer, as it's defined locally here
        self.map_viewer.map_area_rect = pygame.Rect(
            MAP_AREA_LEFT,
            MAP_AREA_TOP,
            MAP_AREA_WIDTH,
            MAP_AREA_HEIGHT
        )

        # Default player token
        self.player_token = {
            'id': 'player_1',
            'name': 'Player',
            'x': 5,  # Grid position
            'y': 5,  # Grid position
            'type': 'player',
            'target_x': 5,  # Target position for animation
            'target_y': 5,  # Target position for animation
            'is_moving': False,  # Whether token is currently moving
            'move_speed': 0.1,  # Speed of movement (grid cells per frame)
            'selected': True  # Whether token is selected
        }
        
        # Add a second token (ally character)
        self.ally_token = {
            'id': 'ally_1',
            'name': 'Ally',
            'x': 7,  # Grid position
            'y': 7,  # Grid position
            'type': 'ally',
            'target_x': 7,  # Target position for animation
            'target_y': 7,  # Target position for animation
            'is_moving': False,  # Whether token is currently moving
            'move_speed': 0.1,  # Speed of movement (grid cells per frame)
            'selected': False  # Whether token is selected
        }
        
        self.tokens = [self.player_token, self.ally_token]
        self.selected_token_id = 'player_1'

        # Movement state
        self.keys_pressed = set()
        self.movement_points = 5  # Default movement points
        self.movement_used = 0    # Movement points used in current turn
        
        # Mouse drag state
        self.dragging_token = False
        self.dragged_token = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        # Wall data
        self.walls = set()  # Set of (x, y) tuples for wall locations
        self.visible_area = set()  # Set of (x, y) tuples for visible grid cells
        self.visibility_radius = 10  # Default visibility radius
        
        # Display options
        self.show_grid = True  # Whether to show the grid or not
        self.center_tokens = True  # Whether to center tokens in grid squares

        self.create_ui()

    def create_ui(self):
        # Create a UI button to reset movement
        self.reset_movement_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((850, 80), (100, 30)),
            text='Reset Move',
            manager=self.gui_manager,
            tool_tip_text='Reset movement points used'
        )
        self.load_map_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 10), (150, 30)),
            text='Load Map',
            manager=self.gui_manager,
            object_id='#load_map_button'
        )

        # Add instructions label
        self.instructions_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((170, 10), (600, 30)),
            text='Drag player token with mouse | Walls block movement & vision | ESC to exit',
            manager=self.gui_manager
        )
        
        # Add visibility radius label and slider
        self.visibility_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((600, 10), (100, 30)),
            text=f'Vision: {self.visibility_radius}',
            manager=self.gui_manager
        )
        
        self.visibility_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((700, 10), (140, 30)),
            start_value=self.visibility_radius,
            value_range=(3, 20),
            manager=self.gui_manager
        )
        
        # Add movement points label and slider
        self.movement_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((850, 10), (100, 30)),
            text=f'Move: {self.movement_points}',
            manager=self.gui_manager
        )
        
        self.movement_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((950, 10), (100, 30)),
            start_value=self.movement_points,
            value_range=(1, 10),
            manager=self.gui_manager
        )
        
        # Add grid toggle checkbox
        self.grid_checkbox = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((1060, 10), (100, 30)),
            text='Grid: On',
            manager=self.gui_manager,
            tool_tip_text='Toggle grid visibility'
        )
        
        # Add token center checkbox
        self.center_checkbox = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((1060, 45), (100, 30)),
            text='Center: On',
            manager=self.gui_manager,
            tool_tip_text='Toggle token centering in grid squares'
        )
        
        # Movement used counter
        self.movement_used_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((850, 45), (190, 30)),
            text=f'Used: {self.movement_used}/{self.movement_points}',
            manager=self.gui_manager
        )
        
        # Initialize dialog state
        self.dialog_active = False
        self.map_options = []

    def show_load_map_dialog(self):
        try:
            print("DEBUG: Getting maps from database")
            maps = self.db.get_all_maps()
            print(f"DEBUG: Found {len(maps)} maps: {maps}")
            
            if not maps:
                self.show_message("No Maps", "No maps found in the database.")
                return
                
            # Create map dictionary
            self.map_options = []
            self.map_ids = {}
            
            for map_entry in maps:
                map_id, name = map_entry[0], map_entry[1]
                display_name = f"{name} (ID: {map_id})"
                self.map_options.append(display_name)
                self.map_ids[display_name] = map_id
                print(f"DEBUG: Added map to list: {display_name}")
            
            # Create map selection dropdown
            self.map_dropdown = pygame_gui.elements.UIDropDownMenu(
                options_list=self.map_options,
                starting_option=self.map_options[0],
                relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 - 100), (300, 30)),
                manager=self.gui_manager
            )
            
            # Create load button
            self.load_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2 - 50), (100, 30)),
                text='Load Map',
                manager=self.gui_manager
            )
            
            # Set dialog state
            self.dialog_active = True
            
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            print(traceback.format_exc())
            self.show_message("Error", f"Failed to load map list: {e}")
    
    def handle_dialog_events(self, event):
        """Handle events for the map selection dialog"""
        if not self.dialog_active:
            return False
            
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.load_button:
                self.load_selected_map()
                return True
                
        return False
    
    def load_selected_map(self):
        """Load the map selected in the dropdown"""
        try:
            selected_map = self.map_dropdown.selected_option
            print(f"DEBUG: Selected map: {selected_map} (type: {type(selected_map)})")
            
            # Handle case where selected_map is a tuple
            if isinstance(selected_map, tuple):
                selected_map = selected_map[0]
            
            # Fallback solution if the key isn't found
            if selected_map not in self.map_ids:
                print(f"DEBUG: Map not found in dictionary. Keys: {list(self.map_ids.keys())}")
                # Extract ID from the display name
                if "(ID:" in selected_map:
                    map_id = int(selected_map.split("(ID: ")[1].split(")")[0])
                    print(f"DEBUG: Extracted map_id from string: {map_id}")
                else:
                    raise ValueError(f"Could not determine map ID from {selected_map}")
            else:
                map_id = self.map_ids[selected_map]
            
            print(f"DEBUG: Loading map with ID: {map_id}")
            
            # Make sure map_id is an integer
            if isinstance(map_id, tuple):
                map_id = map_id[0]  # Extract from tuple if needed
            map_id = int(map_id)  # Ensure it's an integer
            
            map_data = self.db.get_map_by_id(map_id)
            print(f"DEBUG: Map data: {map_data}")
            
            if map_data:
                print(f"DEBUG: Loading map data into viewer")
                try:
                    self.map_viewer.load_map_data(map_data)
                    print(f"DEBUG: Map loaded successfully")
                    
                    # Load walls for the map
                    self.load_walls(map_id)
                    
                    # Calculate initial visibility
                    self.update_visibility()
                    
                    self.show_message("Success", f"Map '{selected_map.split(' (ID:')[0]}' loaded successfully!")
                except Exception as e:
                    print(f"DEBUG ERROR: Error loading map data: {e}")
                    print(traceback.format_exc())
                    self.show_message("Error", f"Error loading map: {e}")
            else:
                self.show_message("Error", f"Could not load map data for ID: {map_id}")
                
            # Clean up dialog elements
            self.map_dropdown.kill()
            self.load_button.kill()
            self.dialog_active = False
            
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            print(traceback.format_exc())
            self.show_message("Error", f"Failed to load map: {e}")
            
    def show_message(self, title, message):
        """Show a message box using pygame_gui"""
        print(f"MESSAGE: {title} - {message}")
        
        # Create message box
        self.message_box = pygame_gui.windows.UIMessageWindow(
            rect=pygame.Rect((SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 100), (400, 200)),
            html_message=f"<b>{title}</b><br>{message}",
            manager=self.gui_manager
        )

    def handle_token_movement(self):
        """Handle keyboard input for token movement and animate tokens"""
        if not self.selected_token_id or not self.map_viewer.current_map_id:
            return
            
        # Find the selected token
        token = None
        for t in self.tokens:
            if t['id'] == self.selected_token_id:
                token = t
                break
                
        if not token:
            return
            
        # Handle keyboard input
        keys = pygame.key.get_pressed()
        
        # Calculate movement
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx = -1
        elif keys[pygame.K_RIGHT]:
            dx = 1
        if keys[pygame.K_UP]:
            dy = -1
        elif keys[pygame.K_DOWN]:
            dy = 1
            
        # Apply movement with bounds checking
        if dx != 0 or dy != 0:
            new_x = token['x'] + dx
            new_y = token['y'] + dy
            
            # Set target position instead of moving immediately
            self.set_token_target(token, new_x, new_y)
        
        # Animate all tokens that are moving
        self.animate_tokens()
    
    def load_walls(self, map_id):
        """Load wall data for the map"""
        try:
            wall_data = self.db.get_map_walls(map_id)
            self.walls = set(wall_data)  # Convert list of tuples to set for faster lookup
            print(f"DEBUG: Loaded {len(self.walls)} walls for map {map_id}")
            
            # If no walls found, create some test walls
            if not self.walls:
                print("DEBUG: No walls found, creating test walls")
                # Create a simple test room with walls
                for x in range(3, 15):
                    # Top and bottom walls
                    self.walls.add((x, 3))
                    self.walls.add((x, 10))
                
                for y in range(3, 11):
                    # Left and right walls
                    self.walls.add((3, y))
                    self.walls.add((14, y))
                
                # Add a wall in the middle
                for y in range(3, 8):
                    self.walls.add((8, y))
                
                print(f"DEBUG: Created {len(self.walls)} test walls")
                
        except Exception as e:
            print(f"DEBUG ERROR: Error loading walls: {e}")
            self.walls = set()
    
    def update_visibility(self):
        """Update visibility based on player position and walls"""
        if not self.map_viewer.current_map_id:
            self.visible_area = set()
            return
        
        # Find the player token (always use player token for visibility, even if ally is selected)
        player_token = None
        for token in self.tokens:
            if token['id'] == 'player_1':
                player_token = token
                break
                
        if not player_token:
            self.visible_area = set()
            return
        
        # Clear visibility
        self.visible_area = set()
        
        # Get player position
        player_x, player_y = player_token['x'], player_token['y']
        print(f"DEBUG: Updating visibility for player at ({player_x}, {player_y})")
        
        # Use the current visibility radius setting
        visibility_range = self.visibility_radius
        
        # Always see your own cell
        self.visible_area.add((player_x, player_y))
        
        # Start with all cells in range being potentially visible
        for dx in range(-visibility_range, visibility_range + 1):
            for dy in range(-visibility_range, visibility_range + 1):
                x, y = player_x + dx, player_y + dy
                
                # Check if cell is in bounds
                if self.map_viewer.grid_size > 0:
                    grid_width = self.map_viewer.map_width // self.map_viewer.grid_size
                    grid_height = self.map_viewer.map_height // self.map_viewer.grid_size
                    if not (0 <= x < grid_width and 0 <= y < grid_height):
                        continue
                
                # Check if cell is within visibility radius
                distance = (dx*dx + dy*dy) ** 0.5
                if distance > visibility_range:
                    continue
                
                # Use line of sight algorithm to check if this cell is visible
                if self.has_line_of_sight(player_x, player_y, x, y):
                    self.visible_area.add((x, y))
        
        print(f"DEBUG: Updated visibility, {len(self.visible_area)} cells visible")
    
    def has_line_of_sight(self, x1, y1, x2, y2):
        """Check if there's a clear line of sight between two points"""
        # Always see your own cell
        if (x1, y1) == (x2, y2):
            return True
        
        # Use Bresenham's line algorithm to check for walls
        points = self.get_line(x1, y1, x2, y2)
        
        # Check all points except the start and end
        for i, (x, y) in enumerate(points):
            # Skip the starting point
            if i == 0:
                continue
                
            # If we hit a wall before reaching the end, there's no line of sight
            if (x, y) in self.walls:
                return False
                
            # If we reached the destination, there is line of sight
            if (x, y) == (x2, y2):
                return True
        
        return True
    
    def get_line(self, x1, y1, x2, y2):
        """Get all points on a line between (x1,y1) and (x2,y2) using Bresenham's algorithm"""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
                
        return points
    
    def is_cell_visible(self, x, y):
        """Check if a cell is visible"""
        return (x, y) in self.visible_area
    
    def move_token_to_grid_position(self, token, grid_x, grid_y):
        """Move a token to a specific grid position with bounds checking"""
        # Basic bounds checking (adjust based on map size)
        # Add safety check for grid_size
        if self.map_viewer.grid_size > 0:
            grid_width = self.map_viewer.map_width // self.map_viewer.grid_size
            grid_height = self.map_viewer.map_height // self.map_viewer.grid_size
            
            if 0 <= grid_x < grid_width and 0 <= grid_y < grid_height:
                # Check if destination is a wall
                if (grid_x, grid_y) in self.walls:
                    print(f"DEBUG: Cannot move to wall at ({grid_x}, {grid_y})")
                    return False
                    
                # Move token
                old_x, old_y = token['x'], token['y']
                token['x'] = grid_x
                token['y'] = grid_y
                print(f"DEBUG: Moved token to ({grid_x}, {grid_y})")
                
                # If this is the player token, update visibility
                if token['id'] == 'player_1':
                    self.update_visibility()
                    
                return True
        else:
            # If no grid size set, allow free movement within reasonable bounds
            if 0 <= grid_x < 100 and 0 <= grid_y < 100:
                token['x'] = grid_x
                token['y'] = grid_y
                return True
                
        return False
    
    def is_point_over_token(self, screen_x, screen_y, token):
        """Check if a screen position is over a token"""
        if not self.map_viewer.map_surface or not self.map_viewer.grid_size:
            return False
            
        # Calculate token's screen position
        if self.center_tokens:
            # Center of grid cell
            token_map_x = (token['x'] + 0.5) * self.map_viewer.grid_size
            token_map_y = (token['y'] + 0.5) * self.map_viewer.grid_size
        else:
            # Corner of grid cell (original behavior)
            token_map_x = token['x'] * self.map_viewer.grid_size
            token_map_y = token['y'] * self.map_viewer.grid_size
            
        token_screen_pos = self.map_viewer.map_to_screen_coords((token_map_x, token_map_y))
        
        # Token radius in screen coordinates
        token_size = int(self.map_viewer.grid_size * self.map_viewer.zoom_level * 0.8)
        token_radius = token_size // 2
        
        # Check if point is within circle
        dx = screen_x - token_screen_pos[0]
        dy = screen_y - token_screen_pos[1]
        distance = (dx*dx + dy*dy) ** 0.5
        
        return distance <= token_radius
    
    def get_token_at_position(self, screen_x, screen_y):
        """Get token at the given screen position"""
        for token in self.tokens:
            if self.is_point_over_token(screen_x, screen_y, token):
                return token
        return None
    
    def screen_to_grid_position(self, screen_x, screen_y):
        """Convert screen coordinates to grid position"""
        if not self.map_viewer.map_surface or not self.map_viewer.grid_size:
            return (0, 0)
            
        # Convert screen position to map coordinates
        map_x, map_y = self.map_viewer.screen_to_map_coords((screen_x, screen_y))
        
        # Convert map coordinates to grid position
        grid_x = int(map_x / self.map_viewer.grid_size)
        grid_y = int(map_y / self.map_viewer.grid_size)
        
        return (grid_x, grid_y)

    def run(self):
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                # ESC key to exit application
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Handle map dialog events if active
                if self.dialog_active:
                    if self.handle_dialog_events(event):
                        continue
                
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.load_map_button:
                        self.show_load_map_dialog()
                    elif event.ui_element == self.reset_movement_button:
                        # Reset movement points used
                        self.movement_used = 0
                        self.movement_used_label.set_text(f'Used: {self.movement_used}/{self.movement_points}')
                    elif event.ui_element == self.grid_checkbox:
                        # Toggle grid visibility
                        self.show_grid = not self.show_grid
                        self.grid_checkbox.set_text('Grid: On' if self.show_grid else 'Grid: Off')
                    elif event.ui_element == self.center_checkbox:
                        # Toggle token centering
                        self.center_tokens = not self.center_tokens
                        self.center_checkbox.set_text('Center: On' if self.center_tokens else 'Center: Off')
                
                # Handle slider movement
                if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                    if event.ui_element == self.visibility_slider:
                        # Update visibility radius
                        new_radius = int(event.value)
                        if new_radius != self.visibility_radius:
                            self.visibility_radius = new_radius
                            self.visibility_label.set_text(f'Vision: {self.visibility_radius}')
                            # Update visibility with new radius
                            self.update_visibility()
                    elif event.ui_element == self.movement_slider:
                        # Update movement points
                        new_movement = int(event.value)
                        if new_movement != self.movement_points:
                            self.movement_points = new_movement
                            self.movement_label.set_text(f'Move: {self.movement_points}')
                            self.movement_used_label.set_text(f'Used: {self.movement_used}/{self.movement_points}')
                            # Reset movement used if we reduce max below current used
                            if self.movement_used > self.movement_points:
                                self.movement_used = 0
                                self.movement_used_label.set_text(f'Used: {self.movement_used}/{self.movement_points}')
                
                # These button handlers are now in the section above
                
                # Handle keyboard events for smoother movement
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                        self.keys_pressed.add(event.key)
                        
                if event.type == pygame.KEYUP:
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                        self.keys_pressed.discard(event.key)
                
                # Handle mouse events for token dragging
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button
                    if not self.dialog_active and self.map_viewer.current_map_id:
                        mouse_pos = pygame.mouse.get_pos()
                        token = self.get_token_at_position(mouse_pos[0], mouse_pos[1])
                        if token:
                            # Select the token
                            self.select_token(token)
                            self.dragging_token = True
                            self.dragged_token = token
                            self.selected_token_id = token['id']
                            # Calculate drag offset (accounting for centering)
                            if self.center_tokens:
                                # Center in grid cell
                                token_map_x = (token['x'] + 0.5) * self.map_viewer.grid_size
                                token_map_y = (token['y'] + 0.5) * self.map_viewer.grid_size
                            else:
                                # Corner of grid cell
                                token_map_x = token['x'] * self.map_viewer.grid_size
                                token_map_y = token['y'] * self.map_viewer.grid_size
                                
                            token_screen_pos = self.map_viewer.map_to_screen_coords((token_map_x, token_map_y))
                            self.drag_offset_x = token_screen_pos[0] - mouse_pos[0]
                            self.drag_offset_y = token_screen_pos[1] - mouse_pos[1]
                            print(f"DEBUG: Started dragging token at ({token['x']}, {token['y']})")
                
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left mouse button
                    # Handle regular map clicks (not drag ends)
                    if not self.dragging_token and not self.dialog_active and self.map_viewer.current_map_id:
                        if self.map_viewer.map_area_rect.collidepoint(event.pos):
                            # Get the selected token
                            selected_token = None
                            for token in self.tokens:
                                if token['id'] == self.selected_token_id:
                                    selected_token = token
                                    break
                            
                            if selected_token:
                                # Convert click position to grid coordinates
                                grid_x, grid_y = self.screen_to_grid_position(event.pos[0], event.pos[1])
                                
                                # Calculate distance
                                old_x, old_y = selected_token['x'], selected_token['y']
                                distance = abs(grid_x - old_x) + abs(grid_y - old_y)  # Manhattan distance
                                
                                # Check if we have enough movement points
                                remaining_movement = self.movement_points - self.movement_used
                                
                                if distance <= remaining_movement:
                                    # Check validity of move
                                    if self.set_token_target(selected_token, grid_x, grid_y):
                                        # Update movement points used
                                        self.movement_used += distance
                                        self.movement_used_label.set_text(f'Used: {self.movement_used}/{self.movement_points}')
                                        print(f"DEBUG: Click-moving token to ({grid_x}, {grid_y})")
                                else:
                                    print(f"DEBUG: Not enough movement points for click move. Need {distance}, have {remaining_movement}")
                    
                    # Handle drag ends
                    elif self.dragging_token and self.dragged_token:
                        # Get final position and convert to grid coordinates
                        mouse_pos = pygame.mouse.get_pos()
                        adjusted_pos = (mouse_pos[0] + self.drag_offset_x, mouse_pos[1] + self.drag_offset_y)
                        grid_x, grid_y = self.screen_to_grid_position(adjusted_pos[0], adjusted_pos[1])
                        
                                # Calculate distance from original position
                        old_x, old_y = self.dragged_token['x'], self.dragged_token['y']
                        distance = abs(grid_x - old_x) + abs(grid_y - old_y)  # Manhattan distance
                        
                        # Check if we have enough movement points
                        remaining_movement = self.movement_points - self.movement_used
                        
                        if distance <= remaining_movement:
                            # Set target position for smooth animation
                            if self.set_token_target(self.dragged_token, grid_x, grid_y):
                                # Update movement points used
                                self.movement_used += distance
                                self.movement_used_label.set_text(f'Used: {self.movement_used}/{self.movement_points}')
                        else:
                            # Not enough movement points
                            print(f"DEBUG: Not enough movement points. Need {distance}, have {remaining_movement}")
                        
                        # Reset drag state
                        self.dragging_token = False
                        self.dragged_token = None
                        print("DEBUG: Finished dragging token")
                
                if event.type == pygame.MOUSEMOTION:
                    # Update token position during drag
                    if self.dragging_token and self.dragged_token and self.map_viewer.current_map_id:
                        # Show visual preview of where token will be placed
                        mouse_pos = pygame.mouse.get_pos()
                        adjusted_pos = (mouse_pos[0] + self.drag_offset_x, mouse_pos[1] + self.drag_offset_y)
                        
                        # Calculate grid position
                        new_grid_x, new_grid_y = self.screen_to_grid_position(adjusted_pos[0], adjusted_pos[1])
                        
                        # Calculate distance from original position
                        old_x, old_y = self.dragged_token['x'], self.dragged_token['y']
                        distance = abs(new_grid_x - old_x) + abs(new_grid_y - old_y)  # Manhattan distance
                        
                        # Get movement allowance
                        remaining_movement = self.movement_points - self.movement_used
                        
                        # Preview color based on whether move is valid
                        is_valid = (distance <= remaining_movement) and (new_grid_x, new_grid_y) not in self.walls
                        color = (0, 255, 0, 128) if is_valid else (255, 0, 0, 128)  # Green if valid, red if not
                        
                        # Draw preview at new position
                        if self.center_tokens:
                            # Center of grid cell
                            map_x = (new_grid_x + 0.5) * self.map_viewer.grid_size
                            map_y = (new_grid_y + 0.5) * self.map_viewer.grid_size
                        else:
                            # Corner of grid cell (original behavior)
                            map_x = new_grid_x * self.map_viewer.grid_size
                            map_y = new_grid_y * self.map_viewer.grid_size
                        
                        screen_pos = self.map_viewer.map_to_screen_coords((map_x, map_y))
                        token_size = int(self.map_viewer.grid_size * self.map_viewer.zoom_level * 0.8)
                        
                        # Create ghost token surface
                        ghost_surface = pygame.Surface((token_size, token_size), pygame.SRCALPHA)
                        pygame.draw.circle(ghost_surface, color, (token_size//2, token_size//2), token_size//2)
                        
                        # Draw ghost token
                        ghost_rect = ghost_surface.get_rect(center=screen_pos)
                        self.screen.blit(ghost_surface, ghost_rect)
                
                self.gui_manager.process_events(event)
                if not self.dialog_active:  # Only handle map viewer events when dialog is not active
                    self.map_viewer.handle_event(event) # Pass events to EnhancedMapViewer

            # Handle continuous token movement
            self.handle_token_movement()

            self.gui_manager.update(time_delta)
            self.map_viewer.update(time_delta) # Update EnhancedMapViewer

            self.screen.fill((config.UI_PANEL_COLOR if hasattr(config, 'UI_PANEL_COLOR') else (50,50,50))) # Background color
            # Pass display options to map viewer
            self.map_viewer.show_grid = self.show_grid
            self.map_viewer.center_tokens = self.center_tokens
            
            # Handle token animation - returns True if any animation occurred
            animation_occurred = self.animate_tokens()
            
            # Draw map viewer elements first
            self.map_viewer.draw(
                self.screen, 
                tokens=self.tokens,
                notes=None, 
                locations=self.map_viewer.location_icons if hasattr(self.map_viewer, 'location_icons') else [], 
                selected_token_id=self.selected_token_id
            ) # Draw EnhancedMapViewer
            
            # Then draw fog of war on top
            if self.map_viewer.current_map_id:
                # Always draw fog of war if animation is happening or normally
                self.draw_fog_of_war()
            self.gui_manager.draw_ui(self.screen)

            pygame.display.flip()

        self.db.close()
        pygame.quit()

    def draw_fog_of_war(self):
        """Draw a simple fog of war overlay"""
        if not self.map_viewer.current_map_id or not self.map_viewer.grid_size:
            return
            
        # Create a full-screen fog surface
        fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fog.fill((0, 0, 0, 220))  # Very dark fog
            
        # Create a mask to remove fog from visible areas
        for x, y in self.visible_area:
            # Calculate grid cell position in map coordinates
            map_x = x * self.map_viewer.grid_size
            map_y = y * self.map_viewer.grid_size
            
            # Convert to screen coordinates
            screen_pos = self.map_viewer.map_to_screen_coords((map_x, map_y))
            
            # Calculate cell size in screen coordinates
            cell_size = int(self.map_viewer.grid_size * self.map_viewer.zoom_level)
            
            # Create rectangle for this cell
            rect = pygame.Rect(
                screen_pos[0] - cell_size//2,
                screen_pos[1] - cell_size//2,
                cell_size,
                cell_size
            )
            
            # Clear this area from fog - no yellow borders
            pygame.draw.rect(fog, (0, 0, 0, 0), rect)
        
        # Draw the fog overlay directly on screen
        self.screen.blit(fog, (0, 0))
        
        # Print debug info
        print(f"DEBUG: Drew fog of war with {len(self.visible_area)} visible cells")

    def select_token(self, token):
        """Select a token and deselect all others"""
        # Only change selection if not already selected
        if self.selected_token_id != token['id']:
            # Deselect all tokens
            for t in self.tokens:
                t['selected'] = False
                
            # Select the new token
            token['selected'] = True
            self.selected_token_id = token['id']
            
            # If this is the player token, update visibility
            # Otherwise use the player token's position for visibility
            if token['id'] == 'player_1':
                self.update_visibility()
            
            print(f"DEBUG: Selected token {token['id']}")
    
    def set_token_target(self, token, target_x, target_y):
        """Set a target position for a token to move to"""
        # Check if the target position is valid
        if not self.is_valid_move(token, target_x, target_y):
            return False
            
        # Set the target position
        token['target_x'] = target_x
        token['target_y'] = target_y
        token['is_moving'] = True
        print(f"DEBUG: Set target position ({target_x}, {target_y}) for token {token['id']}")
        return True
    
    def is_valid_move(self, token, target_x, target_y):
        """Check if a move is valid"""
        # Check map bounds
        if self.map_viewer.grid_size <= 0:
            return False
            
        grid_width = self.map_viewer.map_width // self.map_viewer.grid_size
        grid_height = self.map_viewer.map_height // self.map_viewer.grid_size
        
        if not (0 <= target_x < grid_width and 0 <= target_y < grid_height):
            return False
            
        # Check for walls
        if (target_x, target_y) in self.walls:
            return False
            
        return True
    
    def animate_tokens(self):
        """Animate all tokens that are moving"""
        animation_occurred = False
        
        for token in self.tokens:
            if token['is_moving']:
                animation_occurred = True
                # Calculate direction vector
                dx = token['target_x'] - token['x']
                dy = token['target_y'] - token['y']
                
                # Calculate distance
                distance = (dx*dx + dy*dy) ** 0.5
                
                if distance < token['move_speed']:
                    # We've reached the target
                    token['x'] = token['target_x']
                    token['y'] = token['target_y']
                    token['is_moving'] = False
                    
                    # Update visibility if this is the player
                    if token['id'] == 'player_1':
                        self.update_visibility()
                        
                    print(f"DEBUG: Token {token['id']} reached target position ({token['x']}, {token['y']})")
                else:
                    # Move towards target
                    if distance > 0:
                        move_x = dx * token['move_speed'] / distance
                        move_y = dy * token['move_speed'] / distance
                        
                        token['x'] += move_x
                        token['y'] += move_y
                        
                        # Update visibility for player even during movement
                        if token['id'] == 'player_1':
                            self.update_visibility()
        
        # Return whether any token was animated - used to trigger fog of war redraw
        return animation_occurred

if __name__ == '__main__':
    # Ensure config attributes are available for EnhancedMapViewer
    # These are typically set in a main application class, but for standalone viewer,
    # we can patch them into a simple config-like object or ensure EnhancedMapViewer
    # can get them from its app_ref
    class ConfigMock:
        MAP_AREA_LEFT = MAP_AREA_LEFT
        MAP_AREA_TOP = MAP_AREA_TOP
        MAP_AREA_WIDTH = MAP_AREA_WIDTH
        MAP_AREA_HEIGHT = MAP_AREA_HEIGHT
        # Add any other config values EnhancedMapViewer might directly access from 'config'
        UI_PANEL_COLOR = (40,40,40) # Example, if map_viewer uses it directly

    # This is a bit of a hack. Ideally, EnhancedMapViewer would take all its config via __init__
    # or its app_ref would provide everything, rather than importing 'config' directly.
    # For now, we ensure the global 'config' module has the necessary attributes if map_veiwer.py imports it.
    import config as global_config_module
    global_config_module.MAP_AREA_LEFT = MAP_AREA_LEFT
    global_config_module.MAP_AREA_TOP = MAP_AREA_TOP
    global_config_module.MAP_AREA_WIDTH = MAP_AREA_WIDTH
    global_config_module.MAP_AREA_HEIGHT = MAP_AREA_HEIGHT
    if not hasattr(global_config_module, 'UI_PANEL_COLOR'): # Add if not present
        global_config_module.UI_PANEL_COLOR = (40,40,40)

    app = StandaloneMapViewerApp()
    app.run()
