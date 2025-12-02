"""
A* Pathfinding Algorithm for Library Navigation
Optimal pathfinding with heuristic search
"""

import heapq
import math
import time
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
import numpy as np

from .grid_map import LibraryGridMap, CellType

@dataclass
class AStarNode:
    """Node for A* pathfinding"""
    x: int
    y: int
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0.0           # Heuristic cost to goal
    f_cost: float = field(init=False)  # Total cost
    parent: Optional['AStarNode'] = None
    
    def __post_init__(self):
        self.f_cost = self.g_cost + self.h_cost
    
    def __lt__(self, other):
        """For priority queue comparison"""
        if self.f_cost != other.f_cost:
            return self.f_cost < other.f_cost
        return self.h_cost < other.h_cost  # Tie-breaker: prefer lower h_cost

class AStarPathfinder:
    def __init__(self, grid_map: LibraryGridMap):
        """
        Initialize A* pathfinder
        
        Args:
            grid_map: LibraryGridMap instance for navigation
        """
        self.grid_map = grid_map
        self.heuristic_weight = 1.0  # Weight for heuristic (1.0 = optimal A*)
        self.diagonal_cost = math.sqrt(2)  # Cost for diagonal movement
        
        # Statistics
        self.last_search_stats = {}
        
        print("✅ A* Pathfinder initialized")
    
    def find_path(self, start_x: int, start_y: int, goal_x: int, goal_y: int, 
                  timeout: float = 5.0, smooth_path: bool = True) -> Optional[List[Tuple[int, int]]]:
        """
        Find optimal path using A* algorithm
        
        Args:
            start_x, start_y: Starting grid coordinates
            goal_x, goal_y: Goal grid coordinates
            timeout: Maximum search time in seconds
            smooth_path: Whether to apply path smoothing
            
        Returns:
            List of (x, y) coordinates representing the path, or None if no path found
        """
        start_time = time.time()
        
        # Validate start and goal positions
        if not self.grid_map.is_valid_position(start_x, start_y):
            print(f"❌ Invalid start position: ({start_x}, {start_y})")
            return None
        
        if not self.grid_map.is_valid_position(goal_x, goal_y):
            print(f"❌ Invalid goal position: ({goal_x}, {goal_y})")
            return None
        
        # Initialize data structures
        open_set = []  # Priority queue of nodes to explore
        closed_set: Set[Tuple[int, int]] = set()  # Already explored nodes
        node_map: Dict[Tuple[int, int], AStarNode] = {}  # All created nodes
        
        # Create start node
        start_node = AStarNode(
            x=start_x, 
            y=start_y, 
            g_cost=0.0,
            h_cost=self._calculate_heuristic(start_x, start_y, goal_x, goal_y)
        )
        
        heapq.heappush(open_set, start_node)
        node_map[(start_x, start_y)] = start_node
        
        nodes_explored = 0
        
        # Main A* search loop
        while open_set and (time.time() - start_time) < timeout:
            current_node = heapq.heappop(open_set)
            nodes_explored += 1
            
            # Check if we reached the goal
            if current_node.x == goal_x and current_node.y == goal_y:
                path = self._reconstruct_path(current_node)
                
                # Apply path smoothing if requested
                if smooth_path:
                    path = self._smooth_path(path)
                
                # Store search statistics
                self.last_search_stats = {
                    'nodes_explored': nodes_explored,
                    'path_length': len(path),
                    'path_cost': current_node.g_cost,
                    'search_time': time.time() - start_time,
                    'success': True
                }
                
                return path
            
            # Mark current node as explored
            closed_set.add((current_node.x, current_node.y))
            
            # Explore neighbors
            neighbors = self.grid_map.get_neighbors(current_node.x, current_node.y, include_diagonal=True)
            
            for neighbor_x, neighbor_y in neighbors:
                # Skip if already explored
                if (neighbor_x, neighbor_y) in closed_set:
                    continue
                
                # Calculate movement cost
                movement_cost = self._calculate_movement_cost(
                    current_node.x, current_node.y, neighbor_x, neighbor_y
                )
                
                tentative_g_cost = current_node.g_cost + movement_cost
                
                # Get or create neighbor node
                neighbor_key = (neighbor_x, neighbor_y)
                if neighbor_key not in node_map:
                    neighbor_node = AStarNode(
                        x=neighbor_x,
                        y=neighbor_y,
                        h_cost=self._calculate_heuristic(neighbor_x, neighbor_y, goal_x, goal_y)
                    )
                    node_map[neighbor_key] = neighbor_node
                else:
                    neighbor_node = node_map[neighbor_key]
                
                # Update node if we found a better path
                if tentative_g_cost < neighbor_node.g_cost:
                    neighbor_node.parent = current_node
                    neighbor_node.g_cost = tentative_g_cost
                    neighbor_node.f_cost = neighbor_node.g_cost + neighbor_node.h_cost
                    
                    # Add to open set if not already there
                    if neighbor_node not in open_set:
                        heapq.heappush(open_set, neighbor_node)
        
        # No path found
        self.last_search_stats = {
            'nodes_explored': nodes_explored,
            'path_length': 0,
            'path_cost': float('inf'),
            'search_time': time.time() - start_time,
            'success': False,
            'timeout': (time.time() - start_time) >= timeout
        }
        
        return None
    
    def _calculate_heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate heuristic distance between two points"""
        # Use Euclidean distance as heuristic
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        
        # Euclidean distance
        euclidean = math.sqrt(dx*dx + dy*dy)
        
        # Apply heuristic weight
        return euclidean * self.heuristic_weight
    
    def _calculate_movement_cost(self, from_x: int, from_y: int, to_x: int, to_y: int) -> float:
        """Calculate cost of moving between two adjacent cells"""
        # Base movement cost (diagonal vs straight)
        dx = abs(to_x - from_x)
        dy = abs(to_y - from_y)
        
        if dx == 1 and dy == 1:
            base_cost = self.diagonal_cost
        else:
            base_cost = 1.0
        
        # Add traversal cost from grid map
        traversal_cost = self.grid_map.get_cost(to_x, to_y)
        
        return base_cost * traversal_cost
    
    def _reconstruct_path(self, goal_node: AStarNode) -> List[Tuple[int, int]]:
        """Reconstruct path from goal node back to start"""
        path = []
        current = goal_node
        
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        
        path.reverse()
        return path
    
    def _smooth_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Apply path smoothing to reduce unnecessary waypoints"""
        if len(path) < 3:
            return path
        
        smoothed_path = [path[0]]  # Always keep start
        
        i = 0
        while i < len(path) - 1:
            # Try to find the furthest point we can reach directly
            furthest_reachable = i + 1
            
            for j in range(i + 2, len(path)):
                if self._is_line_of_sight(path[i], path[j]):
                    furthest_reachable = j
                else:
                    break
            
            # Add the furthest reachable point
            if furthest_reachable > i + 1:
                smoothed_path.append(path[furthest_reachable])
            else:
                smoothed_path.append(path[i + 1])
            
            i = furthest_reachable
        
        # Ensure goal is included
        if smoothed_path[-1] != path[-1]:
            smoothed_path.append(path[-1])
        
        return smoothed_path
    
    def _is_line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Check if there's a clear line of sight between two points"""
        x0, y0 = start
        x1, y1 = end
        
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        x, y = x0, y0
        
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        
        error = dx - dy
        
        while True:
            # Check if current cell is blocked
            if not self.grid_map.is_valid_position(x, y):
                return False
            
            # Check if we reached the end
            if x == x1 and y == y1:
                break
            
            # Bresenham step
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        
        return True
    
    def find_path_with_waypoints(self, waypoints: List[Tuple[int, int]], 
                                timeout_per_segment: float = 5.0) -> Optional[List[Tuple[int, int]]]:
        """
        Find path through multiple waypoints
        
        Args:
            waypoints: List of (x, y) waypoints to visit in order
            timeout_per_segment: Timeout for each path segment
            
        Returns:
            Complete path through all waypoints, or None if any segment fails
        """
        if len(waypoints) < 2:
            return waypoints
        
        complete_path = []
        total_stats = {
            'segments': 0,
            'total_nodes_explored': 0,
            'total_search_time': 0.0,
            'success': True
        }
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            goal = waypoints[i + 1]
            
            segment_path = self.find_path(
                start[0], start[1], goal[0], goal[1],
                timeout=timeout_per_segment,
                smooth_path=True
            )
            
            if segment_path is None:
                print(f"❌ Failed to find path from {start} to {goal}")
                total_stats['success'] = False
                return None
            
            # Add segment to complete path (avoid duplicating waypoints)
            if complete_path:
                segment_path = segment_path[1:]  # Skip first point (duplicate)
            
            complete_path.extend(segment_path)
            
            # Accumulate statistics
            total_stats['segments'] += 1
            total_stats['total_nodes_explored'] += self.last_search_stats['nodes_explored']
            total_stats['total_search_time'] += self.last_search_stats['search_time']
        
        self.last_search_stats = total_stats
        return complete_path
    
    def get_search_statistics(self) -> Dict:
        """Get statistics from the last search"""
        return self.last_search_stats.copy()
    
    def set_heuristic_weight(self, weight: float):
        """
        Set heuristic weight for A* search
        
        Args:
            weight: Heuristic weight (1.0 = optimal, >1.0 = faster but suboptimal)
        """
        self.heuristic_weight = max(0.1, weight)
        print(f"✅ Heuristic weight set to {self.heuristic_weight}")


