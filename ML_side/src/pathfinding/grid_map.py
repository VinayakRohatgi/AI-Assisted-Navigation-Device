"""
Grid-based Map Representation for Pathfinding
Converts semantic understanding to navigation grid
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import cv2

class CellType(Enum):
    FREE = 0
    OBSTACLE = 1
    UNKNOWN = 2
    GOAL = 3
    START = 4
    PATH = 5

@dataclass
class GridCell:
    x: int
    y: int
    cost: float = 1.0
    cell_type: CellType = CellType.FREE
    confidence: float = 1.0
    semantic_info: Optional[Dict] = None

class LibraryGridMap:
    def __init__(self, width: int = 640, height: int = 480, resolution: float = 10.0):
        """
        Initialize grid map for library navigation
        
        Args:
            width: Image/camera width in pixels
            height: Image/camera height in pixels  
            resolution: Pixels per grid cell (lower = higher resolution)
        """
        self.image_width = width
        self.image_height = height
        self.resolution = resolution
        
        # Calculate grid dimensions
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        
        # Initialize grid
        self.grid = np.full((self.grid_height, self.grid_width), CellType.FREE.value, dtype=np.int8)
        self.cost_grid = np.ones((self.grid_height, self.grid_width), dtype=np.float32)
        self.confidence_grid = np.ones((self.grid_height, self.grid_width), dtype=np.float32)
        
        # Semantic information storage
        self.semantic_cells = {}  # (x, y) -> semantic info
        
        # Navigation parameters
        self.obstacle_inflation_radius = 2  # Grid cells to inflate around obstacles
        self.safety_margin = 1.5  # Additional safety factor
        
        print(f"✅ Grid map initialized: {self.grid_width}x{self.grid_height} cells")
    
    def pixel_to_grid(self, pixel_x: float, pixel_y: float) -> Tuple[int, int]:
        """Convert pixel coordinates to grid coordinates"""
        grid_x = int(pixel_x / self.resolution)
        grid_y = int(pixel_y / self.resolution)
        
        # Clamp to grid bounds
        grid_x = max(0, min(self.grid_width - 1, grid_x))
        grid_y = max(0, min(self.grid_height - 1, grid_y))
        
        return grid_x, grid_y
    
    def grid_to_pixel(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid coordinates to pixel coordinates (center of cell)"""
        pixel_x = (grid_x + 0.5) * self.resolution
        pixel_y = (grid_y + 0.5) * self.resolution
        return pixel_x, pixel_y
    
    def update_from_detections(self, detections: List[Dict], clear_previous: bool = False):
        """
        Update grid map from YOLO detections
        
        Args:
            detections: List of detection dictionaries with bbox info
            clear_previous: Whether to clear previous obstacle information
        """
        if clear_previous:
            self.grid.fill(CellType.FREE.value)
            self.cost_grid.fill(1.0)
            self.confidence_grid.fill(1.0)
        
        for detection in detections:
            self._add_detection_to_grid(detection)
        
        # Apply obstacle inflation for safety
        self._inflate_obstacles()
    
    def _add_detection_to_grid(self, detection: Dict):
        """Add single detection to grid map"""
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class_name']
        
        # Convert bbox to grid coordinates
        x1, y1 = self.pixel_to_grid(bbox['x1'], bbox['y1'])
        x2, y2 = self.pixel_to_grid(bbox['x2'], bbox['y2'])
        
        # Ensure proper ordering
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Determine obstacle type and cost
        obstacle_cost = self._get_obstacle_cost(class_name, confidence)
        is_obstacle = self._is_obstacle_class(class_name)
        
        # Fill grid cells
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                    if is_obstacle:
                        self.grid[y, x] = CellType.OBSTACLE.value
                        self.cost_grid[y, x] = obstacle_cost
                    else:
                        # Non-obstacle objects increase traversal cost but don't block
                        self.cost_grid[y, x] = max(self.cost_grid[y, x], obstacle_cost * 0.5)
                    
                    self.confidence_grid[y, x] = confidence
                    
                    # Store semantic information
                    self.semantic_cells[(x, y)] = {
                        'class_name': class_name,
                        'confidence': confidence,
                        'detection_data': detection
                    }
    
    def _is_obstacle_class(self, class_name: str) -> bool:
        """Determine if object class should be treated as obstacle"""
        # Objects that block movement
        obstacle_classes = {
            'office-chair', 'table', 'books', 'whiteboard'
        }
        
        # Objects that are landmarks but not obstacles
        non_obstacle_classes = {
            'monitor', 'tv'  # Can potentially navigate around/under
        }
        
        return class_name in obstacle_classes
    
    def _get_obstacle_cost(self, class_name: str, confidence: float) -> float:
        """Calculate traversal cost for different object types"""
        base_costs = {
            'office-chair': 10.0,  # High cost - difficult to move
            'table': 15.0,        # Very high - large obstacle
            'books': 8.0,         # Medium - might be moveable
            'whiteboard': 20.0,   # Extremely high - large, fixed
            'monitor': 3.0,       # Low - might navigate around
            'tv': 4.0            # Low-medium - larger than monitor
        }
        
        base_cost = base_costs.get(class_name, 5.0)
        
        # Scale by confidence - higher confidence = higher cost
        confidence_factor = 0.5 + (confidence * 1.5)
        
        return base_cost * confidence_factor
    
    def _inflate_obstacles(self):
        """Inflate obstacles for safety margin"""
        if self.obstacle_inflation_radius <= 0:
            return
        
        # Create kernel for inflation
        kernel_size = 2 * self.obstacle_inflation_radius + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        # Find obstacle cells
        obstacle_mask = (self.grid == CellType.OBSTACLE.value).astype(np.uint8)
        
        # Dilate obstacles
        inflated_mask = cv2.dilate(obstacle_mask, kernel, iterations=1)
        
        # Apply inflation (only to FREE cells, don't overwrite existing obstacles)
        inflation_cells = (inflated_mask == 1) & (self.grid == CellType.FREE.value)
        
        # Set inflated cells to high cost instead of full obstacle
        inflated_cost = 5.0 * self.safety_margin
        self.cost_grid[inflation_cells] = np.maximum(self.cost_grid[inflation_cells], inflated_cost)
    
    def is_valid_position(self, grid_x: int, grid_y: int) -> bool:
        """Check if grid position is valid for navigation"""
        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            return False
        
        return self.grid[grid_y, grid_x] != CellType.OBSTACLE.value
    
    def get_cost(self, grid_x: int, grid_y: int) -> float:
        """Get traversal cost for grid cell"""
        if not self.is_valid_position(grid_x, grid_y):
            return float('inf')
        
        return self.cost_grid[grid_y, grid_x]
    
    def get_neighbors(self, grid_x: int, grid_y: int, include_diagonal: bool = True) -> List[Tuple[int, int]]:
        """Get valid neighboring cells"""
        neighbors = []
        
        # 4-connected neighbors
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        # Add diagonal neighbors if requested
        if include_diagonal:
            directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
        
        for dx, dy in directions:
            new_x, new_y = grid_x + dx, grid_y + dy
            if self.is_valid_position(new_x, new_y):
                neighbors.append((new_x, new_y))
        
        return neighbors
    
    def get_semantic_info(self, grid_x: int, grid_y: int) -> Optional[Dict]:
        """Get semantic information for grid cell"""
        return self.semantic_cells.get((grid_x, grid_y))
    
    def set_goal(self, pixel_x: float, pixel_y: float):
        """Set goal position on the map"""
        grid_x, grid_y = self.pixel_to_grid(pixel_x, pixel_y)
        if self.is_valid_position(grid_x, grid_y):
            self.grid[grid_y, grid_x] = CellType.GOAL.value
            return grid_x, grid_y
        return None
    
    def set_start(self, pixel_x: float, pixel_y: float):
        """Set start position on the map"""
        grid_x, grid_y = self.pixel_to_grid(pixel_x, pixel_y)
        # Start can be set even in occupied cells (current position)
        self.grid[grid_y, grid_x] = CellType.START.value
        return grid_x, grid_y
    
    def clear_path(self):
        """Clear previous path markings"""
        self.grid[self.grid == CellType.PATH.value] = CellType.FREE.value
    
    def mark_path(self, path: List[Tuple[int, int]]):
        """Mark path on the grid"""
        self.clear_path()
        for x, y in path:
            if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                if self.grid[y, x] == CellType.FREE.value:
                    self.grid[y, x] = CellType.PATH.value
    
    def get_safe_radius_around_point(self, grid_x: int, grid_y: int, max_radius: int = 5) -> int:
        """Find largest safe radius around a point"""
        for radius in range(1, max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:  # Only check perimeter
                        check_x, check_y = grid_x + dx, grid_y + dy
                        if not self.is_valid_position(check_x, check_y):
                            return radius - 1
        return max_radius
    
    def get_visualization(self) -> np.ndarray:
        """Get visual representation of the grid map"""
        # Create color map
        vis_map = np.zeros((self.grid_height, self.grid_width, 3), dtype=np.uint8)
        
        # Color mapping
        colors = {
            CellType.FREE.value: (255, 255, 255),      # White
            CellType.OBSTACLE.value: (0, 0, 0),        # Black
            CellType.UNKNOWN.value: (128, 128, 128),   # Gray
            CellType.GOAL.value: (0, 255, 0),          # Green
            CellType.START.value: (0, 0, 255),         # Blue
            CellType.PATH.value: (255, 0, 0)           # Red
        }
        
        for cell_type, color in colors.items():
            mask = self.grid == cell_type
            vis_map[mask] = color
        
        # Overlay cost information (darker = higher cost)
        cost_overlay = np.clip(self.cost_grid * 50, 0, 255).astype(np.uint8)
        free_cells = self.grid == CellType.FREE.value
        
        # Darken free cells based on cost
        for i in range(3):
            vis_map[free_cells, i] = np.maximum(0, vis_map[free_cells, i] - cost_overlay[free_cells])
        
        return vis_map
    
    def save_map_image(self, filepath: str, scale_factor: int = 4):
        """Save grid map as image"""
        vis_map = self.get_visualization()
        
        # Scale up for better visibility
        if scale_factor > 1:
            vis_map = cv2.resize(vis_map, 
                               (self.grid_width * scale_factor, self.grid_height * scale_factor),
                               interpolation=cv2.INTER_NEAREST)
        
        cv2.imwrite(filepath, vis_map)
        print(f"✅ Grid map saved to {filepath}")


# Test the grid map
if __name__ == "__main__":
    print("Testing Library Grid Map...")
    
    # Create grid map
    grid_map = LibraryGridMap(width=640, height=480, resolution=20.0)
    
    # Test with sample detections
    sample_detections = [
        {
            'class_name': 'monitor',
            'confidence': 0.92,
            'bbox': {'x1': 200, 'y1': 150, 'x2': 400, 'y2': 300, 
                    'center_x': 300, 'center_y': 225}
        },
        {
            'class_name': 'office-chair', 
            'confidence': 0.85,
            'bbox': {'x1': 100, 'y1': 350, 'x2': 200, 'y2': 450,
                    'center_x': 150, 'center_y': 400}
        },
        {
            'class_name': 'table',
            'confidence': 0.88,
            'bbox': {'x1': 450, 'y1': 250, 'x2': 600, 'y2': 330,
                    'center_x': 525, 'center_y': 290}
        }
    ]
    
    # Update grid from detections
    grid_map.update_from_detections(sample_detections)
    
    # Set start and goal
    start_pos = grid_map.set_start(50, 50)
    goal_pos = grid_map.set_goal(590, 430)
    
    print(f"✅ Grid updated with {len(sample_detections)} detections")
    print(f"   Start position: {start_pos}")
    print(f"   Goal position: {goal_pos}")
    print(f"   Grid dimensions: {grid_map.grid_width} x {grid_map.grid_height}")
    
    # Test pathfinding readiness
    if start_pos and goal_pos:
        neighbors = grid_map.get_neighbors(start_pos[0], start_pos[1])
        print(f"   Start has {len(neighbors)} valid neighbors")
        
        goal_neighbors = grid_map.get_neighbors(goal_pos[0], goal_pos[1])
        print(f"   Goal has {len(goal_neighbors)} valid neighbors")
    
    # Save visualization
    grid_map.save_map_image("test_grid_map.png", scale_factor=8)
    
    print("\n✅ Grid map test completed!")