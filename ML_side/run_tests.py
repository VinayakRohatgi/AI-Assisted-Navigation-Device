"""
Main Test Runner for AI-Assisted Navigation Device
Runs comprehensive tests for all system components
"""

def main():
    """Run all system tests"""
    print("🧪 AI-ASSISTED NAVIGATION DEVICE - TEST SUITE")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Test semantic mapping
        print("\n🗺️ TESTING SEMANTIC MAPPING SYSTEM")
        print("-" * 40)
        
        from test_semantic_mapping import test_integrated_semantic_navigation
        semantic_result = test_integrated_semantic_navigation()
        test_results.append(("Semantic Mapping", semantic_result))
        
        # Test pathfinding
        print("\n🚀 TESTING PATHFINDING SYSTEM") 
        print("-" * 40)
        
        from test_pathfinding import test_astar_pathfinding, test_algorithm_comparison, test_integrated_navigation_planner
        
        astar_result = test_astar_pathfinding()
        test_results.append(("A* Pathfinding", astar_result))
        
        comparison_result = test_algorithm_comparison()
        test_results.append(("Algorithm Comparison", comparison_result))
        
        integration_result = test_integrated_navigation_planner()
        test_results.append(("Navigation Integration", integration_result))
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return False
    
    # Results summary
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System ready for deployment.")
        return True
    else:
        print("⚠️ Some tests failed. Check system components.")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)