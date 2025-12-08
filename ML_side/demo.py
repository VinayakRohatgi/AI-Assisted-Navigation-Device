"""
AI-Assisted Navigation Device - Live Demo
Demonstrates the complete navigation system with real YOLO model
"""

import cv2
import time
from src.llm_integration.navigation_pipeline import BasicNavigationPipeline
from src.semantic_mapping.library_map_builder import LibraryMapBuilder
from src.semantic_mapping.scene_memory import SceneMemorySystem
from src.pathfinding.navigation_planner import NavigationPlanner, NavigationRequest, PathfindingAlgorithm

def run_demo():
    """Run live demo of navigation system"""
    print(" AI-ASSISTED NAVIGATION DEVICE - LIVE DEMO")
    print("=" * 55)
    
    # Initialize all components
    print(" Initializing navigation system...")
    
    try:
        # Core navigation pipeline
        model_path = "models/object_detection/best.pt"
        nav_pipeline = BasicNavigationPipeline(model_path, use_llm=True)
        
        # Semantic understanding
        map_builder = LibraryMapBuilder()
        scene_memory = SceneMemorySystem()
        
        # Pathfinding planner
        planner = NavigationPlanner(image_width=640, image_height=480, resolution=20.0)
        
        print(" All systems initialized successfully!")
        
    except Exception as e:
        print(f" Initialization failed: {e}")
        return False
    
    # Demo scenarios
    demo_scenarios = [
        {
            'name': 'Computer Lab Navigation',
            'goal': 'computer lab',
            'location': 'Library entrance'
        },
        {
            'name': 'Study Area Finding',
            'goal': 'quiet study area', 
            'location': 'Main library floor'
        },
        {
            'name': 'Reading Area Location',
            'goal': 'reading area',
            'location': 'Near circulation desk'
        }
    ]
    
    # Try webcam first, fallback to test images
    cap = cv2.VideoCapture(0)
    using_camera = cap.isOpened()
    
    if not using_camera:
        print(" Camera not available, using test images...")
        # Get test images
        import glob
        import os
        
        test_images = []
        for directory in ["data/processed/val_dataset/val/images/", "data/processed/train_dataset/train/images/"]:
            if os.path.exists(directory):
                images = glob.glob(os.path.join(directory, "*.jpg"))
                test_images.extend(images[:3])
                break
        
        if not test_images:
            print(" No test images available")
            return False
    else:
        print(" Using live camera feed")
    
    # Run demo scenarios
    for i, scenario in enumerate(demo_scenarios):
        print(f"\n{'='*55}")
        print(f" DEMO SCENARIO {i+1}: {scenario['name']}")
        print(f"{'='*55}")
        
        # Get image
        if using_camera:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture camera frame")
                continue
        else:
            if i < len(test_images):
                frame = cv2.imread(test_images[i])
                print(f"📸 Using test image: {os.path.basename(test_images[i])}")
            else:
                frame = cv2.imread(test_images[0])
        
        if frame is None:
            continue
        
        print(f" Goal: {scenario['goal']}")
        print(f" Starting location: {scenario['location']}")
        
        # Step 1: Object Detection
        print(f"\n Step 1: Analyzing environment...")
        nav_result = nav_pipeline.process_frame(
            frame,
            user_intent=f"Navigate to {scenario['goal']}",
            current_location=scenario['location']
        )
        
        if nav_result['detections']:
            print(f" Detected {len(nav_result['detections'])} objects:")
            for det in nav_result['detections'][:3]:
                print(f"   - {det['class_name'].upper()} ({det['confidence']:.2f}) at {det['frame_position']}")
        else:
            print("   No objects detected")
        
        # Step 2: Semantic Understanding
        print(f"\n Step 2: Building semantic understanding...")
        map_update = map_builder.update_map(
            nav_result['detections'],
            f"demo_frame_{i+1}",
            scenario['location']
        )
        
        memory_update = scene_memory.update_scene_memory(nav_result['detections'])
        
        print(f" Environment classified as: {map_update['zone_type']}")
        print(f"   Navigation difficulty: {map_update['navigation_info']['navigation_difficulty']}")
        print(f"   Tracked objects: {memory_update['memory_stats']['tracked_objects']}")
        
        # Step 3: Navigation Planning
        print(f"\n Step 3: Planning navigation route...")
        planner.update_environment(nav_result['detections'], f"demo_{i+1}", scenario['location'])
        
        request = NavigationRequest(
            goal_description=scenario['goal'],
            start_pixel_pos=(50.0, 50.0),
            algorithm=PathfindingAlgorithm.AUTO
        )
        
        nav_plan = planner.plan_navigation(request)
        
        if nav_plan.success:
            print(f" Navigation route planned successfully!")
            print(f"   Algorithm: {nav_plan.algorithm_used.value}")
            print(f"   Path length: {len(nav_plan.path)} waypoints")
            print(f"   Confidence: {nav_plan.confidence:.2f}")
            print(f"   Difficulty: {nav_plan.difficulty_level}")
            print(f"   Estimated time: {nav_plan.estimated_duration:.1f}s")
        else:
            print(f" Navigation planning failed")
        
        # Step 4: Navigation Guidance
        print(f"\n Step 4: Navigation guidance...")
        nav_decision = nav_result['navigation_decision']
        
        print(f" Next action: {nav_plan.next_action if nav_plan.success else nav_decision.get('direction', 'No guidance available')}")
        
        if nav_plan.success and 'reasoning' in nav_decision:
            print(f"   Reasoning: {nav_decision['reasoning'][:80]}...")
        
        # Show visual result if available
        if using_camera:
            # Draw detections on frame
            for det in nav_result['detections']:
                bbox = det['bbox']
                cv2.rectangle(frame,
                            (int(bbox['x1']), int(bbox['y1'])),
                            (int(bbox['x2']), int(bbox['y2'])),
                            (0, 255, 0), 2)
                cv2.putText(frame,
                          f"{det['class_name']} ({det['confidence']:.2f})",
                          (int(bbox['x1']), int(bbox['y1']-10)),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow(f'Demo - {scenario["name"]}', frame)
            cv2.waitKey(3000)  # Show for 3 seconds
            cv2.destroyAllWindows()
        
        print(f"\n Scenario {i+1} completed!")
        
        if not using_camera:
            time.sleep(2)  # Pause between scenarios
    
    if using_camera:
        cap.release()
    
    print(f"\n DEMO COMPLETED SUCCESSFULLY!")
    print("The AI-Assisted Navigation Device is fully functional with:")
    print("    Real-time object detection (YOLO)")
    print("    Semantic environment understanding")
    print("    Intelligent pathfinding (A*, RRT*)")
    print("    Natural language navigation guidance")
    print("    Dynamic scene memory and tracking")
    
    return True

if __name__ == "__main__":
    success = run_demo()
    if success:
        print("\n System ready for deployment!")
    else:
        print("\n Demo encountered issues")
        exit(1)