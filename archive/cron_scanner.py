#!/usr/bin/env python3
"""
MT5 Low-Token Cron Scanner
Minimal reporting - triggers LLM only on significant events
"""
import subprocess
import sys
import os

# Add mt5_trader to path
sys.path.insert(0, r"C:\Users\Claw\.openclaw\workspace\mt5_trader")

from connector_optimized import OptimizedConnector

def main():
    """Run optimized scan with minimal token usage"""
    connector = OptimizedConnector()
    result = connector.run(verbose=False)
    
    if "error" in result:
        # Critical error - need LLM attention
        print(f"🚨 MT5 ERROR: {result['error']}")
        print("[LLM_REVIEW_REQUIRED]")
        return 1
    
    # Print minimal report
    print(result["report"])
    
    # Determine if LLM review needed
    if result.get("needs_llm"):
        print(f"\n[LLM_ALERT: {result.get('llm_reason', 'Review needed')}]")
        
        # Exit code 2 signals LLM review needed
        # This can be caught by the calling script
        return 2
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
