"""
Library Semantic Map Builder
Creates and maintains spatial understanding of library environments
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
import cv2
from collections import defaultdict, deque
import os

class LibraryMapBuilder:
    def __init__(self, confidence_threshold: float = 0.7, memory_size: int = 100):
        """
        Initialize the library semantic map builder
        
        Args:
            confidence_threshold: Minimum confidence for object persistence
            memory_size: Number of recent frames to remember
        """
        self.confidence_threshold = confidence_threshold
        self.memory_size = memory_size
        
        # Semantic map storage
        self.persistent_objects = {}  # Long-term object memory
        self.room_zones = {}  # Identified areas/zones
        self.navigation_graph = {}  # Pathways between areas
        self.object_frequency = defaultdict(int)  # Object occurrence tracking
        
        # Temporal memory for tracking
        self.recent_frames = deque(maxlen=memory_size)
        self.object_tracking_history = defaultdict(list)
        
        # Library-specific semantic understanding
        self.library_zones = {
            'study_area': ['table', 'office-chair', 'books'],
            'computer_lab': ['monitor', 'office-chair', 'table'],
            'reading_area': ['books', 'office-chair'],
            'presentation_area': ['whiteboard', 'office-chair', 'table'],
            'circulation_area': ['books', 'table'],
            'corridor': []  # Identified by absence of furniture
        }
        
        # Spatial relationships for mapping
        self.spatial_relationships = []
        self.landmark_objects = {}
        
        print("✅ Library Semantic Map Builder initialized")
    
    def update_map(self, detections: List[Dict], frame_id: str = None, 
                   location_hint: str = None) -> Dict:
        """
        Update semantic map with new detection data
        
        Args:
            detections: YOLO detection results
            frame_id: Unique frame identifier
            location_hint: Optional location context
            
        Returns:
            Updated map information
        """
        if frame_id is None:
            frame_id = f"frame_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Store frame data
        frame_data = {
            'frame_id': frame_id,
            'timestamp': datetime.now(),
            'detections': detections,
            'location_hint': location_hint
        }
        self.recent_frames.append(frame_data)
        
        # Update persistent objects
        self._update_persistent_objects(detections, frame_id)
        
        # Analyze spatial relationships
        self._analyze_spatial_context(detections, frame_id)
        
        # Identify room/zone type
        zone_type = self._classify_environment_zone(detections)
        
        # Update navigation understanding
        navigation_info = self._update_navigation_context(detections, zone_type)
        
        # Build semantic understanding
        semantic_context = self._build_semantic_context(detections, zone_type)
        
        return {
            'frame_id': frame_id,
            'zone_type': zone_type,
            'persistent_objects': len(self.persistent_objects),
            'navigation_info': navigation_info,
            'semantic_context': semantic_context,
            'spatial_memory': self._get_spatial_memory_summary()
        }
    
    def _update_persistent_objects(self, detections: List[Dict], frame_id: str):
        """Update long-term object memory with high-confidence detections"""
        for detection in detections:
            if detection['confidence'] >= self.confidence_threshold:
                obj_key = self._generate_object_key(detection)
                
                if obj_key in self.persistent_objects:
                    # Update existing object
                    self.persistent_objects[obj_key]['confidence'] = max(
                        self.persistent_objects[obj_key]['confidence'],
                        detection['confidence']
                    )
                    self.persistent_objects[obj_key]['last_seen'] = datetime.now()
                    self.persistent_objects[obj_key]['frequency'] += 1
                else:
                    # Add new persistent object
                    self.persistent_objects[obj_key] = {
                        'class_name': detection['class_name'],
                        'position': detection['frame_position'],
                        'confidence': detection['confidence'],
                        'first_seen': datetime.now(),
                        'last_seen': datetime.now(),
                        'frequency': 1,
                        'bbox_history': [detection['bbox']],
                        'is_landmark': self._is_landmark_object(detection)
                    }
                
                # Update frequency tracking
                self.object_frequency[detection['class_name']] += 1
                
                # Track object movement history
                self.object_tracking_history[obj_key].append({
                    'frame_id': frame_id,
                    'bbox': detection['bbox'],
                    'position': detection['frame_position'],
                    'timestamp': datetime.now()
                })
    
    def _generate_object_key(self, detection: Dict) -> str:
        """Generate unique key for object tracking"""
        # Use class name and approximate position for clustering
        pos = detection['frame_position']
        bbox = detection['bbox']
        center_x = int(bbox['center_x'] // 50) * 50  # Round to nearest 50 pixels
        center_y = int(bbox['center_y'] // 50) * 50
        
        return f"{detection['class_name']}_{pos}_{center_x}_{center_y}"
    
    def _is_landmark_object(self, detection: Dict) -> bool:
        """Determine if object should be considered a landmark"""
        # High confidence, large objects make good landmarks
        is_large = detection.get('relative_size') == 'large'
        is_high_confidence = detection['confidence'] > 0.8
        is_landmark_class = detection['class_name'] in ['monitor', 'whiteboard', 'table']
        
        return is_high_confidence and (is_large or is_landmark_class)
    
    def _analyze_spatial_context(self, detections: List[Dict], frame_id: str):
        """Analyze spatial relationships and context"""
        if len(detections) < 2:
            return
        
        # Calculate object relationships
        relationships = []
        for i, det1 in enumerate(detections):
            for j, det2 in enumerate(detections[i+1:], i+1):
                rel_info = self._calculate_relationship(det1, det2)
                relationships.append(rel_info)
        
        # Store spatial relationships
        self.spatial_relationships.extend(relationships)
        
        # Keep only recent relationships (avoid memory explosion)
        if len(self.spatial_relationships) > 1000:
            self.spatial_relationships = self.spatial_relationships[-500:]
    
    def _calculate_relationship(self, obj1: Dict, obj2: Dict) -> Dict:
        """Calculate detailed spatial relationship between two objects"""
        bbox1, bbox2 = obj1['bbox'], obj2['bbox']
        
        # Distance calculation
        dx = bbox1['center_x'] - bbox2['center_x']
        dy = bbox1['center_y'] - bbox2['center_y']
        distance = np.sqrt(dx**2 + dy**2)
        
        # Direction calculation
        if abs(dx) > abs(dy):
            direction = "left_of" if dx > 0 else "right_of"
        else:
            direction = "above" if dy > 0 else "below"
        
        # Proximity assessment
        if distance < 100:
            proximity = "close"
        elif distance < 200:
            proximity = "moderate"
        else:
            proximity = "far"
        
        return {
            'object1': obj1['class_name'],
            'object2': obj2['class_name'],
            'relationship': direction,
            'distance': float(distance),
            'proximity': proximity,
            'confidence': (obj1['confidence'] + obj2['confidence']) / 2
        }
    
    def _classify_environment_zone(self, detections: List[Dict]) -> str:
        """Classify the current environment zone based on objects"""
        detected_classes = [det['class_name'] for det in detections 
                          if det['confidence'] > self.confidence_threshold]
        
        # Score each zone type
        zone_scores = {}
        for zone_name, required_objects in self.library_zones.items():
            score = 0
            for req_obj in required_objects:
                if req_obj in detected_classes:
                    score += detected_classes.count(req_obj)
            
            # Bonus for complete sets
            if all(obj in detected_classes for obj in required_objects):
                score += len(required_objects)
            
            zone_scores[zone_name] = score
        
        # Return highest scoring zone
        if zone_scores:
            best_zone = max(zone_scores, key=zone_scores.get)
            if zone_scores[best_zone] > 0:
                return best_zone
        
        return "general_area"
    
    def _update_navigation_context(self, detections: List[Dict], zone_type: str) -> Dict:
        """Update navigation context and pathways"""
        # Identify potential pathways (areas with fewer obstacles)
        obstacles = [det for det in detections if det['frame_position'] == 'center']
        clear_paths = self._identify_clear_paths(detections)
        
        # Update navigation graph
        nav_info = {
            'current_zone': zone_type,
            'obstacle_density': len(obstacles),
            'clear_paths': clear_paths,
            'navigation_difficulty': self._assess_navigation_difficulty(detections),
            'recommended_direction': self._get_recommended_direction(detections)
        }
        
        return nav_info
    
    def _identify_clear_paths(self, detections: List[Dict]) -> List[str]:
        """Identify clear movement paths"""
        occupied_positions = {det['frame_position'] for det in detections}
        
        all_positions = {'left', 'center', 'right', 'top-left', 'top-center', 
                        'top-right', 'bottom-left', 'bottom-center', 'bottom-right'}
        
        clear_positions = all_positions - occupied_positions
        
        # Prioritize main movement directions
        clear_paths = []
        if 'center' not in occupied_positions:
            clear_paths.append('forward')
        if 'left' not in occupied_positions and 'center-left' not in occupied_positions:
            clear_paths.append('left')
        if 'right' not in occupied_positions and 'center-right' not in occupied_positions:
            clear_paths.append('right')
        
        return clear_paths
    
    def _assess_navigation_difficulty(self, detections: List[Dict]) -> str:
        """Assess navigation difficulty based on object density and layout"""
        if len(detections) == 0:
            return "easy"
        elif len(detections) <= 2:
            return "moderate"
        elif len(detections) <= 5:
            return "challenging"
        else:
            return "difficult"
    
    def _get_recommended_direction(self, detections: List[Dict]) -> str:
        """Get recommended movement direction"""
        clear_paths = self._identify_clear_paths(detections)
        
        if 'forward' in clear_paths:
            return "continue_forward"
        elif 'left' in clear_paths:
            return "move_left"
        elif 'right' in clear_paths:
            return "move_right"
        else:
            return "proceed_carefully"
    
    def _build_semantic_context(self, detections: List[Dict], zone_type: str) -> Dict:
        """Build rich semantic understanding of the current scene"""
        # Object categorization
        furniture = [d for d in detections if d['class_name'] in ['table', 'office-chair']]
        technology = [d for d in detections if d['class_name'] in ['monitor', 'tv']]
        educational = [d for d in detections if d['class_name'] in ['books', 'whiteboard']]
        
        # Scene analysis
        scene_density = len(detections)
        predominant_objects = self._get_predominant_objects(detections)
        
        # Accessibility assessment
        accessibility = self._assess_accessibility(detections)
        
        return {
            'zone_type': zone_type,
            'furniture_count': len(furniture),
            'technology_count': len(technology),
            'educational_count': len(educational),
            'scene_density': scene_density,
            'predominant_objects': predominant_objects,
            'accessibility': accessibility,
            'landmark_objects': [d['class_name'] for d in detections 
                               if self._is_landmark_object(d)]
        }
    
    def _get_predominant_objects(self, detections: List[Dict]) -> List[str]:
        """Identify most common objects in the scene"""
        object_counts = defaultdict(int)
        for det in detections:
            object_counts[det['class_name']] += 1
        
        # Return top 3 most common objects
        return sorted(object_counts.keys(), key=object_counts.get, reverse=True)[:3]
    
    def _assess_accessibility(self, detections: List[Dict]) -> Dict:
        """Assess accessibility of the current area"""
        center_obstacles = [d for d in detections if 'center' in d['frame_position']]
        
        return {
            'mobility_friendly': len(center_obstacles) == 0,
            'obstacle_count': len(center_obstacles),
            'clear_width': self._estimate_clear_width(detections),
            'complexity': "low" if len(detections) <= 3 else "high"
        }
    
    def _estimate_clear_width(self, detections: List[Dict]) -> str:
        """Estimate available clear width for movement"""
        left_occupied = any('left' in d['frame_position'] for d in detections)
        right_occupied = any('right' in d['frame_position'] for d in detections)
        
        if not left_occupied and not right_occupied:
            return "wide"
        elif left_occupied and right_occupied:
            return "narrow"
        else:
            return "moderate"
    
    def _get_spatial_memory_summary(self) -> Dict:
        """Get summary of accumulated spatial memory"""
        return {
            'persistent_objects': len(self.persistent_objects),
            'tracked_relationships': len(self.spatial_relationships),
            'memory_frames': len(self.recent_frames),
            'most_common_objects': dict(sorted(self.object_frequency.items(), 
                                             key=lambda x: x[1], reverse=True)[:5]),
            'landmark_count': sum(1 for obj in self.persistent_objects.values() 
                                if obj.get('is_landmark', False))
        }
    
    def get_navigation_map(self) -> Dict:
        """Generate comprehensive navigation map"""
        return {
            'persistent_objects': self.persistent_objects,
            'spatial_relationships': self.spatial_relationships[-50:],  # Recent relationships
            'object_frequency': dict(self.object_frequency),
            'memory_summary': self._get_spatial_memory_summary(),
            'last_updated': datetime.now().isoformat()
        }
    
    def save_map(self, filepath: str):
        """Save semantic map to file"""
        map_data = self.get_navigation_map()
        
        # Convert datetime objects to strings for JSON serialization
        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(filepath, 'w') as f:
            json.dump(map_data, f, indent=2, default=datetime_converter)
        
        print(f"✅ Semantic map saved to {filepath}")
    
    def load_map(self, filepath: str):
        """Load semantic map from file"""
        if not os.path.exists(filepath):
            print(f"❌ Map file not found: {filepath}")
            return
        
        with open(filepath, 'r') as f:
            map_data = json.load(f)
        
        # Restore data structures
        self.persistent_objects = map_data.get('persistent_objects', {})
        self.spatial_relationships = map_data.get('spatial_relationships', [])
        self.object_frequency = defaultdict(int, map_data.get('object_frequency', {}))
        
        print(f"✅ Semantic map loaded from {filepath}")


# Test the semantic map builder
if __name__ == "__main__":
    print("Testing Library Semantic Map Builder...")
    
    # Initialize map builder
    map_builder = LibraryMapBuilder()
    
    # Test with sample detection data
    test_detections = [
        {
            'class_name': 'monitor',
            'confidence': 0.92,
            'frame_position': 'center',
            'relative_size': 'large',
            'bbox': {'center_x': 320, 'center_y': 240, 'width': 200, 'height': 150}
        },
        {
            'class_name': 'office-chair',
            'confidence': 0.85,
            'frame_position': 'bottom-left',
            'relative_size': 'medium',
            'bbox': {'center_x': 150, 'center_y': 400, 'width': 100, 'height': 120}
        },
        {
            'class_name': 'table',
            'confidence': 0.88,
            'frame_position': 'right',
            'relative_size': 'large',
            'bbox': {'center_x': 500, 'center_y': 300, 'width': 180, 'height': 80}
        }
    ]
    
    # Update map with test data
    result = map_builder.update_map(test_detections, "test_frame_1", "Computer lab")
    
    print("\nMap Update Result:")
    print("="*50)
    for key, value in result.items():
        print(f"{key}: {value}")
    
    # Get full navigation map
    nav_map = map_builder.get_navigation_map()
    print(f"\nNavigation Map Summary:")
    print(f"Persistent Objects: {len(nav_map['persistent_objects'])}")
    print(f"Spatial Relationships: {len(nav_map['spatial_relationships'])}")
    print(f"Object Frequency: {nav_map['object_frequency']}")
    
    print("\n✅ Semantic mapping test completed!")