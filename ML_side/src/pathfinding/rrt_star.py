"""
RRT* (Rapidly-exploring Random Tree Star) Pathfinding Algorithm
Sampling-based pathfinding for complex environments
"""

import random
import math
import time
from typing import List, Tuple, Optional, Dict
import numpy as np

from .grid_map import LibraryGridMap, CellType

class RRTNode:
    """Node for RRT* tree"""
    def __init__(self, x: float, y: float, parent: Optional['RRTNode'] = None):
        self.x = x
        self.y = y
        self.parent = parent
        self.children: List['RRTNode'] = []
        self.cost = 0.0  # Cost from root
        
    def distance_to(self, other: 'RRTNode') -> float:
        """Calculate Euclidean distance to another node"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class RRTStarPathfinder:
    def __init__(self, grid_map: LibraryGridMap):
        """
        Initialize RRT* pathfinder
        
        Args:
            grid_map: LibraryGridMap instance for navigation
        """
        self.grid_map = grid_map
        
        # RRT* parameters
        self.max_iterations = 5000
        self.step_size = 3.0  # Maximum distance for new nodes
        self.goal_tolerance = 2.0  # Distance to goal considered success
        self.rewire_radius = 6.0  # Radius for rewiring optimization
        self.goal_bias = 0.1  # Probability of sampling goal directly
        
        # Tree structure
        self.tree: List[RRTNode] = []
        self.start_node: Optional[RRTNode] = None
        self.goal_node: Optional[RRTNode] = None
        
        # Search statistics
        self.last_search_stats = {}
        
        print("✅ RRT* Pathfinder initialized for sampling-based planning")
    
    def find_path(self, start_x: int, start_y: int, goal_x: int, goal_y: int,
                  timeout: float = 30.0, optimize_iterations: int = 1000) -> Optional[List[Tuple[float, float]]]:
        """
        Find path using RRT* algorithm
        
        Args:
            start_x, start_y: Starting coordinates (grid)
            goal_x, goal_y: Goal coordinates (grid)
            timeout: Maximum search time
            optimize_iterations: Additional iterations for optimization after first solution
            
        Returns:
            Path as list of (x, y) coordinates, or None if no path found
        """
        start_time = time.time()
        
        # Convert to continuous coordinates
        start_pixel_x, start_pixel_y = self.grid_map.grid_to_pixel(start_x, start_y)
        goal_pixel_x, goal_pixel_y = self.grid_map.grid_to_pixel(goal_x, goal_y)
        
        # Validate positions
        if not self.grid_map.is_valid_position(start_x, start_y):
            print(f"❌ Invalid start position: ({start_x}, {start_y})")
            return None
        
        if not self.grid_map.is_valid_position(goal_x, goal_y):
            print(f"❌ Invalid goal position: ({goal_x}, {goal_y})")
            return None
        
        # Initialize tree
        self.tree = []
        self.start_node = RRTNode(start_pixel_x, start_pixel_y)
        self.tree.append(self.start_node)
        self.goal_node = None
        
        goal_found = False
        best_goal_node = None
        best_cost = float('inf')
        iterations = 0
        
        # Main RRT* loop
        while iterations < self.max_iterations and (time.time() - start_time) < timeout:
            # Sample random point or goal (with bias)
            if random.random() < self.goal_bias:
                sample_x, sample_y = goal_pixel_x, goal_pixel_y
            else:
                sample_x = random.uniform(0, self.grid_map.image_width)
                sample_y = random.uniform(0, self.grid_map.image_height)
            
            sample_point = RRTNode(sample_x, sample_y)
            
            # Find nearest node in tree
            nearest_node = self._find_nearest_node(sample_point)
            
            # Extend tree towards sample
            new_node = self._extend_towards(nearest_node, sample_point)
            
            if new_node is None:
                iterations += 1
                continue
            
            # Check if path to new node is collision-free
            if not self._is_path_collision_free(nearest_node, new_node):
                iterations += 1
                continue
            
            # Find near nodes for rewiring
            near_nodes = self._find_near_nodes(new_node)
            
            # Choose parent with minimum cost
            min_cost_parent = nearest_node
            min_cost = nearest_node.cost + nearest_node.distance_to(new_node) * self._get_path_cost_multiplier(nearest_node, new_node)
            
            for near_node in near_nodes:
                if self._is_path_collision_free(near_node, new_node):
                    cost = near_node.cost + near_node.distance_to(new_node) * self._get_path_cost_multiplier(near_node, new_node)
                    if cost < min_cost:
                        min_cost_parent = near_node
                        min_cost = cost
            
            # Set parent and cost
            new_node.parent = min_cost_parent
            new_node.cost = min_cost
            min_cost_parent.children.append(new_node)
            self.tree.append(new_node)
            
            # Rewire tree for optimization
            self._rewire_tree(new_node, near_nodes)
            
            # Check if goal is reached
            goal_distance = math.sqrt((new_node.x - goal_pixel_x)**2 + (new_node.y - goal_pixel_y)**2)
            
            if goal_distance <= self.goal_tolerance:
                if not goal_found:
                    goal_found = True
                    print(f"🎯 Goal reached at iteration {iterations}")
                
                # Update best goal if this is better
                if new_node.cost < best_cost:
                    best_goal_node = new_node
                    best_cost = new_node.cost
            
            iterations += 1
            
            # Continue optimizing for a while after first solution
            if goal_found and iterations > self.max_iterations - optimize_iterations:
                if iterations % 100 == 0:
                    print(f"🔧 Optimizing... iteration {iterations}, best cost: {best_cost:.2f}")
        
        # Extract best path
        if best_goal_node is not None:
            path = self._extract_path(best_goal_node)
            
            # Convert back to grid coordinates
            grid_path = []
            for px, py in path:
                gx, gy = self.grid_map.pixel_to_grid(px, py)
                grid_path.append((float(gx), float(gy)))
            
            # Store statistics
            self.last_search_stats = {
                'iterations': iterations,
                'path_length': len(path),
                'path_cost': best_goal_node.cost,
                'search_time': time.time() - start_time,
                'tree_size': len(self.tree),
                'goal_found_iteration': iterations - optimize_iterations if goal_found else -1,
                'success': True
            }
            
            return grid_path
        else:
            # No path found
            self.last_search_stats = {
                'iterations': iterations,
                'path_length': 0,
                'path_cost': float('inf'),
                'search_time': time.time() - start_time,
                'tree_size': len(self.tree),
                'goal_found_iteration': -1,
                'success': False
            }
            
            return None
    
    def _find_nearest_node(self, sample: RRTNode) -> RRTNode:
        """Find nearest node in the tree to sample point"""
        min_distance = float('inf')
        nearest_node = self.start_node
        
        for node in self.tree:
            distance = node.distance_to(sample)
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        
        return nearest_node
    
    def _extend_towards(self, from_node: RRTNode, to_node: RRTNode) -> Optional[RRTNode]:
        """Extend tree from from_node towards to_node by step_size"""
        distance = from_node.distance_to(to_node)
        
        if distance <= self.step_size:
            return RRTNode(to_node.x, to_node.y)
        else:
            # Create new node at step_size distance
            ratio = self.step_size / distance
            new_x = from_node.x + ratio * (to_node.x - from_node.x)
            new_y = from_node.y + ratio * (to_node.y - from_node.y)
            return RRTNode(new_x, new_y)
    
    def _is_path_collision_free(self, from_node: RRTNode, to_node: RRTNode) -> bool:
        """Check if path between two nodes is collision-free"""
        # Sample points along the path
        distance = from_node.distance_to(to_node)
        num_samples = int(distance / 2.0) + 1  # Sample every 2 pixels
        
        for i in range(num_samples + 1):
            ratio = i / max(1, num_samples)
            check_x = from_node.x + ratio * (to_node.x - from_node.x)
            check_y = from_node.y + ratio * (to_node.y - from_node.y)
            
            # Convert to grid coordinates
            grid_x, grid_y = self.grid_map.pixel_to_grid(check_x, check_y)
            
            # Check if position is valid
            if not self.grid_map.is_valid_position(grid_x, grid_y):
                return False
            
            # Check if cost is too high (treat as obstacle)
            cost = self.grid_map.get_cost(grid_x, grid_y)
            if cost > 10.0:  # Threshold for "collision"
                return False
        
        return True
    
    def _find_near_nodes(self, node: RRTNode) -> List[RRTNode]:
        """Find nodes within rewire radius"""
        near_nodes = []
        
        for tree_node in self.tree:
            if tree_node != node and tree_node.distance_to(node) <= self.rewire_radius:
                near_nodes.append(tree_node)
        
        return near_nodes
    
    def _rewire_tree(self, new_node: RRTNode, near_nodes: List[RRTNode]):
        """Rewire tree to optimize paths through new_node"""
        for near_node in near_nodes:
            # Skip if this would create a cycle
            if self._would_create_cycle(new_node, near_node):
                continue
            
            # Calculate potential new cost
            potential_cost = new_node.cost + new_node.distance_to(near_node) * self._get_path_cost_multiplier(new_node, near_node)
            
            # Rewire if path through new_node is better and collision-free
            if potential_cost < near_node.cost and self._is_path_collision_free(new_node, near_node):
                # Remove from old parent
                if near_node.parent:
                    near_node.parent.children.remove(near_node)
                
                # Set new parent
                near_node.parent = new_node
                new_node.children.append(near_node)
                
                # Update costs recursively
                self._update_costs_recursive(near_node, potential_cost)
    
    def _would_create_cycle(self, new_parent: RRTNode, child: RRTNode) -> bool:
        """Check if making new_parent the parent of child would create a cycle"""
        current = new_parent.parent
        while current is not None:
            if current == child:
                return True
            current = current.parent
        return False
    
    def _update_costs_recursive(self, node: RRTNode, new_cost: float):
        """Update costs recursively down the tree"""
        old_cost = node.cost
        node.cost = new_cost
        cost_difference = new_cost - old_cost
        
        # Avoid infinite recursion with invalid costs
        if not np.isfinite(cost_difference):
            return
        
        # Update all children
        for child in node.children:
            self._update_costs_recursive(child, child.cost + cost_difference)
    
    def _get_path_cost_multiplier(self, from_node: RRTNode, to_node: RRTNode) -> float:
        """Get cost multiplier for path segment based on environment"""
        # Sample a few points along the path and get average cost
        num_samples = 5
        total_cost = 0.0
        
        for i in range(num_samples):
            ratio = i / (num_samples - 1) if num_samples > 1 else 0
            sample_x = from_node.x + ratio * (to_node.x - from_node.x)
            sample_y = from_node.y + ratio * (to_node.y - from_node.y)
            
            grid_x, grid_y = self.grid_map.pixel_to_grid(sample_x, sample_y)
            
            if self.grid_map.is_valid_position(grid_x, grid_y):
                total_cost += self.grid_map.get_cost(grid_x, grid_y)
            else:
                return float('inf')  # Invalid path
        
        return total_cost / num_samples
    
    def _extract_path(self, goal_node: RRTNode) -> List[Tuple[float, float]]:
        """Extract path from goal node back to start"""
        path = []
        current = goal_node
        
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        
        path.reverse()
        return path
    
    def get_tree_visualization_data(self) -> Dict:
        """Get tree data for visualization"""
        edges = []
        nodes = []
        
        for node in self.tree:
            nodes.append((node.x, node.y))
            if node.parent:
                edges.append(((node.parent.x, node.parent.y), (node.x, node.y)))
        
        return {
            'nodes': nodes,
            'edges': edges,
            'start': (self.start_node.x, self.start_node.y) if self.start_node else None
        }
    
    def get_search_statistics(self) -> Dict:
        """Get statistics from the last search"""
        return self.last_search_stats.copy()
    
    def set_parameters(self, max_iterations: int = None, step_size: float = None,
                      goal_tolerance: float = None, rewire_radius: float = None,
                      goal_bias: float = None):
        """
        Set RRT* parameters
        
        Args:
            max_iterations: Maximum number of iterations
            step_size: Maximum distance for extending tree
            goal_tolerance: Distance to goal considered success
            rewire_radius: Radius for rewiring optimization
            goal_bias: Probability of sampling goal directly
        """
        if max_iterations is not None:
            self.max_iterations = max_iterations
        if step_size is not None:
            self.step_size = step_size
        if goal_tolerance is not None:
            self.goal_tolerance = goal_tolerance
        if rewire_radius is not None:
            self.rewire_radius = rewire_radius
        if goal_bias is not None:
            self.goal_bias = goal_bias
        
        print(f"✅ RRT* parameters updated")


# Test RRT* pathfinder
if __name__ == "__main__":
    print("Testing RRT* Pathfinder...")
    
    # Create test environment
    from .grid_map import LibraryGridMap
    
    grid_map = LibraryGridMap(width=640, height=480, resolution=20.0)
    
    # Add test obstacles to create interesting environment
    test_detections = [
        {
            'class_name': 'table',
            'confidence': 0.9,
            'bbox': {'x1': 200, 'y1': 150, 'x2': 350, 'y2': 230, 
                    'center_x': 275, 'center_y': 190}
        },
        {
            'class_name': 'office-chair',
            'confidence': 0.85,
            'bbox': {'x1': 400, 'y1': 300, 'x2': 500, 'y2': 400,
                    'center_x': 450, 'center_y': 350}
        },
        {
            'class_name': 'whiteboard',
            'confidence': 0.95,
            'bbox': {'x1': 150, 'y1': 350, 'x2': 300, 'y2': 380,
                    'center_x': 225, 'center_y': 365}
        }
    ]
    
    grid_map.update_from_detections(test_detections)
    
    # Initialize RRT* pathfinder
    pathfinder = RRTStarPathfinder(grid_map)
    
    # Set parameters for faster testing
    pathfinder.set_parameters(
        max_iterations=2000,
        step_size=4.0,
        goal_tolerance=3.0,
        rewire_radius=8.0,
        goal_bias=0.15
    )
    
    # Test pathfinding
    start_pos = (2, 2)
    goal_pos = (25, 20)
    
    print(f"\n🚀 Finding path from {start_pos} to {goal_pos} using RRT*...")
    
    path = pathfinder.find_path(start_pos[0], start_pos[1], goal_pos[0], goal_pos[1], timeout=15.0)
    
    if path:
        print(f"✅ Path found!")
        print(f"   Path length: {len(path)} waypoints")
        
        # Get statistics
        stats = pathfinder.get_search_statistics()
        print(f"   Iterations: {stats['iterations']}")
        print(f"   Tree size: {stats['tree_size']}")
        print(f"   Path cost: {stats['path_cost']:.2f}")
        print(f"   Search time: {stats['search_time']:.3f}s")
        print(f"   Goal found at iteration: {stats['goal_found_iteration']}")
        
        # Convert path to grid coordinates for visualization
        grid_path = [(int(x), int(y)) for x, y in path]
        grid_map.mark_path(grid_path)
        grid_map.save_map_image("rrt_star_test_result.png", scale_factor=8)
        print(f"   Visualization saved to rrt_star_test_result.png")
        
    else:
        print("❌ No path found")
        stats = pathfinder.get_search_statistics()
        print(f"   Iterations: {stats['iterations']}")
        print(f"   Tree size: {stats['tree_size']}")
        print(f"   Search time: {stats['search_time']:.3f}s")
    
    print("\n✅ RRT* pathfinder test completed!")