"""
D* (Dynamic A*) Pathfinding Algorithm
Handles dynamic environments with changing obstacles
"""

import heapq
import math
import time
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .grid_map import LibraryGridMap, CellType

class NodeState(Enum):
    NEW = 0      # Not yet processed
    OPEN = 1     # In the priority queue
    CLOSED = 2   # Already processed

@dataclass
class DStarNode:
    """Node for D* pathfinding"""
    x: int
    y: int
    tag: NodeState = NodeState.NEW
    h: float = 0.0           # Cost-to-goal estimate
    k: float = 0.0           # Key value for priority
    parent: Optional['DStarNode'] = None
    cost: float = float('inf')  # Actual cost from goal
    
    def __lt__(self, other):
        """For priority queue comparison"""
        return self.k < other.k

class DStarPathfinder:
    def __init__(self, grid_map: LibraryGridMap):
        """
        Initialize D* pathfinder for dynamic environments
        
        Args:
            grid_map: LibraryGridMap instance for navigation
        """
        self.grid_map = grid_map
        self.goal_x = None
        self.goal_y = None
        
        # D* specific data structures
        self.nodes: Dict[Tuple[int, int], DStarNode] = {}
        self.open_list = []  # Priority queue
        self.last_path = []
        
        # Environment change tracking
        self.cost_changes = []  # Track cost changes for replanning
        self.last_grid_state = None
        
        # Statistics
        self.replan_count = 0
        self.last_search_stats = {}
        
        print("✅ D* Pathfinder initialized for dynamic environments")
    
    def set_goal(self, goal_x: int, goal_y: int):
        """
        Set goal position and initialize D* data structures
        
        Args:
            goal_x, goal_y: Goal coordinates in grid space
        """
        if not self.grid_map.is_valid_position(goal_x, goal_y):
            print(f"❌ Invalid goal position: ({goal_x}, {goal_y})")
            return False
        
        self.goal_x = goal_x
        self.goal_y = goal_y
        
        # Reset all data structures
        self.nodes.clear()
        self.open_list.clear()
        self.cost_changes.clear()
        self.replan_count = 0
        
        # Initialize goal node
        goal_node = self._get_or_create_node(goal_x, goal_y)
        goal_node.cost = 0.0
        goal_node.h = 0.0
        goal_node.tag = NodeState.OPEN
        goal_node.k = 0.0
        
        heapq.heappush(self.open_list, goal_node)
        
        # Store initial grid state for change detection
        self.last_grid_state = self.grid_map.grid.copy()
        
        print(f"✅ Goal set to ({goal_x}, {goal_y})")
        return True
    
    def find_path(self, start_x: int, start_y: int, timeout: float = 10.0) -> Optional[List[Tuple[int, int]]]:
        """
        Find path using D* algorithm
        
        Args:
            start_x, start_y: Starting coordinates
            timeout: Maximum search time
            
        Returns:
            Path as list of (x, y) coordinates, or None if no path
        """
        if self.goal_x is None or self.goal_y is None:
            print("❌ Goal not set. Call set_goal() first.")
            return None
        
        if not self.grid_map.is_valid_position(start_x, start_y):
            print(f"❌ Invalid start position: ({start_x}, {start_y})")
            return None
        
        start_time = time.time()
        
        # Check for environment changes and replan if necessary
        if self._detect_environment_changes():
            self._handle_environment_changes()
        
        # Process open list until start node is optimal
        start_node = self._get_or_create_node(start_x, start_y)
        
        while self.open_list and (time.time() - start_time) < timeout:
            if self._process_state() == -1:
                break
            
            # Check if start node is optimally processed
            if start_node.tag == NodeState.CLOSED and start_node.cost < float('inf'):
                break
        
        # Reconstruct path
        if start_node.cost < float('inf'):
            path = self._extract_path(start_x, start_y)
            self.last_path = path
            
            # Store statistics
            self.last_search_stats = {
                'path_length': len(path) if path else 0,
                'path_cost': start_node.cost,
                'search_time': time.time() - start_time,
                'replan_count': self.replan_count,
                'success': True
            }
            
            return path
        else:
            # No path found
            self.last_search_stats = {
                'path_length': 0,
                'path_cost': float('inf'),
                'search_time': time.time() - start_time,
                'replan_count': self.replan_count,
                'success': False
            }
            
            return None
    
    def _process_state(self) -> int:
        """
        Process one state from the open list
        
        Returns:
            -1 if open list is empty, k_old otherwise
        """
        if not self.open_list:
            return -1
        
        # Get node with minimum k value
        current = heapq.heappop(self.open_list)
        current.tag = NodeState.CLOSED
        
        k_old = current.k
        
        if k_old < current.h:
            # RAISE state: cost increased
            neighbors = self._get_neighbors(current.x, current.y)
            
            for neighbor in neighbors:
                if neighbor.h <= k_old and current.h > neighbor.h + self._get_arc_cost(neighbor, current):
                    current.parent = neighbor
                    current.h = neighbor.h + self._get_arc_cost(neighbor, current)
        
        elif k_old == current.h:
            # LOWER state: cost decreased or optimal
            neighbors = self._get_neighbors(current.x, current.y)
            
            for neighbor in neighbors:
                arc_cost = self._get_arc_cost(current, neighbor)
                
                if neighbor.tag == NodeState.NEW or \
                   (neighbor.parent == current and neighbor.h != current.h + arc_cost) or \
                   (neighbor.parent != current and neighbor.h > current.h + arc_cost):
                    
                    neighbor.parent = current
                    self._insert_node(neighbor, current.h + arc_cost)
        
        else:
            # k_old > current.h: RAISE state
            neighbors = self._get_neighbors(current.x, current.y)
            
            for neighbor in neighbors:
                arc_cost = self._get_arc_cost(current, neighbor)
                
                if neighbor.tag == NodeState.NEW or \
                   (neighbor.parent == current and neighbor.h != current.h + arc_cost):
                    
                    neighbor.parent = current
                    self._insert_node(neighbor, current.h + arc_cost)
                else:
                    if neighbor.parent != current and neighbor.h > current.h + arc_cost:
                        self._insert_node(current, current.h)
                    else:
                        if neighbor.parent != current and current.h > neighbor.h + self._get_arc_cost(neighbor, current) and \
                           neighbor.tag == NodeState.CLOSED and neighbor.h > k_old:
                            self._insert_node(neighbor, neighbor.h)
        
        return k_old
    
    def _get_neighbors(self, x: int, y: int) -> List['DStarNode']:
        """Get neighboring nodes"""
        neighbor_coords = self.grid_map.get_neighbors(x, y, include_diagonal=True)
        neighbors = []
        
        for nx, ny in neighbor_coords:
            neighbor_node = self._get_or_create_node(nx, ny)
            neighbors.append(neighbor_node)
        
        return neighbors
    
    def _get_arc_cost(self, from_node: 'DStarNode', to_node: 'DStarNode') -> float:
        """Calculate cost of moving between two nodes"""
        # Check if destination is valid
        if not self.grid_map.is_valid_position(to_node.x, to_node.y):
            return float('inf')
        
        # Base movement cost (Euclidean distance)
        dx = abs(to_node.x - from_node.x)
        dy = abs(to_node.y - from_node.y)
        
        if dx == 1 and dy == 1:
            base_cost = math.sqrt(2)  # Diagonal
        else:
            base_cost = 1.0  # Orthogonal
        
        # Add traversal cost from grid
        traversal_cost = self.grid_map.get_cost(to_node.x, to_node.y)
        
        return base_cost * traversal_cost
    
    def _get_or_create_node(self, x: int, y: int) -> 'DStarNode':
        """Get existing node or create new one"""
        key = (x, y)
        if key not in self.nodes:
            self.nodes[key] = DStarNode(x, y)
        return self.nodes[key]
    
    def _insert_node(self, node: 'DStarNode', h_new: float):
        """Insert node into open list with new h value"""
        if node.tag == NodeState.NEW:
            node.k = h_new
        elif node.tag == NodeState.OPEN:
            node.k = min(node.k, h_new)
        elif node.tag == NodeState.CLOSED:
            node.k = min(node.h, h_new)
        
        node.h = h_new
        node.tag = NodeState.OPEN
        
        heapq.heappush(self.open_list, node)
    
    def _extract_path(self, start_x: int, start_y: int) -> List[Tuple[int, int]]:
        """Extract path from start to goal"""
        path = []
        current = self._get_or_create_node(start_x, start_y)
        
        visited = set()
        while current is not None:
            if (current.x, current.y) in visited:
                print("⚠️ Cycle detected in path extraction")
                break
            
            visited.add((current.x, current.y))
            path.append((current.x, current.y))
            
            if current.x == self.goal_x and current.y == self.goal_y:
                break
            
            current = current.parent
        
        return path
    
    def _detect_environment_changes(self) -> bool:
        """Detect if the environment has changed since last planning"""
        if self.last_grid_state is None:
            return False
        
        # Compare current grid with stored state
        current_grid = self.grid_map.grid
        changes_detected = not np.array_equal(current_grid, self.last_grid_state)
        
        if changes_detected:
            # Find specific changes
            diff_mask = current_grid != self.last_grid_state
            changed_positions = np.where(diff_mask)
            
            self.cost_changes = []
            for i in range(len(changed_positions[0])):
                y, x = changed_positions[0][i], changed_positions[1][i]
                old_cost = self.grid_map.get_cost(x, y) if self.last_grid_state[y, x] != CellType.OBSTACLE.value else float('inf')
                new_cost = self.grid_map.get_cost(x, y)
                
                if old_cost != new_cost:
                    self.cost_changes.append((x, y, old_cost, new_cost))
            
            print(f"🔄 Environment changes detected: {len(self.cost_changes)} cost changes")
            
        return changes_detected
    
    def _handle_environment_changes(self):
        """Handle detected environment changes by updating affected nodes"""
        self.replan_count += 1
        
        # Process each cost change
        for x, y, old_cost, new_cost in self.cost_changes:
            node = self._get_or_create_node(x, y)
            
            # If cost increased, we may need to propagate changes
            if new_cost > old_cost:
                neighbors = self._get_neighbors(x, y)
                
                for neighbor in neighbors:
                    if neighbor.parent == node:
                        # This neighbor's parent has increased cost
                        self._insert_node(neighbor, neighbor.h)
            
            # If cost decreased, we may have found better paths
            elif new_cost < old_cost:
                if node.tag == NodeState.CLOSED:
                    self._insert_node(node, node.h)
        
        # Update stored grid state
        self.last_grid_state = self.grid_map.grid.copy()
    
    def replan_if_needed(self, current_x: int, current_y: int) -> Optional[List[Tuple[int, int]]]:
        """
        Check if replanning is needed and replan if so
        
        Args:
            current_x, current_y: Current robot position
            
        Returns:
            Updated path if replanning occurred, None if no replanning needed
        """
        if self._detect_environment_changes():
            print("🔄 Replanning due to environment changes...")
            return self.find_path(current_x, current_y)
        
        return None
    
    def get_next_waypoint(self, current_x: int, current_y: int) -> Optional[Tuple[int, int]]:
        """
        Get next waypoint in the planned path
        
        Args:
            current_x, current_y: Current position
            
        Returns:
            Next waypoint coordinates or None if at goal
        """
        if not self.last_path:
            return None
        
        # Find current position in path
        current_pos = (current_x, current_y)
        
        try:
            current_index = self.last_path.index(current_pos)
            if current_index < len(self.last_path) - 1:
                return self.last_path[current_index + 1]
        except ValueError:
            # Current position not in path - might need replanning
            print("⚠️ Current position not in planned path")
        
        return None
    
    def get_search_statistics(self) -> Dict:
        """Get statistics from the last search"""
        return self.last_search_stats.copy()


