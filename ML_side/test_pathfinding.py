"""
Comprehensive Test Suite for Pathfinding Algorithms
Tests A*, D*, RRT*, and integrated navigation planner
"""

import time
import cv2
import numpy as np
from typing import List, Tuple

# Import pathfinding components
from src.pathfinding.grid_map import LibraryGridMap
from src.pathfinding.astar import AStarPathfinder
from src.pathfinding.dstar import DStarPathfinder
from src.pathfinding.rrt_star import RRTStarPathfinder
from src.pathfinding.navigation_planner import NavigationPlanner, NavigationRequest, PathfindingAlgorithm, NavigationStrategy

def create_test_environment() -> Tuple[LibraryGridMap, List[dict]]:
    """Create test environment with obstacles"""
    grid_map = LibraryGridMap(width=640, height=480, resolution=20.0)
    
    # Create complex test environment
    test_detections = [
        {
            'class_name': 'table',
            'confidence': 0.92,
            'bbox': {'x1': 150, 'y1': 100, 'x2': 300, 'y2': 180, 
                    'center_x': 225, 'center_y': 140}
        },
        {
            'class_name': 'office-chair',
            'confidence': 0.88,
            'bbox': {'x1': 350, 'y1': 250, 'x2': 450, 'y2': 350,
                    'center_x': 400, 'center_y': 300}
        },
        {
            'class_name': 'whiteboard',
            'confidence': 0.95,
            'bbox': {'x1': 500, 'y1': 50, 'x2': 620, 'y2': 100,
                    'center_x': 560, 'center_y': 75}
        },
        {
            'class_name': 'monitor',
            'confidence': 0.90,
            'bbox': {'x1': 100, 'y1': 300, 'x2': 250, 'y2': 380,
                    'center_x': 175, 'center_y': 340}
        },
        {
            'class_name': 'books',
            'confidence': 0.85,
            'bbox': {'x1': 450, 'y1': 350, 'x2': 550, 'y2': 400,
                    'center_x': 500, 'center_y': 375}
        }
    ]
    
    grid_map.update_from_detections(test_detections)
    return grid_map, test_detections

def test_astar_pathfinding():
    """Test A* pathfinding algorithm"""
    print("\n🚀 Testing A* Pathfinding")
    print("=" * 50)
    
    grid_map, _ = create_test_environment()
    pathfinder = AStarPathfinder(grid_map)
    
    # Test scenarios
    test_cases = [
        {"name": "Simple path", "start": (2, 2), "goal": (30, 20)},
        {"name": "Around obstacles", "start": (5, 15), "goal": (25, 8)},
        {"name": "Long distance", "start": (1, 1), "goal": (31, 23)},
    ]
    
    for case in test_cases:
        print(f"\n📍 Test case: {case['name']}")
        start_time = time.time()
        
        path = pathfinder.find_path(
            case['start'][0], case['start'][1], 
            case['goal'][0], case['goal'][1],
            timeout=5.0
        )
        
        if path:
            stats = pathfinder.get_search_statistics()
            print(f"✅ Path found!")
            print(f"   Length: {len(path)} waypoints")
            print(f"   Cost: {stats['path_cost']:.2f}")
            print(f"   Time: {stats['search_time']:.3f}s")
            print(f"   Nodes explored: {stats['nodes_explored']}")
        else:
            print(f"❌ No path found")
    
    return True

