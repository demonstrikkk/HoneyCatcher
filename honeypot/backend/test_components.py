#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, ".")

from db.mongo import MongoDB
from services.scam_detector import scam_detector
from agents.graph import agent_system

async def test_system():
    print("Testing system components...")
    
    # 1. Test MongoDB
    print("\n1. Testing MongoDB connection...")
    try:
        await MongoDB.connect()
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB failed: {e}")
        return
    
    # 2. Test Scam Detector
    print("\n2. Testing Scam Detector...")
    try:
        result = await scam_detector.analyze("Your bank account will be blocked", [])
        print(f"✅ Scam Detector: {result}")
    except Exception as e:
        print(f"❌ Scam Detector failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Test Agent
    print("\n3. Testing Agent System...")
    try:
        history = [{"role": "scammer", "content": "Hello, your account is blocked"}]
        reply = await agent_system.run(history)
        print(f"✅ Agent reply: {reply}")
    except Exception as e:
        print(f"❌ Agent failed: {e}")
        import traceback
        traceback.print_exc()
    
    await MongoDB.close()
    print("\n✅ All tests complete")

if __name__ == "__main__":
    asyncio.run(test_system())
