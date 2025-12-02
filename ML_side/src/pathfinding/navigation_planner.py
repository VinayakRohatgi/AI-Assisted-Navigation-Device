"""
Integrated Navigation Planner
Combines pathfinding algorithms with semantic mapping for optimal navigation
"""

import time
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
import numpy as np

from .grid_map import LibraryGridMap
from .astar import AStarPathfinder
from .dstar import DStarPathfinder
from .rrt_star import RRTStarPathfinder
from ..semantic_mapping.library_map_builder import LibraryMapBuilder
from ..semantic_mapping.scene_memory import SceneMemorySystem

class PathfindingAlgorithm(Enum):
    ASTAR = "astar"
    DSTAR = "dstar"
    RRT_STAR = "rrt_star"
    AUTO = "auto"  # Automatically choose best algorithm

class NavigationStrategy(Enum):
    OPTIMAL = "optimal"      # Find best path regardless of time
    FAST = "fast"           # Quick path planning
    DYNAMIC = "dynamic"     # Handle changing environments
    EXPLORATION = "exploration"  # For unknown/complex environments

@dataclass
class NavigationRequest:
    """Request for navigation planning"""
    goal_description: str  # e.g., "computer lab", "quiet study area"
    start_pixel_pos: Tuple[float, float]  # Current camera position
    algorithm: PathfindingAlgorithm = PathfindingAlgorithm.AUTO
    strategy: NavigationStrategy = NavigationStrategy.OPTIMAL
    timeout: float = 10.0
    user_preferences: Dict[str, Any] = None

@dataclass
class NavigationResult:
    """Result of navigation planning"""
    success: bool
    path: Optional[List[Tuple[int, int]]]  # Grid coordinates
    pixel_path: Optional[List[Tuple[float, float]]]  # Pixel coordinates
    algorithm_used: PathfindingAlgorithm
    planning_time: float
    path_cost: float
    confidence: float
    waypoint_descriptions: List[str]
    next_action: str
    estimated_duration: float  # Estimated traversal time
    difficulty_level: str
    semantic_guidance: Dict[str, Any]

