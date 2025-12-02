"""
Advanced LLM Integration for Navigation Reasoning
Supports OpenAI API, local models, and fallback reasoning
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
import time

class LLMNavigationReasoner:
    def __init__(self, model_type: str = "openai", api_key: str = None, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize LLM reasoning engine
        
        Args:
            model_type: "openai", "local", or "ollama"
            api_key: API key for OpenAI (if using OpenAI)
            model_name: Model name to use
        """
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        # Set up API endpoints
        if model_type == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        elif model_type == "ollama":
            self.api_url = "http://localhost:11434/api/generate"
            self.headers = {"Content-Type": "application/json"}
        elif model_type == "local":
            # For local models (you'd implement this based on your setup)
            self.api_url = "http://localhost:8000/generate"
            self.headers = {"Content-Type": "application/json"}
        
        # Conversation history for context
        self.conversation_history = []
        
        print(f"LLM Navigation Reasoner initialized: {model_type} - {model_name}")
        
    def reason_about_navigation(self, detections: List[Dict], spatial_context: Dict, 
                               user_intent: str = "Navigate safely through the library",
                               current_location: str = "Unknown") -> Dict[str, str]:
        """
        Use LLM to reason about navigation decisions
        
        Returns structured navigation guidance
        """
        
        # Build comprehensive reasoning prompt
        prompt = self._build_navigation_prompt(detections, spatial_context, user_intent, current_location)
        
        # Try LLM reasoning first
        try:
            if self.model_type == "openai" and self.api_key:
                response = self._query_openai(prompt)
            elif self.model_type == "ollama":
                response = self._query_ollama(prompt)
            elif self.model_type == "local":
                response = self._query_local_model(prompt)
            else:
                print("No valid LLM configuration, using fallback reasoning")
                response = None
                
            if response:
                return self._parse_llm_response(response)
                
        except Exception as e:
            print(f"LLM reasoning failed: {e}")
            print("Falling back to rule-based reasoning")
        
        # Fallback to advanced rule-based reasoning
        return self._advanced_fallback_reasoning(detections, spatial_context, user_intent)
    
    def _build_navigation_prompt(self, detections: List[Dict], spatial_context: Dict, 
                                user_intent: str, current_location: str) -> str:
        """Build comprehensive navigation reasoning prompt"""
        
        # Scene description
        scene_desc = self._describe_scene(detections, spatial_context)
        
        # Spatial relationships
        spatial_desc = self._describe_spatial_relationships(spatial_context)
        
        # Context and history
        context_desc = self._describe_context(user_intent, current_location)
        
        # Navigation prompt
        prompt = f"""You are an advanced AI navigation assistant helping a visually impaired person navigate through a university library. You provide safe, clear, and helpful navigation guidance.

CURRENT SCENE ANALYSIS:
{scene_desc}

SPATIAL RELATIONSHIPS:
{spatial_desc}

NAVIGATION CONTEXT:
{context_desc}

PREVIOUS CONTEXT:
{self._get_recent_context()}

TASK: Provide intelligent navigation guidance considering:

1. SAFETY: Highest priority - avoid collisions and hazards
2. EFFICIENCY: Suggest optimal paths to destination
3. CLARITY: Use simple, directional language with landmarks
4. ACCESSIBILITY: Account for visual impairment needs
5. CONTEXT: Consider the library environment and user intent

RESPOND in this EXACT format:
DIRECTION: [One clear directional instruction in simple language]
REASONING: [Brief explanation of why this direction is recommended]
OBSTACLES: [Comma-separated list of objects to avoid]
LANDMARKS: [Comma-separated list of reference objects for orientation]
SAFETY_LEVEL: [Low/Medium/High - current risk assessment]
NEXT_ACTION: [What the user should do after following this direction]
ENVIRONMENT_TYPE: [Description of current area - e.g., "reading area", "computer lab", "corridor"]

Example response:
DIRECTION: Move slightly to your left to avoid the office chair, then continue forward
REASONING: Chair is blocking direct path but left side appears clear
OBSTACLES: office-chair
LANDMARKS: table on your right, monitor ahead
SAFETY_LEVEL: Medium
NEXT_ACTION: After passing chair, continue straight toward the reading area
ENVIRONMENT_TYPE: study area with furniture"""

        return prompt
    
    def _describe_scene(self, detections: List[Dict], spatial_context: Dict) -> str:
        """Create natural language scene description"""
        if not detections:
            return "Empty scene with no objects currently detected."
        
        desc = f"Scene contains {len(detections)} objects in a {spatial_context['scene_density']} environment:\n"
        
        # Sort by confidence for better description
        sorted_detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        for i, det in enumerate(sorted_detections):
            desc += f"{i+1}. {det['class_name'].upper()} - "
            desc += f"Confidence: {det['confidence']:.2f}, "
            desc += f"Size: {det['relative_size']}, "
            desc += f"Position: {det['frame_position']}\n"
        
        return desc
    
    def _describe_spatial_relationships(self, spatial_context: Dict) -> str:
        """Describe spatial relationships between objects"""
        relationships = spatial_context.get('relationships', [])
        
        if not relationships:
            return "No clear spatial relationships detected between objects."
        
        desc = f"Found {len(relationships)} spatial relationships:\n"
        
        # Show most important relationships
        for i, rel in enumerate(relationships[:5]):  # Top 5 relationships
            desc += f"{i+1}. {rel['object1']} is {rel['relationship']} {rel['object2']}"
            if 'distance' in rel:
                desc += f" (distance: {rel['distance']:.0f})"
            desc += "\n"
        
        return desc
    
    def _describe_context(self, user_intent: str, current_location: str) -> str:
        """Describe navigation context and user intent"""
        context = f"User Intent: {user_intent}\n"
        context += f"Current Location: {current_location}\n"
        context += f"Environment: University library with study areas, computer labs, and reading spaces\n"
        context += f"User Needs: Clear audio guidance, obstacle avoidance, landmark-based directions"
        
        return context
    
    def _get_recent_context(self) -> str:
        """Get recent conversation context"""
        if not self.conversation_history:
            return "No previous navigation history"
        
        recent = self.conversation_history[-3:]  # Last 3 interactions
        context = "Recent navigation decisions:\n"
        
        for i, hist in enumerate(recent):
            context += f"{i+1}. {hist.get('direction', 'Unknown direction')}\n"
        
        return context
    
    def _query_openai(self, prompt: str) -> str:
        """Query OpenAI API"""
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert navigation assistant for visually impaired users. Provide clear, safe, and helpful navigation guidance in the exact format requested."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _query_ollama(self, prompt: str) -> str:
        """Query local Ollama model"""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result['response']
    
    def _query_local_model(self, prompt: str) -> str:
        """Query local model API"""
        payload = {
            "prompt": prompt,
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', result.get('text', ''))
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, str]:
        """Parse structured LLM response"""
        result = {
            'direction': 'Continue forward with caution',
            'reasoning': 'Default navigation guidance',
            'obstacles': 'None detected',
            'landmarks': 'None available',
            'safety_level': 'Medium',
            'next_action': 'Continue monitoring surroundings',
            'environment_type': 'General area'
        }
        
        # Parse the structured response
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'direction' in key:
                    result['direction'] = value
                elif 'reasoning' in key:
                    result['reasoning'] = value
                elif 'obstacle' in key:
                    result['obstacles'] = value
                elif 'landmark' in key:
                    result['landmarks'] = value
                elif 'safety' in key:
                    result['safety_level'] = value
                elif 'next' in key or 'action' in key:
                    result['next_action'] = value
                elif 'environment' in key or 'type' in key:
                    result['environment_type'] = value
        
        # Store in conversation history
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'direction': result['direction'],
            'reasoning': result['reasoning'],
            'safety_level': result['safety_level']
        })
        
        # Keep only recent history
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        return result
    
    def _advanced_fallback_reasoning(self, detections: List[Dict], spatial_context: Dict, user_intent: str) -> Dict[str, str]:
        """Advanced rule-based reasoning when LLM is unavailable"""
        
        if not detections:
            return {
                'direction': 'No obstacles detected, you may proceed forward carefully',
                'reasoning': 'Clear path with no visible objects',
                'obstacles': 'None',
                'landmarks': 'None',
                'safety_level': 'Low',
                'next_action': 'Continue forward and listen for audio cues',
                'environment_type': 'Open area'
            }
        
        # Analyze object positions and risks
        center_objects = [d for d in detections if 'center' in d.get('frame_position', '')]
        left_objects = [d for d in detections if 'left' in d.get('frame_position', '')]
        right_objects = [d for d in detections if 'right' in d.get('frame_position', '')]
        
        # Determine navigation strategy
        if center_objects:
            primary_obstacle = max(center_objects, key=lambda x: x['confidence'])
            
            # Choose best avoidance direction
            if len(left_objects) < len(right_objects):
                direction = f"Move to your left to avoid the {primary_obstacle['class_name']}, then continue forward"
                next_action = "After moving left, proceed straight"
            else:
                direction = f"Move to your right to avoid the {primary_obstacle['class_name']}, then continue forward"
                next_action = "After moving right, proceed straight"
                
            safety_level = "Medium"
            reasoning = f"Obstacle detected in direct path, safer route available"
            
        else:
            direction = "Path ahead appears clear, proceed forward"
            reasoning = "No obstacles in direct path"
            safety_level = "Low"
            next_action = "Continue straight and monitor for new obstacles"
        
        # Identify landmarks
        high_conf_objects = [d['class_name'] for d in detections if d['confidence'] > 0.7]
        landmarks = ', '.join(high_conf_objects[:3]) if high_conf_objects else 'None'
        
        # Identify obstacles to avoid
        obstacles = [d['class_name'] for d in center_objects]
        obstacles_str = ', '.join(obstacles) if obstacles else 'None in direct path'
        
        # Determine environment type
        object_types = [d['class_name'] for d in detections]
        if 'monitor' in object_types and len([o for o in object_types if o == 'monitor']) >= 2:
            env_type = 'Computer lab'
        elif 'books' in object_types or 'book' in object_types:
            env_type = 'Reading area'
        elif 'table' in object_types and 'office-chair' in object_types:
            env_type = 'Study area'
        elif 'whiteboard' in object_types:
            env_type = 'Presentation area'
        else:
            env_type = 'General library area'
        
        return {
            'direction': direction,
            'reasoning': reasoning,
            'obstacles': obstacles_str,
            'landmarks': landmarks,
            'safety_level': safety_level,
            'next_action': next_action,
            'environment_type': env_type
        }

# Test the LLM reasoner
if __name__ == "__main__":
    print("Testing LLM Navigation Reasoner...")
    
    # Initialize reasoner (will fallback to rule-based if no API key)
    reasoner = LLMNavigationReasoner(model_type="openai")
    
    # Test data
    test_detections = [
        {
            'class_name': 'office-chair',
            'confidence': 0.85,
            'frame_position': 'center',
            'relative_size': 'medium'
        },
        {
            'class_name': 'table', 
            'confidence': 0.92,
            'frame_position': 'right',
            'relative_size': 'large'
        }
    ]
    
    test_spatial_context = {
        'scene_density': 'moderate',
        'relationships': [
            {'object1': 'office-chair', 'object2': 'table', 'relationship': 'left of', 'distance': 120}
        ],
        'object_count': 2
    }
    
    # Get navigation decision
    result = reasoner.reason_about_navigation(
        test_detections,
        test_spatial_context,
        "Find a place to sit and study",
        "Library main area"
    )
    
    print("\nNavigation Decision:")
    print("="*50)
    for key, value in result.items():
        print(f"{key.upper()}: {value}")