# Test D* pathfinder
if __name__ == "__main__":
    print("Testing D* Pathfinder...")
    
    # Create test environment
    from .grid_map import LibraryGridMap
    
    grid_map = LibraryGridMap(width=640, height=480, resolution=25.0)
    
    # Add initial obstacles
    initial_detections = [
        {
            'class_name': 'table',
            'confidence': 0.9,
            'bbox': {'x1': 300, 'y1': 200, 'x2': 450, 'y2': 280, 
                    'center_x': 375, 'center_y': 240}
        }
    ]
    
    grid_map.update_from_detections(initial_detections)
    
    # Initialize D* pathfinder
    pathfinder = DStarPathfinder(grid_map)
    
    # Set goal
    goal_pos = (20, 15)
    pathfinder.set_goal(goal_pos[0], goal_pos[1])
    
    # Find initial path
    start_pos = (2, 2)
    print(f"\n🚀 Finding initial path from {start_pos} to {goal_pos}...")
    
    path = pathfinder.find_path(start_pos[0], start_pos[1])
    
    if path:
        print(f"✅ Initial path found!")
        print(f"   Path length: {len(path)} waypoints")
        
        stats = pathfinder.get_search_statistics()
        print(f"   Path cost: {stats['path_cost']:.2f}")
        print(f"   Search time: {stats['search_time']:.3f}s")
        
        # Simulate environment change
        print(f"\n🔄 Simulating environment change...")
        new_detections = initial_detections + [
            {
                'class_name': 'office-chair',
                'confidence': 0.85,
                'bbox': {'x1': 200, 'y1': 300, 'x2': 300, 'y2': 400,
                        'center_x': 250, 'center_y': 350}
            }
        ]
        
        grid_map.update_from_detections(new_detections)
        
        # Test replanning
        current_pos = path[len(path)//2] if len(path) > 2 else start_pos
        new_path = pathfinder.replan_if_needed(current_pos[0], current_pos[1])
        
        if new_path:
            print(f"✅ Replanning successful!")
            print(f"   New path length: {len(new_path)} waypoints")
            
            new_stats = pathfinder.get_search_statistics()
            print(f"   Replan count: {new_stats['replan_count']}")
            print(f"   New path cost: {new_stats['path_cost']:.2f}")
        else:
            print("ℹ️ No replanning needed")
        
    else:
        print("❌ No path found")
    
    print("\n✅ D* pathfinder test completed!")