class NavigationPlanner:
    def __init__(self, image_width: int = 640, image_height: int = 480, resolution: float = 15.0):
        """
        Initialize integrated navigation planner
        
        Args:
            image_width: Camera image width
            image_height: Camera image height
            resolution: Grid resolution (pixels per cell)
        """
        self.image_width = image_width
        self.image_height = image_height
        self.resolution = resolution
        
        # Core components
        self.grid_map = LibraryGridMap(image_width, image_height, resolution)
        self.map_builder = LibraryMapBuilder()
        self.scene_memory = SceneMemorySystem()
        
        # Pathfinding algorithms
        self.astar = AStarPathfinder(self.grid_map)
        self.dstar = DStarPathfinder(self.grid_map)
        self.rrt_star = RRTStarPathfinder(self.grid_map)
        
        # Navigation state
        self.current_goal = None
        self.active_path = None
        self.last_planning_result = None
        
        # Goal locations in library (learned from semantic mapping)
        self.known_locations = {}
        
        print("✅ Integrated Navigation Planner initialized")
    
    def update_environment(self, detections: List[Dict], frame_id: str = None, 
                          location_hint: str = None) -> Dict:
        """
        Update environment understanding with new detection data
        
        Args:
            detections: YOLO detection results
            frame_id: Frame identifier
            location_hint: Optional location context
            
        Returns:
            Environment update summary
        """
        # Update semantic understanding
        map_update = self.map_builder.update_map(detections, frame_id, location_hint)
        memory_update = self.scene_memory.update_scene_memory(detections)
        
        # Update grid map for pathfinding
        self.grid_map.update_from_detections(detections)
        
        # Learn goal locations from semantic understanding
        self._update_known_locations(map_update, detections)
        
        return {
            'map_update': map_update,
            'memory_update': memory_update,
            'grid_updated': True,
            'known_locations': len(self.known_locations)
        }
    
    def plan_navigation(self, request: NavigationRequest) -> NavigationResult:
        """
        Plan navigation based on request
        
        Args:
            request: Navigation planning request
            
        Returns:
            Navigation planning result
        """
        start_time = time.time()
        
        # Parse goal from description
        goal_pos = self._resolve_goal_location(request.goal_description)
        
        if goal_pos is None:
            return NavigationResult(
                success=False,
                path=None,
                pixel_path=None,
                algorithm_used=request.algorithm,
                planning_time=time.time() - start_time,
                path_cost=float('inf'),
                confidence=0.0,
                waypoint_descriptions=[],
                next_action=f"Cannot locate '{request.goal_description}' in current environment",
                estimated_duration=0.0,
                difficulty_level="impossible",
                semantic_guidance={}
            )
        
        # Convert start position to grid coordinates
        start_grid = self.grid_map.pixel_to_grid(request.start_pixel_pos[0], request.start_pixel_pos[1])
        
        # Choose algorithm based on request and environment
        algorithm = self._choose_algorithm(request, start_grid, goal_pos)
        
        # Plan path using chosen algorithm
        path_result = self._plan_with_algorithm(algorithm, start_grid, goal_pos, request)
        
        if path_result['success']:
            # Enhance result with semantic information
            enhanced_result = self._enhance_path_with_semantics(path_result, request)
            
            # Store for future reference
            self.current_goal = goal_pos
            self.active_path = path_result['path']
            self.last_planning_result = enhanced_result
            
            return enhanced_result
        else:
            return NavigationResult(
                success=False,
                path=None,
                pixel_path=None,
                algorithm_used=algorithm,
                planning_time=time.time() - start_time,
                path_cost=float('inf'),
                confidence=0.0,
                waypoint_descriptions=[],
                next_action="No path found to destination",
                estimated_duration=0.0,
                difficulty_level="impossible",
                semantic_guidance={}
            )
    
    def get_next_waypoint(self, current_pixel_pos: Tuple[float, float]) -> Optional[Dict]:
        """
        Get next waypoint in active path
        
        Args:
            current_pixel_pos: Current position in pixel coordinates
            
        Returns:
            Next waypoint information or None if no active path
        """
        if not self.active_path:
            return None
        
        current_grid = self.grid_map.pixel_to_grid(current_pixel_pos[0], current_pixel_pos[1])
        
        # Find current position in path
        min_distance = float('inf')
        current_index = 0
        
        for i, (gx, gy) in enumerate(self.active_path):
            distance = abs(gx - current_grid[0]) + abs(gy - current_grid[1])  # Manhattan distance
            if distance < min_distance:
                min_distance = distance
                current_index = i
        
        # Get next waypoint
        if current_index < len(self.active_path) - 1:
            next_grid = self.active_path[current_index + 1]
            next_pixel = self.grid_map.grid_to_pixel(next_grid[0], next_grid[1])
            
            # Get semantic information about waypoint
            semantic_info = self.grid_map.get_semantic_info(next_grid[0], next_grid[1])
            
            return {
                'grid_pos': next_grid,
                'pixel_pos': next_pixel,
                'distance': min_distance,
                'semantic_info': semantic_info,
                'waypoint_index': current_index + 1,
                'total_waypoints': len(self.active_path)
            }
        
        return None
    
    def replan_if_needed(self, current_pixel_pos: Tuple[float, float]) -> Optional[NavigationResult]:
        """
        Check if replanning is needed due to environment changes
        
        Args:
            current_pixel_pos: Current position
            
        Returns:
            New navigation result if replanning occurred, None otherwise
        """
        if not self.active_path or not self.current_goal:
            return None
        
        # Check if using D* (handles dynamic changes internally)
        if hasattr(self, 'last_algorithm_used') and self.last_algorithm_used == PathfindingAlgorithm.DSTAR:
            current_grid = self.grid_map.pixel_to_grid(current_pixel_pos[0], current_pixel_pos[1])
            new_path = self.dstar.replan_if_needed(current_grid[0], current_grid[1])
            
            if new_path:
                print("🔄 D* replanning successful")
                self.active_path = new_path
                
                # Create updated result
                return NavigationResult(
                    success=True,
                    path=new_path,
                    pixel_path=[self.grid_map.grid_to_pixel(x, y) for x, y in new_path],
                    algorithm_used=PathfindingAlgorithm.DSTAR,
                    planning_time=0.0,  # Replanning time
                    path_cost=self.dstar.get_search_statistics().get('path_cost', 0.0),
                    confidence=0.9,
                    waypoint_descriptions=[],
                    next_action="Following replanned path",
                    estimated_duration=len(new_path) * 0.5,
                    difficulty_level="moderate",
                    semantic_guidance={}
                )
        
        return None
    
    def _resolve_goal_location(self, goal_description: str) -> Optional[Tuple[int, int]]:
        """Resolve goal description to grid coordinates"""
        # Check known locations first
        goal_lower = goal_description.lower()
        
        for location_name, location_info in self.known_locations.items():
            if goal_lower in location_name.lower() or location_name.lower() in goal_lower:
                return location_info['grid_pos']
        
        # Try to infer from current environment
        nav_map = self.map_builder.get_navigation_map()
        
        # Look for relevant objects
        target_objects = []
        if 'computer' in goal_lower or 'monitor' in goal_lower:
            target_objects = ['monitor']
        elif 'study' in goal_lower or 'table' in goal_lower:
            target_objects = ['table', 'office-chair']
        elif 'reading' in goal_lower or 'book' in goal_lower:
            target_objects = ['books']
        elif 'presentation' in goal_lower or 'whiteboard' in goal_lower:
            target_objects = ['whiteboard']
        
        # Find best location based on object frequency and confidence
        best_location = None
        best_score = 0.0
        
        for obj_key, obj_info in nav_map['persistent_objects'].items():
            if obj_info['class_name'] in target_objects:
                score = obj_info['confidence'] * obj_info['frequency']
                if score > best_score:
                    best_score = score
                    # Extract grid position from object key (simplified)
                    # This would be improved with actual position tracking
                    best_location = (20, 15)  # Placeholder
        
        # Fallback: use center of environment
        if best_location is None:
            best_location = (self.grid_map.grid_width // 2, self.grid_map.grid_height // 2)
        
        return best_location
    
    def _choose_algorithm(self, request: NavigationRequest, start_grid: Tuple[int, int], 
                         goal_pos: Tuple[int, int]) -> PathfindingAlgorithm:
        """Choose best pathfinding algorithm based on request and environment"""
        if request.algorithm != PathfindingAlgorithm.AUTO:
            return request.algorithm
        
        # Auto-selection logic
        scene_context = self.scene_memory.get_scene_context()
        
        # Use D* for dynamic environments
        if scene_context['current_stability'] < 0.7:
            return PathfindingAlgorithm.DSTAR
        
        # Use RRT* for complex environments
        obstacle_density = len([obj for obj in self.grid_map.grid.flatten() 
                              if obj == 1]) / self.grid_map.grid.size
        
        if obstacle_density > 0.3 or request.strategy == NavigationStrategy.EXPLORATION:
            return PathfindingAlgorithm.RRT_STAR
        
        # Default to A* for optimal paths in stable environments
        return PathfindingAlgorithm.ASTAR
    
    def _plan_with_algorithm(self, algorithm: PathfindingAlgorithm, start_grid: Tuple[int, int],
                           goal_pos: Tuple[int, int], request: NavigationRequest) -> Dict:
        """Plan path using specified algorithm"""
        if algorithm == PathfindingAlgorithm.ASTAR:
            path = self.astar.find_path(start_grid[0], start_grid[1], goal_pos[0], goal_pos[1], 
                                      timeout=request.timeout, smooth_path=True)
            stats = self.astar.get_search_statistics()
            
        elif algorithm == PathfindingAlgorithm.DSTAR:
            self.dstar.set_goal(goal_pos[0], goal_pos[1])
            path = self.dstar.find_path(start_grid[0], start_grid[1], timeout=request.timeout)
            stats = self.dstar.get_search_statistics()
            
        elif algorithm == PathfindingAlgorithm.RRT_STAR:
            path = self.rrt_star.find_path(start_grid[0], start_grid[1], goal_pos[0], goal_pos[1],
                                         timeout=request.timeout)
            stats = self.rrt_star.get_search_statistics()
        
        else:
            return {'success': False, 'path': None, 'stats': {}}
        
        self.last_algorithm_used = algorithm
        
        return {
            'success': path is not None,
            'path': path,
            'stats': stats,
            'algorithm': algorithm
        }
    
    def _enhance_path_with_semantics(self, path_result: Dict, request: NavigationRequest) -> NavigationResult:
        """Enhance path result with semantic information"""
        path = path_result['path']
        stats = path_result['stats']
        algorithm = path_result['algorithm']
        
        # Convert to pixel coordinates
        pixel_path = [self.grid_map.grid_to_pixel(x, y) for x, y in path]
        
        # Generate waypoint descriptions
        waypoint_descriptions = self._generate_waypoint_descriptions(path)
        
        # Determine next action
        next_action = self._generate_next_action(path, request.goal_description)
        
        # Estimate traversal difficulty and duration
        difficulty = self._assess_path_difficulty(path)
        duration = self._estimate_traversal_time(path)
        
        # Calculate confidence based on various factors
        confidence = self._calculate_path_confidence(path, stats, algorithm)
        
        # Get semantic guidance
        semantic_guidance = self._generate_semantic_guidance(path, request)
        
        return NavigationResult(
            success=True,
            path=path,
            pixel_path=pixel_path,
            algorithm_used=algorithm,
            planning_time=stats.get('search_time', 0.0),
            path_cost=stats.get('path_cost', 0.0),
            confidence=confidence,
            waypoint_descriptions=waypoint_descriptions,
            next_action=next_action,
            estimated_duration=duration,
            difficulty_level=difficulty,
            semantic_guidance=semantic_guidance
        )
    
    def _update_known_locations(self, map_update: Dict, detections: List[Dict]):
        """Update known locations based on semantic understanding"""
        zone_type = map_update.get('zone_type', 'general_area')
        
        if zone_type != 'general_area':
            # Calculate center of detected objects
            if detections:
                center_x = sum(det['bbox']['center_x'] for det in detections) / len(detections)
                center_y = sum(det['bbox']['center_y'] for det in detections) / len(detections)
                grid_pos = self.grid_map.pixel_to_grid(center_x, center_y)
                
                self.known_locations[zone_type] = {
                    'grid_pos': grid_pos,
                    'confidence': sum(det['confidence'] for det in detections) / len(detections),
                    'last_seen': time.time()
                }
    
    def _generate_waypoint_descriptions(self, path: List[Tuple[int, int]]) -> List[str]:
        """Generate human-readable descriptions for waypoints"""
        descriptions = []
        
        for i, (x, y) in enumerate(path[::max(1, len(path)//5)]):  # Sample every few waypoints
            semantic_info = self.grid_map.get_semantic_info(x, y)
            
            if semantic_info:
                obj_name = semantic_info['class_name']
                descriptions.append(f"Pass by {obj_name}")
            else:
                descriptions.append(f"Continue forward")
        
        return descriptions
    
    def _generate_next_action(self, path: List[Tuple[int, int]], goal_description: str) -> str:
        """Generate next action description"""
        if len(path) > 1:
            start = path[0]
            next_point = path[1]
            
            dx = next_point[0] - start[0]
            dy = next_point[1] - start[1]
            
            if abs(dx) > abs(dy):
                direction = "right" if dx > 0 else "left"
            else:
                direction = "forward" if dy > 0 else "backward"
            
            return f"Head {direction} toward {goal_description}"
        
        return f"Navigate to {goal_description}"
    
    def _assess_path_difficulty(self, path: List[Tuple[int, int]]) -> str:
        """Assess difficulty of following the path"""
        if not path:
            return "impossible"
        
        total_cost = 0.0
        obstacle_count = 0
        
        for x, y in path:
            cost = self.grid_map.get_cost(x, y)
            total_cost += cost
            if cost > 5.0:
                obstacle_count += 1
        
        avg_cost = total_cost / len(path)
        obstacle_ratio = obstacle_count / len(path)
        
        if avg_cost > 8.0 or obstacle_ratio > 0.5:
            return "difficult"
        elif avg_cost > 4.0 or obstacle_ratio > 0.2:
            return "moderate"
        else:
            return "easy"
    
    def _estimate_traversal_time(self, path: List[Tuple[int, int]]) -> float:
        """Estimate time to traverse the path (in seconds)"""
        if not path:
            return 0.0
        
        # Base time per grid cell (assuming slow walking speed)
        base_time_per_cell = 0.5  # seconds
        
        total_time = 0.0
        for x, y in path:
            cost_multiplier = self.grid_map.get_cost(x, y)
            total_time += base_time_per_cell * cost_multiplier
        
        return total_time
    
    def _calculate_path_confidence(self, path: List[Tuple[int, int]], stats: Dict, 
                                 algorithm: PathfindingAlgorithm) -> float:
        """Calculate confidence in the planned path"""
        base_confidence = 0.8
        
        # Algorithm-specific confidence
        if algorithm == PathfindingAlgorithm.ASTAR:
            base_confidence = 0.9  # Optimal paths
        elif algorithm == PathfindingAlgorithm.DSTAR:
            base_confidence = 0.85  # Good for dynamic environments
        elif algorithm == PathfindingAlgorithm.RRT_STAR:
            base_confidence = 0.7   # Probabilistic, may not be optimal
        
        # Adjust based on search statistics
        if stats.get('success', False):
            search_time = stats.get('search_time', 0.0)
            if search_time < 1.0:
                base_confidence += 0.1  # Fast solutions are good
            elif search_time > 5.0:
                base_confidence -= 0.1  # Slow solutions might be suboptimal
        
        # Adjust based on scene stability
        scene_context = self.scene_memory.get_scene_context()
        stability = scene_context.get('current_stability', 1.0)
        base_confidence *= stability
        
        return max(0.1, min(1.0, base_confidence))
    
    def _generate_semantic_guidance(self, path: List[Tuple[int, int]], 
                                  request: NavigationRequest) -> Dict[str, Any]:
        """Generate semantic guidance for navigation"""
        # Analyze path environment
        path_objects = []
        for x, y in path:
            semantic_info = self.grid_map.get_semantic_info(x, y)
            if semantic_info:
                path_objects.append(semantic_info['class_name'])
        
        # Get environment context
        nav_map = self.map_builder.get_navigation_map()
        scene_context = self.scene_memory.get_scene_context()
        
        return {
            'path_objects': list(set(path_objects)),
            'environment_familiarity': len(scene_context.get('environment_history', {})),
            'obstacles_detected': len([obj for obj in path_objects if obj in ['table', 'office-chair']]),
            'landmarks_available': len([obj for obj in path_objects if obj in ['monitor', 'whiteboard']]),
            'navigation_confidence': scene_context.get('current_stability', 1.0)
        }
    
    def get_planning_statistics(self) -> Dict:
        """Get comprehensive planning statistics"""
        return {
            'known_locations': len(self.known_locations),
            'grid_dimensions': (self.grid_map.grid_width, self.grid_map.grid_height),
            'last_result': self.last_planning_result.__dict__ if self.last_planning_result else None,
            'scene_memory': self.scene_memory.get_scene_context(),
            'semantic_map': self.map_builder.get_navigation_map()
        }


# Test the navigation planner
if __name__ == "__main__":
    print("Testing Integrated Navigation Planner...")
    
    # Initialize planner
    planner = NavigationPlanner(width=640, height=480, resolution=20.0)
    
    # Simulate environment update
    test_detections = [
        {
            'class_name': 'monitor',
            'confidence': 0.95,
            'bbox': {'x1': 300, 'y1': 150, 'x2': 450, 'y2': 250,
                    'center_x': 375, 'center_y': 200},
            'frame_position': 'center',
            'relative_size': 'large'
        },
        {
            'class_name': 'office-chair',
            'confidence': 0.85,
            'bbox': {'x1': 200, 'y1': 350, 'x2': 300, 'y2': 450,
                    'center_x': 250, 'center_y': 400},
            'frame_position': 'bottom-left',
            'relative_size': 'medium'
        }
    ]
    
    # Update environment
    env_update = planner.update_environment(test_detections, "test_frame", "Computer lab")
    print(f"✅ Environment updated: {env_update['map_update']['zone_type']}")
    
    # Create navigation request
    request = NavigationRequest(
        goal_description="computer lab",
        start_pixel_pos=(50.0, 50.0),
        algorithm=PathfindingAlgorithm.AUTO,
        strategy=NavigationStrategy.OPTIMAL,
        timeout=5.0
    )
    
    # Plan navigation
    print(f"\n🚀 Planning navigation to '{request.goal_description}'...")
    result = planner.plan_navigation(request)
    
    if result.success:
        print(f"✅ Navigation planned successfully!")
        print(f"   Algorithm used: {result.algorithm_used.value}")
        print(f"   Path length: {len(result.path)} waypoints")
        print(f"   Planning time: {result.planning_time:.3f}s")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Difficulty: {result.difficulty_level}")
        print(f"   Estimated duration: {result.estimated_duration:.1f}s")
        print(f"   Next action: {result.next_action}")
        
        # Test waypoint navigation
        next_waypoint = planner.get_next_waypoint((60.0, 60.0))
        if next_waypoint:
            print(f"   Next waypoint: {next_waypoint['pixel_pos']}")
        
    else:
        print(f"❌ Navigation planning failed")
        print(f"   Next action: {result.next_action}")
    
    # Get comprehensive statistics
    stats = planner.get_planning_statistics()
    print(f"\n📊 Planning Statistics:")
    print(f"   Known locations: {stats['known_locations']}")
    print(f"   Grid size: {stats['grid_dimensions']}")
    
    print("\n✅ Navigation planner test completed!")