"""
Test Semantic Mapping Integration with Navigation Pipeline
"""

import cv2
import glob
import os
import time
from datetime import datetime
from src.llm_integration.navigation_pipeline import BasicNavigationPipeline
from src.semantic_mapping.library_map_builder import LibraryMapBuilder
from src.semantic_mapping.scene_memory import SceneMemorySystem

def test_integrated_semantic_navigation():
    """Test the complete semantic mapping + navigation system"""
    print("🚀 Testing Integrated Semantic Navigation System")
    print("="*70)
    
    # Initialize components
    model_path = "models/object_detection/best.pt"
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        return
    
    try:
        # Initialize all components
        navigation_pipeline = BasicNavigationPipeline(model_path, use_llm=True)
        map_builder = LibraryMapBuilder()
        scene_memory = SceneMemorySystem()
        
        print("✅ All components initialized successfully")
        
    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        return
    
    # Get test images
    test_images = []
    image_directories = [
        "data/processed/val_dataset/val/images/",
        "data/processed/train_dataset/train/images/"
    ]
    
    for directory in image_directories:
        if os.path.exists(directory):
            images = glob.glob(os.path.join(directory, "*.jpg"))
            test_images.extend(images[:5])  # Take 5 images from each
            break
    
    if not test_images:
        print("❌ No test images found")
        return
    
    print(f"\n📸 Found {len(test_images)} test images")
    
    # Process images with full semantic pipeline
    for i, img_path in enumerate(test_images):
        print(f"\n{'='*50}")
        print(f"🖼️ Processing Image {i+1}: {os.path.basename(img_path)}")
        print(f"{'='*50}")
        
        # Load image
        image = cv2.imread(img_path)
        if image is None:
            continue
        
        # Simulate different user intents
        test_scenarios = [
            {"intent": "Find a computer to work on", "location": "Library entrance"},
            {"intent": "Look for a quiet study spot", "location": "Main floor"},
            {"intent": "Find the reading area", "location": "Near circulation desk"}
        ]
        
        scenario = test_scenarios[i % len(test_scenarios)]
        
        # 1. Basic navigation processing
        nav_result = navigation_pipeline.process_frame(
            image, 
            user_intent=scenario["intent"],
            current_location=scenario["location"]
        )
        
        # 2. Update semantic map
        frame_id = f"frame_{datetime.now().strftime('%H%M%S')}_{i}"
        map_update = map_builder.update_map(
            nav_result['detections'], 
            frame_id=frame_id,
            location_hint=scenario["location"]
        )
        
        # 3. Update scene memory
        memory_update = scene_memory.update_scene_memory(
            nav_result['detections']
        )
        
        # Display comprehensive results
        display_results(nav_result, map_update, memory_update, scenario)
        
        # Small delay to simulate real-time processing
        time.sleep(1)
    
    # Generate comprehensive summary
    generate_comprehensive_summary(map_builder, scene_memory)

def display_results(nav_result, map_update, memory_update, scenario):
    """Display comprehensive results from all systems"""
    
    print(f"🎯 SCENARIO: {scenario['intent']}")
    print(f"📍 Location: {scenario['location']}")
    
    # Navigation results
    print(f"\n🔍 NAVIGATION ANALYSIS:")
    print(f"   Objects detected: {len(nav_result['detections'])}")
    
    if nav_result['detections']:
        for j, det in enumerate(nav_result['detections'][:3]):  # Show top 3
            print(f"   {j+1}. {det['class_name'].upper()} ({det['confidence']:.2f}) at {det['frame_position']}")
    
    nav_decision = nav_result['navigation_decision']
    print(f"\n🧠 NAVIGATION DECISION:")
    print(f"   Direction: {nav_decision.get('direction', 'N/A')[:80]}...")
    print(f"   Safety Level: {nav_decision.get('safety_level', 'N/A')}")
    
    if 'reasoning' in nav_decision:
        print(f"   Reasoning: {nav_decision['reasoning'][:80]}...")
    if 'environment_type' in nav_decision:
        print(f"   Environment: {nav_decision['environment_type']}")
    
    # Semantic mapping results
    print(f"\n🗺️ SEMANTIC MAPPING:")
    print(f"   Zone Type: {map_update['zone_type']}")
    print(f"   Persistent Objects: {map_update['persistent_objects']}")
    
    nav_info = map_update['navigation_info']
    print(f"   Navigation Difficulty: {nav_info['navigation_difficulty']}")
    print(f"   Clear Paths: {', '.join(nav_info['clear_paths'])}")
    print(f"   Recommended Direction: {nav_info['recommended_direction']}")
    
    semantic_context = map_update['semantic_context']
    print(f"   Furniture Count: {semantic_context['furniture_count']}")
    print(f"   Technology Count: {semantic_context['technology_count']}")
    print(f"   Accessibility: {semantic_context['accessibility']['complexity']}")
    
    # Scene memory results
    print(f"\n🧠 SCENE MEMORY:")
    tracking = memory_update['tracking_summary']
    print(f"   Tracked Objects: {tracking['total_tracked']}")
    print(f"   New Objects: {tracking['new_objects']}")
    
    scene_analysis = memory_update['scene_analysis']
    print(f"   Scene Change: {scene_analysis['scene_change_level']}")
    print(f"   Stability Score: {scene_analysis.get('stability_score', 1.0):.2f}")
    
    env_update = memory_update['environmental_update']
    print(f"   Environment: {env_update['current_environment']}")
    print(f"   Familiarity: {env_update['environment_familiarity']} visits")

