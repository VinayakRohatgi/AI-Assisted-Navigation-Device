"""
Scene Memory System for Navigation
Maintains temporal understanding and object tracking
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
from datetime import datetime, timedelta
import cv2

class SceneMemorySystem:
    def __init__(self, memory_duration_minutes: int = 30, max_tracking_objects: int = 50):
        """
        Initialize scene memory system
        
        Args:
            memory_duration_minutes: How long to keep objects in memory
            max_tracking_objects: Maximum number of objects to track simultaneously
        """
        self.memory_duration = timedelta(minutes=memory_duration_minutes)
        self.max_tracking_objects = max_tracking_objects
        
        # Object tracking
        self.tracked_objects = {}  # object_id -> tracking info
        self.object_trajectories = defaultdict(list)  # object_id -> position history
        self.disappeared_objects = {}  # Recently disappeared objects
        
        # Scene understanding
        self.scene_transitions = deque(maxlen=100)  # Zone transition history
        self.environmental_memory = {}  # Long-term environment understanding
        
        # Temporal patterns
        self.object_appearance_patterns = defaultdict(list)  # When objects typically appear
        self.scene_stability_score = 1.0  # How stable is the current scene
        
        print("✅ Scene Memory System initialized")
    
    def update_scene_memory(self, detections: List[Dict], frame_timestamp: datetime = None) -> Dict:
        """
        Update scene memory with new detections
        
        Args:
            detections: Current frame detections
            frame_timestamp: When this frame was captured
            
        Returns:
            Memory update summary
        """
        if frame_timestamp is None:
            frame_timestamp = datetime.now()
        
        # Track object continuity
        tracking_summary = self._update_object_tracking(detections, frame_timestamp)
        
        # Analyze scene changes
        scene_analysis = self._analyze_scene_changes(detections, frame_timestamp)
        
        # Update environmental memory
        env_update = self._update_environmental_memory(detections, frame_timestamp)
        
        # Clean old memory
        self._cleanup_old_memory(frame_timestamp)
        
        return {
            'tracking_summary': tracking_summary,
            'scene_analysis': scene_analysis,
            'environmental_update': env_update,
            'memory_stats': self._get_memory_statistics()
        }
    
    def _update_object_tracking(self, detections: List[Dict], timestamp: datetime) -> Dict:
        """Update object tracking with new detections"""
        current_objects = {}
        new_objects = []
        matched_objects = []
        
        # Match detections to existing tracked objects
        for detection in detections:
            if detection['confidence'] < 0.6:  # Skip low confidence detections
                continue
            
            matched_id = self._find_matching_object(detection)
            
            if matched_id:
                # Update existing object
                self.tracked_objects[matched_id].update({
                    'last_seen': timestamp,
                    'confidence': detection['confidence'],
                    'bbox': detection['bbox'],
                    'frame_position': detection['frame_position'],
                    'stability_count': self.tracked_objects[matched_id]['stability_count'] + 1
                })
                
                # Track trajectory
                self.object_trajectories[matched_id].append({
                    'timestamp': timestamp,
                    'position': (detection['bbox']['center_x'], detection['bbox']['center_y']),
                    'bbox': detection['bbox']
                })
                
                matched_objects.append(matched_id)
                current_objects[matched_id] = detection
            else:
                # Create new tracked object
                new_id = f"{detection['class_name']}_{timestamp.strftime('%H%M%S%f')}"
                self.tracked_objects[new_id] = {
                    'class_name': detection['class_name'],
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'confidence': detection['confidence'],
                    'bbox': detection['bbox'],
                    'frame_position': detection['frame_position'],
                    'stability_count': 1,
                    'trajectory_length': 1
                }
                
                new_objects.append(new_id)
                current_objects[new_id] = detection
        
        # Mark objects that disappeared
        disappeared_objects = []
        for obj_id in list(self.tracked_objects.keys()):
            if obj_id not in current_objects:
                time_since_seen = timestamp - self.tracked_objects[obj_id]['last_seen']
                if time_since_seen > timedelta(seconds=10):  # Object gone for 10+ seconds
                    disappeared_objects.append(obj_id)
                    self.disappeared_objects[obj_id] = self.tracked_objects[obj_id]
                    del self.tracked_objects[obj_id]
        
        return {
            'new_objects': len(new_objects),
            'matched_objects': len(matched_objects),
            'disappeared_objects': len(disappeared_objects),
            'total_tracked': len(self.tracked_objects)
        }
    
    def _find_matching_object(self, detection: Dict) -> Optional[str]:
        """Find existing tracked object that matches this detection"""
        best_match = None
        best_similarity = 0.0
        
        for obj_id, tracked_obj in self.tracked_objects.items():
            # Only match same class
            if tracked_obj['class_name'] != detection['class_name']:
                continue
            
            # Calculate position similarity
            old_bbox = tracked_obj['bbox']
            new_bbox = detection['bbox']
            
            # Distance between centers
            dx = old_bbox['center_x'] - new_bbox['center_x']
            dy = old_bbox['center_y'] - new_bbox['center_y']
            distance = np.sqrt(dx**2 + dy**2)
            
            # Size similarity
            old_area = old_bbox['width'] * old_bbox['height']
            new_area = new_bbox['width'] * new_bbox['height']
            size_ratio = min(old_area, new_area) / max(old_area, new_area)
            
            # Combined similarity score
            distance_score = max(0, 1.0 - distance / 200)  # Normalize distance
            similarity = (distance_score * 0.7) + (size_ratio * 0.3)
            
            if similarity > 0.5 and similarity > best_similarity:
                best_similarity = similarity
                best_match = obj_id
        
        return best_match
    
    def _analyze_scene_changes(self, detections: List[Dict], timestamp: datetime) -> Dict:
        """Analyze how the scene has changed"""
        current_objects = {det['class_name'] for det in detections if det['confidence'] > 0.6}
        
        if not hasattr(self, '_previous_scene'):
            self._previous_scene = current_objects
            return {'scene_change_level': 'initial', 'new_scene': True}
        
        # Calculate scene change
        added_objects = current_objects - self._previous_scene
        removed_objects = self._previous_scene - current_objects
        common_objects = current_objects & self._previous_scene
        
        change_ratio = (len(added_objects) + len(removed_objects)) / max(len(current_objects), 1)
        
        if change_ratio == 0:
            change_level = 'stable'
        elif change_ratio < 0.3:
            change_level = 'minor'
        elif change_ratio < 0.7:
            change_level = 'moderate'
        else:
            change_level = 'major'
        
        # Update stability score
        if change_level == 'stable':
            self.scene_stability_score = min(1.0, self.scene_stability_score + 0.1)
        else:
            self.scene_stability_score = max(0.0, self.scene_stability_score - 0.2)
        
        self._previous_scene = current_objects
        
        return {
            'scene_change_level': change_level,
            'added_objects': list(added_objects),
            'removed_objects': list(removed_objects),
            'stability_score': self.scene_stability_score,
            'new_scene': change_ratio > 0.8
        }
    
    def _update_environmental_memory(self, detections: List[Dict], timestamp: datetime) -> Dict:
        """Update long-term environmental understanding"""
        # Identify current environment type
        detected_classes = [det['class_name'] for det in detections if det['confidence'] > 0.7]
        
        # Environment classification
        env_type = self._classify_environment(detected_classes)
        
        # Update environment memory
        if env_type not in self.environmental_memory:
            self.environmental_memory[env_type] = {
                'first_encountered': timestamp,
                'visit_count': 1,
                'typical_objects': defaultdict(int),
                'duration_spent': timedelta(0)
            }
        else:
            self.environmental_memory[env_type]['visit_count'] += 1
            
            if hasattr(self, '_last_env_timestamp'):
                time_diff = timestamp - self._last_env_timestamp
                if time_diff < timedelta(minutes=5):  # Reasonable time gap
                    self.environmental_memory[env_type]['duration_spent'] += time_diff
        
        # Update typical objects for this environment
        for class_name in detected_classes:
            self.environmental_memory[env_type]['typical_objects'][class_name] += 1
        
        self._last_env_timestamp = timestamp
        self._current_environment = env_type
        
        return {
            'current_environment': env_type,
            'environment_familiarity': self.environmental_memory[env_type]['visit_count'],
            'time_spent': str(self.environmental_memory[env_type]['duration_spent'])
        }
    
    def _classify_environment(self, detected_classes: List[str]) -> str:
        """Classify current environment based on detected objects"""
        # Environment signatures
        env_signatures = {
            'computer_lab': {'monitor': 2, 'office-chair': 1},
            'study_area': {'table': 1, 'office-chair': 1},
            'reading_area': {'books': 1},
            'presentation_room': {'whiteboard': 1},
            'corridor': {}  # Absence of furniture
        }
        
        object_counts = defaultdict(int)
        for obj in detected_classes:
            object_counts[obj] += 1
        
        best_match = 'general_area'
        best_score = 0
        
        for env_name, signature in env_signatures.items():
            score = 0
            for obj, min_count in signature.items():
                if object_counts[obj] >= min_count:
                    score += min_count
            
            # Bonus for exact matches
            if all(object_counts[obj] >= count for obj, count in signature.items()):
                score += len(signature)
            
            if score > best_score:
                best_score = score
                best_match = env_name
        
        return best_match
    
    def _cleanup_old_memory(self, current_time: datetime):
        """Remove old memory entries"""
        # Clean disappeared objects
        cutoff_time = current_time - self.memory_duration
        
        old_objects = [obj_id for obj_id, obj_info in self.disappeared_objects.items()
                      if obj_info['last_seen'] < cutoff_time]
        
        for obj_id in old_objects:
            del self.disappeared_objects[obj_id]
        
        # Clean trajectories
        for obj_id in list(self.object_trajectories.keys()):
            trajectory = self.object_trajectories[obj_id]
            # Keep only recent trajectory points
            recent_points = [point for point in trajectory 
                           if point['timestamp'] > cutoff_time]
            if recent_points:
                self.object_trajectories[obj_id] = recent_points
            else:
                del self.object_trajectories[obj_id]
        
        # Limit tracking if too many objects
        if len(self.tracked_objects) > self.max_tracking_objects:
            # Remove least stable objects
            sorted_objects = sorted(self.tracked_objects.items(),
                                  key=lambda x: x[1]['stability_count'])
            
            objects_to_remove = len(self.tracked_objects) - self.max_tracking_objects
            for i in range(objects_to_remove):
                obj_id = sorted_objects[i][0]
                del self.tracked_objects[obj_id]
    
    def _get_memory_statistics(self) -> Dict:
        """Get current memory system statistics"""
        return {
            'tracked_objects': len(self.tracked_objects),
            'disappeared_objects': len(self.disappeared_objects),
            'trajectories': len(self.object_trajectories),
            'environments_known': len(self.environmental_memory),
            'scene_stability': round(self.scene_stability_score, 2),
            'current_environment': getattr(self, '_current_environment', 'unknown')
        }
    
    def get_stable_objects(self, min_stability: int = 5) -> List[Dict]:
        """Get objects that have been stable for a minimum number of frames"""
        stable_objects = []
        
        for obj_id, obj_info in self.tracked_objects.items():
            if obj_info['stability_count'] >= min_stability:
                stable_objects.append({
                    'object_id': obj_id,
                    'class_name': obj_info['class_name'],
                    'stability_count': obj_info['stability_count'],
                    'confidence': obj_info['confidence'],
                    'duration_tracked': datetime.now() - obj_info['first_seen']
                })
        
        return sorted(stable_objects, key=lambda x: x['stability_count'], reverse=True)
    
    def get_movement_patterns(self) -> Dict:
        """Analyze movement patterns of tracked objects"""
        patterns = {}
        
        for obj_id, trajectory in self.object_trajectories.items():
            if len(trajectory) < 3:
                continue
            
            # Calculate movement statistics
            positions = [(point['position'][0], point['position'][1]) for point in trajectory]
            
            # Movement distance
            total_distance = 0
            for i in range(1, len(positions)):
                dx = positions[i][0] - positions[i-1][0]
                dy = positions[i][1] - positions[i-1][1]
                total_distance += np.sqrt(dx**2 + dy**2)
            
            # Movement type classification
            if total_distance < 20:
                movement_type = 'stationary'
            elif total_distance < 100:
                movement_type = 'minor_movement'
            else:
                movement_type = 'mobile'
            
            patterns[obj_id] = {
                'movement_type': movement_type,
                'total_distance': total_distance,
                'trajectory_points': len(trajectory),
                'class_name': self.tracked_objects.get(obj_id, {}).get('class_name', 'unknown')
            }
        
        return patterns
    
    def get_scene_context(self) -> Dict:
        """Get rich scene context from memory"""
        return {
            'current_stability': self.scene_stability_score,
            'stable_objects': self.get_stable_objects(),
            'movement_patterns': self.get_movement_patterns(),
            'environment_history': dict(self.environmental_memory),
            'memory_stats': self._get_memory_statistics()
        }


# Test scene memory system
if __name__ == "__main__":
    print("Testing Scene Memory System...")
    
    memory_system = SceneMemorySystem(memory_duration_minutes=5)
    
    # Simulate sequence of detections
    test_sequences = [
        # Frame 1: Initial scene
        [
            {'class_name': 'monitor', 'confidence': 0.9, 
             'bbox': {'center_x': 300, 'center_y': 200, 'width': 200, 'height': 150},
             'frame_position': 'center'},
            {'class_name': 'office-chair', 'confidence': 0.8,
             'bbox': {'center_x': 150, 'center_y': 350, 'width': 100, 'height': 120},
             'frame_position': 'bottom-left'}
        ],
        # Frame 2: Similar scene (slight movement)
        [
            {'class_name': 'monitor', 'confidence': 0.85,
             'bbox': {'center_x': 305, 'center_y': 205, 'width': 200, 'height': 150},
             'frame_position': 'center'},
            {'class_name': 'office-chair', 'confidence': 0.82,
             'bbox': {'center_x': 155, 'center_y': 355, 'width': 100, 'height': 120},
             'frame_position': 'bottom-left'}
        ],
        # Frame 3: New object appears
        [
            {'class_name': 'monitor', 'confidence': 0.88,
             'bbox': {'center_x': 300, 'center_y': 200, 'width': 200, 'height': 150},
             'frame_position': 'center'},
            {'class_name': 'office-chair', 'confidence': 0.79,
             'bbox': {'center_x': 150, 'center_y': 350, 'width': 100, 'height': 120},
             'frame_position': 'bottom-left'},
            {'class_name': 'table', 'confidence': 0.75,
             'bbox': {'center_x': 500, 'center_y': 300, 'width': 180, 'height': 80},
             'frame_position': 'right'}
        ]
    ]
    
    # Process test sequences
    for i, detections in enumerate(test_sequences):
        print(f"\n--- Processing Frame {i+1} ---")
        result = memory_system.update_scene_memory(detections)
        
        print(f"Tracking Summary: {result['tracking_summary']}")
        print(f"Scene Analysis: {result['scene_analysis']}")
        print(f"Memory Stats: {result['memory_stats']}")
    
    # Get final scene context
    scene_context = memory_system.get_scene_context()
    print(f"\n--- Final Scene Context ---")
    print(f"Stability Score: {scene_context['current_stability']}")
    print(f"Stable Objects: {len(scene_context['stable_objects'])}")
    print(f"Movement Patterns: {len(scene_context['movement_patterns'])}")
    
    print("\n✅ Scene memory system test completed!")