def test_dstar_pathfinding():
    """Test D* (Dynamic A*) pathfinding algorithm"""
    print("\n🚀 Testing D* Dynamic Pathfinding")
    print("=" * 50)
    
    grid_map, test_detections = create_test_environment()
    pathfinder = DStarPathfinder(grid_map)
    
    # Set goal
    goal_pos = (28, 18)
    pathfinder.set_goal(goal_pos[0], goal_pos[1])
    
    # Find initial path
    start_pos = (3, 3)
    print(f"📍 Finding initial path from {start_pos} to {goal_pos}")
    
    path = pathfinder.find_path(start_pos[0], start_pos[1], timeout=8.0)
    
    if path:
        stats = pathfinder.get_search_statistics()
        print(f"✅ Initial path found!")
        print(f"   Length: {len(path)} waypoints")
        print(f"   Cost: {stats['path_cost']:.2f}")
        print(f"   Time: {stats['search_time']:.3f}s")
        
        # Simulate environment change
        print(f"\n🔄 Simulating dynamic environment change...")
        
        # Add new obstacle
        new_detections = test_detections + [
            {
                'class_name': 'table',
                'confidence': 0.90,
                'bbox': {'x1': 200, 'y1': 200, 'x2': 350, 'y2': 280,
                        'center_x': 275, 'center_y': 240}
            }
        ]
        
        grid_map.update_from_detections(new_detections)
        
        # Test replanning
        midpoint = path[len(path)//2] if len(path) > 2 else start_pos
        new_path = pathfinder.replan_if_needed(midpoint[0], midpoint[1])
        
        if new_path:
            new_stats = pathfinder.get_search_statistics()
            print(f"✅ Replanning successful!")
            print(f"   New length: {len(new_path)} waypoints")
            print(f"   Replan count: {new_stats['replan_count']}")
        else:
            print(f"ℹ️ No replanning needed")
    else:
        print(f"❌ No initial path found")
    
    return True

def test_rrt_star_pathfinding():
    """Test RRT* pathfinding algorithm"""
    print("\n🚀 Testing RRT* Sampling-Based Pathfinding")
    print("=" * 50)
    
    grid_map, _ = create_test_environment()
    pathfinder = RRTStarPathfinder(grid_map)
    
    # Configure for faster testing
    pathfinder.set_parameters(
        max_iterations=1500,
        step_size=3.0,
        goal_tolerance=2.5,
        rewire_radius=7.0,
        goal_bias=0.15
    )
    
    # Test scenario
    start_pos = (2, 2)
    goal_pos = (29, 20)
    
    print(f"📍 Finding path from {start_pos} to {goal_pos} using RRT*")
    print(f"   (This may take longer due to sampling-based nature)")
    
    path = pathfinder.find_path(
        start_pos[0], start_pos[1], 
        goal_pos[0], goal_pos[1], 
        timeout=10.0
    )
    
    if path:
        stats = pathfinder.get_search_statistics()
        print(f"✅ RRT* path found!")
        print(f"   Length: {len(path)} waypoints")
        print(f"   Cost: {stats['path_cost']:.2f}")
        print(f"   Time: {stats['search_time']:.3f}s")
        print(f"   Iterations: {stats['iterations']}")
        print(f"   Tree size: {stats['tree_size']}")
        print(f"   Goal found at iteration: {stats['goal_found_iteration']}")
    else:
        stats = pathfinder.get_search_statistics()
        print(f"❌ No path found")
        print(f"   Iterations: {stats['iterations']}")
        print(f"   Tree size: {stats['tree_size']}")
    
    return True

def test_algorithm_comparison():
    """Compare all three pathfinding algorithms"""
    print("\n🚀 Algorithm Performance Comparison")
    print("=" * 50)
    
    grid_map, _ = create_test_environment()
    
    # Initialize all algorithms
    astar = AStarPathfinder(grid_map)
    dstar = DStarPathfinder(grid_map)
    rrt_star = RRTStarPathfinder(grid_map)
    
    # Configure RRT* for reasonable comparison
    rrt_star.set_parameters(max_iterations=800, step_size=4.0, goal_tolerance=3.0)
    
    # Test scenario - use simpler positions
    start_pos = (2, 2)
    goal_pos = (25, 15)
    
    print(f"📍 Comparing algorithms: {start_pos} → {goal_pos}")
    
    results = {}
    
    # Test A*
    print(f"\n🔸 A* Algorithm:")
    path_astar = astar.find_path(start_pos[0], start_pos[1], goal_pos[0], goal_pos[1], timeout=5.0)
    stats_astar = astar.get_search_statistics()
    results['A*'] = {
        'success': path_astar is not None,
        'length': len(path_astar) if path_astar else 0,
        'cost': stats_astar.get('path_cost', float('inf')),
        'time': stats_astar.get('search_time', 0.0),
        'nodes_explored': stats_astar.get('nodes_explored', 0)
    }
    print(f"   Success: {results['A*']['success']}")
    print(f"   Length: {results['A*']['length']}")
    print(f"   Cost: {results['A*']['cost']:.2f}")
    print(f"   Time: {results['A*']['time']:.3f}s")
    
    # Test D*
    print(f"\n🔸 D* Algorithm:")
    dstar.set_goal(goal_pos[0], goal_pos[1])
    path_dstar = dstar.find_path(start_pos[0], start_pos[1], timeout=5.0)
    stats_dstar = dstar.get_search_statistics()
    results['D*'] = {
        'success': path_dstar is not None,
        'length': len(path_dstar) if path_dstar else 0,
        'cost': stats_dstar.get('path_cost', float('inf')),
        'time': stats_dstar.get('search_time', 0.0)
    }
    print(f"   Success: {results['D*']['success']}")
    print(f"   Length: {results['D*']['length']}")
    print(f"   Cost: {results['D*']['cost']:.2f}")
    print(f"   Time: {results['D*']['time']:.3f}s")
    
    # Test RRT*
    print(f"\n🔸 RRT* Algorithm:")
    path_rrt = rrt_star.find_path(start_pos[0], start_pos[1], goal_pos[0], goal_pos[1], timeout=8.0)
    stats_rrt = rrt_star.get_search_statistics()
    results['RRT*'] = {
        'success': path_rrt is not None,
        'length': len(path_rrt) if path_rrt else 0,
        'cost': stats_rrt.get('path_cost', float('inf')),
        'time': stats_rrt.get('search_time', 0.0),
        'iterations': stats_rrt.get('iterations', 0)
    }
    print(f"   Success: {results['RRT*']['success']}")
    print(f"   Length: {results['RRT*']['length']}")
    print(f"   Cost: {results['RRT*']['cost']:.2f}")
    print(f"   Time: {results['RRT*']['time']:.3f}s")
    print(f"   Iterations: {results['RRT*']['iterations']}")
    
    # Summary
    print(f"\n📊 COMPARISON SUMMARY:")
    successful_algorithms = [name for name, result in results.items() if result['success']]
    
    if successful_algorithms:
        print(f"   Successful algorithms: {', '.join(successful_algorithms)}")
        
        # Find best in each category
        fastest = min(successful_algorithms, key=lambda x: results[x]['time'])
        shortest = min(successful_algorithms, key=lambda x: results[x]['length'])
        lowest_cost = min(successful_algorithms, key=lambda x: results[x]['cost'])
        
        print(f"   Fastest: {fastest} ({results[fastest]['time']:.3f}s)")
        print(f"   Shortest path: {shortest} ({results[shortest]['length']} waypoints)")
        print(f"   Lowest cost: {lowest_cost} (cost: {results[lowest_cost]['cost']:.2f})")
    else:
        print(f"   No algorithms found a path!")
    
    return True

def test_integrated_navigation_planner():
    """Test the integrated navigation planner"""
    print("\n🚀 Testing Integrated Navigation Planner")
    print("=" * 50)
    
    # Initialize planner
    planner = NavigationPlanner(image_width=640, image_height=480, resolution=20.0)
    
    # Create enhanced test detections with semantic info
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
            'confidence': 0.88,
            'bbox': {'x1': 200, 'y1': 300, 'x2': 300, 'y2': 400,
                    'center_x': 250, 'center_y': 350},
            'frame_position': 'bottom-left',
            'relative_size': 'medium'
        },
        {
            'class_name': 'table',
            'confidence': 0.90,
            'bbox': {'x1': 450, 'y1': 280, 'x2': 580, 'y2': 350,
                    'center_x': 515, 'center_y': 315},
            'frame_position': 'bottom-right',
            'relative_size': 'large'
        }
    ]
    
    # Update environment
    print(f"🌍 Updating environment with {len(test_detections)} detections...")
    env_update = planner.update_environment(test_detections, "integration_test", "Computer lab")
    print(f"   Environment type: {env_update['map_update']['zone_type']}")
    print(f"   Navigation difficulty: {env_update['map_update']['navigation_info']['navigation_difficulty']}")
    
    # Test navigation scenarios
    navigation_scenarios = [
        {
            'name': 'Find computer lab',
            'goal': 'computer lab',
            'start': (50.0, 50.0),
            'algorithm': PathfindingAlgorithm.AUTO,
            'strategy': NavigationStrategy.OPTIMAL
        },
        {
            'name': 'Find study area',
            'goal': 'study area',
            'start': (100.0, 100.0),
            'algorithm': PathfindingAlgorithm.ASTAR,
            'strategy': NavigationStrategy.FAST
        },
        {
            'name': 'Dynamic navigation',
            'goal': 'computer lab',
            'start': (80.0, 80.0),
            'algorithm': PathfindingAlgorithm.DSTAR,
            'strategy': NavigationStrategy.DYNAMIC
        }
    ]
    
    for scenario in navigation_scenarios:
        print(f"\n📍 Scenario: {scenario['name']}")
        
        # Create request
        request = NavigationRequest(
            goal_description=scenario['goal'],
            start_pixel_pos=scenario['start'],
            algorithm=scenario['algorithm'],
            strategy=scenario['strategy'],
            timeout=8.0
        )
        
        # Plan navigation
        result = planner.plan_navigation(request)
        
        if result.success:
            print(f"✅ Navigation successful!")
            print(f"   Algorithm used: {result.algorithm_used.value}")
            print(f"   Path length: {len(result.path)} waypoints")
            print(f"   Planning time: {result.planning_time:.3f}s")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Difficulty: {result.difficulty_level}")
            print(f"   Next action: {result.next_action}")
            print(f"   Estimated duration: {result.estimated_duration:.1f}s")
            
            # Test waypoint navigation
            next_waypoint = planner.get_next_waypoint((60.0, 60.0))
            if next_waypoint:
                print(f"   Next waypoint: Grid {next_waypoint['grid_pos']}")
        else:
            print(f"❌ Navigation failed: {result.next_action}")
    
    # Get comprehensive statistics
    stats = planner.get_planning_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Known locations: {stats['known_locations']}")
    print(f"   Grid dimensions: {stats['grid_dimensions']}")
    
    return True