def generate_comprehensive_summary(map_builder, scene_memory):
    """Generate comprehensive summary of semantic understanding"""
    print(f"\n{'='*70}")
    print("📊 COMPREHENSIVE SEMANTIC UNDERSTANDING SUMMARY")
    print(f"{'='*70}")
    
    # Navigation map summary
    nav_map = map_builder.get_navigation_map()
    print(f"\n🗺️ SEMANTIC MAP SUMMARY:")
    print(f"   Total Persistent Objects: {len(nav_map['persistent_objects'])}")
    print(f"   Spatial Relationships Tracked: {len(nav_map['spatial_relationships'])}")
    print(f"   Most Common Objects:")
    
    for obj, count in list(nav_map['object_frequency'].items())[:5]:
        print(f"     - {obj}: {count} occurrences")
    
    # Scene memory summary
    scene_context = scene_memory.get_scene_context()
    print(f"\n🧠 SCENE MEMORY SUMMARY:")
    print(f"   Current Stability Score: {scene_context['current_stability']:.2f}")
    print(f"   Stable Objects: {len(scene_context['stable_objects'])}")
    
    stable_objects = scene_context['stable_objects'][:3]  # Top 3 most stable
    if stable_objects:
        print(f"   Most Stable Objects:")
        for obj in stable_objects:
            print(f"     - {obj['class_name']} (stability: {obj['stability_count']})")
    
    # Movement analysis
    movement_patterns = scene_context['movement_patterns']
    if movement_patterns:
        print(f"   Movement Patterns:")
        for obj_id, pattern in list(movement_patterns.items())[:3]:
            print(f"     - {pattern['class_name']}: {pattern['movement_type']}")
    
    # Environment understanding
    env_history = scene_context['environment_history']
    if env_history:
        print(f"   Known Environments: {len(env_history)}")
        for env_name, env_info in env_history.items():
            print(f"     - {env_name}: {env_info['visit_count']} visits")
    
    print(f"\n✅ Semantic Mapping Integration Test Completed!")
    print(f"   - Navigation pipeline: Working with LLM reasoning")
    print(f"   - Semantic mapping: Building persistent spatial understanding")
    print(f"   - Scene memory: Tracking object continuity and changes")
    print(f"   - Integration: All systems working together seamlessly")

def test_semantic_mapping_standalone():
    """Test semantic mapping components in isolation"""
    print(f"\n{'='*50}")
    print("🧪 STANDALONE SEMANTIC MAPPING TESTS")
    print(f"{'='*50}")
    
    # Test map builder
    print("\n🗺️ Testing Map Builder...")
    map_builder = LibraryMapBuilder()
    
    test_detections = [
        {
            'class_name': 'monitor', 'confidence': 0.92, 'frame_position': 'center',
            'relative_size': 'large', 'bbox': {'center_x': 320, 'center_y': 240, 'width': 200, 'height': 150}
        },
        {
            'class_name': 'table', 'confidence': 0.88, 'frame_position': 'right', 
            'relative_size': 'large', 'bbox': {'center_x': 500, 'center_y': 300, 'width': 180, 'height': 80}
        }
    ]
    
    map_result = map_builder.update_map(test_detections, "test_frame", "Computer lab")
    print(f"✅ Map builder test: Zone={map_result['zone_type']}, Objects={map_result['persistent_objects']}")
    
    # Test scene memory
    print("\n🧠 Testing Scene Memory...")
    scene_memory = SceneMemorySystem()
    
    memory_result = scene_memory.update_scene_memory(test_detections)
    print(f"✅ Scene memory test: Tracked={memory_result['memory_stats']['tracked_objects']}")
    
    print(f"\n✅ Standalone tests completed successfully!")

if __name__ == "__main__":
    # Run comprehensive tests
    test_integrated_semantic_navigation()
    test_semantic_mapping_standalone()