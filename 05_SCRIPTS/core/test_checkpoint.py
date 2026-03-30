"""
Checkpoint System Test
Tests checkpoint creation, resumption, and status reporting.
"""

import json
import sys
from pathlib import Path
from checkpoint_manager import get_checkpoint, CHECKPOINT_FILE

def reset_checkpoint():
    """Clean slate for testing."""
    cp = get_checkpoint()
    cp.reset()
    print("[RESET OK] Checkpoint reset")

def test_basic_workflow():
    """Test basic checkpoint workflow."""
    print("\n" + "="*70)
    print("TEST 1: Basic Step Progression")
    print("="*70)
    
    cp = get_checkpoint()
    
    # Simulate steps 1-3 completing successfully
    for i in range(1, 4):
        cp.mark_step_started(i, f"Test Step {i}")
        cp.mark_step_complete(i, f"Test Step {i}", 0)
        print(f"  Step {i}: completed in {cp.state['steps'][i]['duration_sec']}s")
    
    # Step 4 fails
    cp.mark_step_started(4, "Test Step 4")
    cp.mark_step_failed(4, "Test Step 4", 1, "Simulated failure for testing")
    print(f"  Step 4: FAILED (as expected)")
    
    # Check resume point
    resume = cp.get_resume_point()
    print(f"\n  Resume point: Step {resume}")
    assert resume == 4, f"Expected resume point 4, got {resume}"
    print("  [PASS] Resume point is correct")

def test_resume():
    """Test resume from failure."""
    print("\n" + "="*70)
    print("TEST 2: Resume from Failure")
    print("="*70)
    
    cp = get_checkpoint()
    
    # Check current state
    completed = cp.get_completed_steps()
    resume = cp.get_resume_point()
    
    print(f"  Completed steps: {sorted(completed)}")
    print(f"  Resume point: {resume}")
    
    assert 1 in completed, "Step 1 should be completed"
    assert 2 in completed, "Step 2 should be completed"
    assert 3 in completed, "Step 3 should be completed"
    assert 4 not in completed, "Step 4 should not be completed"
    
    # Now "fix" the error and resume from step 4
    print("\n  Resuming from step 4...")
    cp.mark_step_started(4, "Test Step 4")
    cp.mark_step_complete(4, "Test Step 4", 0)
    print(f"  Step 4: now completed in {cp.state['steps'][4]['duration_sec']}s")
    
    # Steps 5-6 continue
    for i in range(5, 7):
        cp.mark_step_started(i, f"Test Step {i}")
        cp.mark_step_complete(i, f"Test Step {i}", 0)
        print(f"  Step {i}: completed in {cp.state['steps'][i]['duration_sec']}s")
    
    # All should be completed
    completed = sorted(cp.get_completed_steps())
    resume = cp.get_resume_point()
    
    print(f"\n  All completed steps: {completed}")
    print(f"  Resume point: {resume}")
    assert resume is None, "All steps should be completed"
    print("  [PASS] Resume functionality works")

def test_reporting():
    """Test checkpoint reporting."""
    print("\n" + "="*70)
    print("TEST 3: Checkpoint Reporting")
    print("="*70)
    
    cp = get_checkpoint()
    report = cp.report()
    print(report)
    
    # Verify report contains expected info
    assert "Completed: 6/6 steps" in report, "Report should show 6/6 completion"
    assert "[" in report and "]" in report, "Report should show status markers"
    print("\n  [PASS] Report generated successfully")

def test_checkpoint_file():
    """Verify checkpoint file structure."""
    print("\n" + "="*70)
    print("TEST 4: Checkpoint File Structure")
    print("="*70)
    
    # Read raw checkpoint file
    data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    
    print(f"  File: {CHECKPOINT_FILE}")
    print(f"  Version: {data['pipeline_version']}")
    print(f"  Steps recorded: {len(data['steps'])}")
    print(f"  Status: {data['overall_status']}")
    
    # Verify structure
    assert "pipeline_version" in data
    assert "created_at" in data
    assert "last_updated" in data
    assert "overall_status" in data
    assert "steps" in data
    
    # Verify step structure
    for step_id, step in data["steps"].items():
        assert "name" in step
        assert "status" in step
        assert "start_time" in step
        assert "end_time" in step
        assert "duration_sec" in step
        assert "exit_code" in step
        assert "error" in step
    
    print("  [PASS] Checkpoint file structure is valid")

def test_reset():
    """Test checkpoint reset."""
    print("\n" + "="*70)
    print("TEST 5: Checkpoint Reset")
    print("="*70)
    
    cp = get_checkpoint()
    original_steps = len(cp.state["steps"])
    print(f"  Before reset: {original_steps} steps recorded")
    
    cp.reset()
    print("  Running reset...")
    
    cp2 = get_checkpoint()
    reset_steps = len(cp2.state["steps"])
    print(f"  After reset: {reset_steps} steps recorded")
    
    assert reset_steps == 0, "Steps should be cleared on reset"
    print("  [PASS] Reset works correctly")

def main():
    """Run all tests."""
    print("\n" + "#"*70)
    print("# CHECKPOINT SYSTEM TEST SUITE")
    print("#"*70)
    
    try:
        reset_checkpoint()
        test_basic_workflow()
        test_resume()
        test_reporting()
        test_checkpoint_file()
        test_reset()
        
        print("\n" + "="*70)
        print("[SUCCESS] ALL TESTS PASSED")
        print("="*70 + "\n")
        return 0
    
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