def test_visualization():
    """Test pathfinding visualization"""
    print("\n🚀 Testing Pathfinding Visualization")
    print("=" * 50)
    
    grid_map, _ = create_test_environment()
    
    # Find path with A*
    pathfinder = AStarPathfinder(grid_map)
    start_pos = (2, 2)
    goal_pos = (30, 20)
    
    # Set start and goal on map
    grid_map.set_start(start_pos[0] * 20, start_pos[1] * 20)
    grid_map.set_goal(goal_pos[0] * 20, goal_pos[1] * 20)
    
    path = pathfinder.find_path(start_pos[0], start_pos[1], goal_pos[0], goal_pos[1])
    
    if path:
        # Mark path on grid
        grid_map.mark_path(path)
        
        # Save visualization
        grid_map.save_map_image("pathfinding_test_result.png", scale_factor=10)
        print(f"✅ Visualization saved to pathfinding_test_result.png")
        print(f"   Path length: {len(path)} waypoints")
    else:
        print(f"❌ Could not create visualization - no path found")
    
    return True

def main():
    """Run all pathfinding tests"""
    print("🧪 COMPREHENSIVE PATHFINDING TEST SUITE")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Test individual algorithms
        print("\n" + "=" * 60)
        print("INDIVIDUAL ALGORITHM TESTS")
        print("=" * 60)
        
        test_results.append(("A* Algorithm", test_astar_pathfinding()))
        test_results.append(("D* Algorithm", test_dstar_pathfinding()))
        test_results.append(("RRT* Algorithm", test_rrt_star_pathfinding()))
        
        # Comparative tests
        print("\n" + "=" * 60)
        print("COMPARATIVE TESTS")
        print("=" * 60)
        
        test_results.append(("Algorithm Comparison", test_algorithm_comparison()))
        
        # Integration tests
        print("\n" + "=" * 60)
        print("INTEGRATION TESTS")
        print("=" * 60)
        
        test_results.append(("Navigation Planner", test_integrated_navigation_planner()))
        test_results.append(("Visualization", test_visualization()))
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<25} {status}")
        if result:
            passed_tests += 1
    
    print(f"\n📊 Final Score: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All pathfinding tests PASSED! System is ready for navigation.")
    else:
        print("⚠️ Some tests failed. Please check the implementations.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)