# Test A* pathfinder
if __name__ == "__main__":
    print("Testing A* Pathfinder...")
    
    # Create test environment
    from .grid_map import LibraryGridMap
    
    grid_map = LibraryGridMap(width=640, height=480, resolution=20.0)
    
    # Add test obstacles
    test_detections = [
        {
            'class_name': 'table',
            'confidence': 0.9,
            'bbox': {'x1': 200, 'y1': 200, 'x2': 400, 'y2': 280, 
                    'center_x': 300, 'center_y': 240}
        },
        {
            'class_name': 'office-chair',
            'confidence': 0.85,
            'bbox': {'x1': 150, 'y1': 350, 'x2': 250, 'y2': 450,
                    'center_x': 200, 'center_y': 400}
        }
    ]
    
    grid_map.update_from_detections(test_detections)
    
    # Initialize pathfinder
    pathfinder = AStarPathfinder(grid_map)
    
    # Test pathfinding
    start_pos = (2, 2)
    goal_pos = (30, 20)
    
    print(f"\n🚀 Finding path from {start_pos} to {goal_pos}...")
    
    path = pathfinder.find_path(start_pos[0], start_pos[1], goal_pos[0], goal_pos[1])
    
    if path:
        print(f"✅ Path found!")
        print(f"   Path length: {len(path)} waypoints")
        
        # Get statistics
        stats = pathfinder.get_search_statistics()
        print(f"   Nodes explored: {stats['nodes_explored']}")
        print(f"   Search time: {stats['search_time']:.3f}s")
        print(f"   Path cost: {stats['path_cost']:.2f}")
        
        # Mark path on grid
        grid_map.mark_path(path)
        grid_map.save_map_image("astar_test_result.png", scale_factor=8)
        print(f"   Visualization saved to astar_test_result.png")
        
    else:
        print("❌ No path found")
        stats = pathfinder.get_search_statistics()
        print(f"   Nodes explored: {stats['nodes_explored']}")
        print(f"   Search time: {stats['search_time']:.3f}s")
    
    print("\n✅ A* pathfinder test completed!")