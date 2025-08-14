"""
Migration script to convert single-session data to multi-session format
Run this if you have existing chat data from the old single-session system
"""

from pymongo import MongoClient
from datetime import datetime
import sys
from config import config

def migrate_single_to_multi_session():
    """Migrate from single session to multi-session format"""
    print("=" * 60)
    print("Chat History Migration Tool")
    print("Converting single-session to multi-session format")
    print("=" * 60)
    
    try:
        # Validate configuration
        config.validate_required_keys()
        print("✅ Configuration validation successful")
        
        # Connect to MongoDB using config
        client = MongoClient(config.MONGODB_URI)
        db = client[config.DATABASE_NAME]
        collection = db["simple_chats"]
        
        # Check for old single-session data
        print("\n1. Checking for existing data...")
        old_session = collection.find_one({"_id": "default_session"})
        
        if not old_session:
            print("   No single-session data found (default_session).")
            print("   Nothing to migrate!")
            return
        
        # Check if it has the old format
        if "display_name" in old_session:
            print("   Data appears to already be in multi-session format.")
            print("   No migration needed!")
            return
        
        # Extract old data
        messages = old_session.get("messages", [])
        created_at = old_session.get("created_at", datetime.utcnow().isoformat())
        last_updated = old_session.get("last_updated", datetime.utcnow().isoformat())
        
        print(f"   Found single-session data with {len(messages)} message exchanges")
        
        # Ask user what to name the migrated session
        print("\n2. Migration Options:")
        print("   The old chat history will be preserved in a new named session.")
        print("   Enter a name for the migrated session (e.g., 'old_chats', 'archive')")
        
        session_name = input("   Session name: ").strip()
        if not session_name:
            session_name = "migrated_session"
        
        # Clean the name
        clean_name = "".join(c for c in session_name if c.isalnum() or c in ['_', '-', ' '])
        clean_name = clean_name.replace(' ', '_').lower()[:30]
        
        # Create new session ID
        import random
        random_suffix = str(random.randint(100, 999))
        new_session_id = f"{clean_name}_{random_suffix}"
        
        print(f"\n3. Migrating to new session: {new_session_id}")
        
        # Create new session document with multi-session format
        new_session = {
            "_id": new_session_id,
            "display_name": clean_name,
            "messages": messages,
            "created_at": created_at,
            "last_updated": last_updated,
            "message_count": len(messages)
        }
        
        # Insert new session
        collection.insert_one(new_session)
        print(f"   ✅ Created new session: {new_session_id}")
        
        # Ask if user wants to delete old session
        print("\n4. Cleanup old data?")
        print("   The old 'default_session' is no longer needed.")
        choice = input("   Delete old session? (y/n): ").strip().lower()
        
        if choice == 'y':
            collection.delete_one({"_id": "default_session"})
            print("   ✅ Deleted old default_session")
        else:
            # Update old session to new format to prevent future migration attempts
            collection.update_one(
                {"_id": "default_session"},
                {"$set": {
                    "display_name": "default_session",
                    "message_count": len(messages)
                }}
            )
            print("   ✅ Updated old session to new format")
        
        print("\n" + "=" * 60)
        print("✅ Migration Complete!")
        print(f"Your chat history is now available in session: {new_session_id}")
        print("You can now use the multi-session interface!")
        print("=" * 60)
        
        # Close connection
        client.close()
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("Please check your MongoDB connection and try again.")
        sys.exit(1)

def check_data_format():
    """Check current data format in the database"""
    print("\nChecking data format...")
    
    try:
        # Validate configuration
        config.validate_required_keys()
        
        client = MongoClient(config.MONGODB_URI)
        db = client[config.DATABASE_NAME]
        collection = db["simple_chats"]
        
        # Get all sessions
        sessions = list(collection.find({}, {"_id": 1, "display_name": 1, "messages": 1}))
        
        print(f"Found {len(sessions)} sessions in database:")
        for session in sessions:
            session_id = session["_id"]
            has_display_name = "display_name" in session
            message_count = len(session.get("messages", []))
            
            if has_display_name:
                print(f"  ✅ {session_id}: Multi-session format ({message_count} messages)")
            else:
                print(f"  ⚠️  {session_id}: Old format - needs migration ({message_count} messages)")
        
        client.close()
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
    except Exception as e:
        print(f"Error checking data: {str(e)}")

if __name__ == "__main__":
    print("Multi-Session Migration Tool")
    print(f"Using Database: {config.DATABASE_NAME}")
    print(f"MongoDB Connection: {'✅ Configured' if config.MONGODB_URI else '❌ Missing'}")
    print("-" * 30)
    print("1. Migrate old data")
    print("2. Check data format")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        migrate_single_to_multi_session()
    elif choice == "2":
        check_data_format()
    else:
        print("Exiting...")
        sys.exit(0)