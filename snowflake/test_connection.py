#!/usr/bin/env python3
"""
Test Snowflake connection with key-pair authentication
"""

import json
import os
import sys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def load_private_key(private_key_path, passphrase=None):
    """Load and decode the private key."""
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend()
        )
    
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

def test_connection():
    """Test Snowflake connection with key-pair authentication."""
    print("=" * 60)
    print("  Testing Snowflake Connection (Key-Pair Auth)")
    print("=" * 60)
    
    # Load config
    config_path = "snowflake_config.json"
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        print("\n💡 Create it from the example:")
        print("   cp snowflake_config.json.example snowflake_config.json")
        return False
    
    print(f"\n📄 Loading config from: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Validate required fields
    required_fields = ['account', 'user', 'role']
    missing_fields = [f for f in required_fields if f not in config]
    if missing_fields:
        print(f"❌ Missing required fields: {', '.join(missing_fields)}")
        return False
    
    print(f"✅ Config loaded")
    print(f"   Account: {config.get('account')}")
    print(f"   User: {config.get('user')}")
    print(f"   Role: {config.get('role')}")
    
    # Check authentication method
    auth_method = config.get('authenticator', 'password')
    
    if auth_method == 'SNOWFLAKE_JWT':
        print(f"   Auth: Key-Pair (JWT)")
        
        # Load private key
        private_key_path = config.get('private_key_path')
        if not private_key_path:
            print("❌ private_key_path not specified in config")
            return False
        
        if not os.path.exists(private_key_path):
            print(f"❌ Private key file not found: {private_key_path}")
            print("\n💡 Generate key pair:")
            print("   python setup_keypair_auth.py")
            return False
        
        print(f"   Private Key: {private_key_path}")
        
        # Load private key
        try:
            passphrase = config.get('private_key_passphrase')
            if passphrase and passphrase in ['your_passphrase_if_encrypted', '']:
                passphrase = None
            
            print("\n🔑 Loading private key...")
            private_key_bytes = load_private_key(private_key_path, passphrase)
            print("✅ Private key loaded successfully")
            
            # Update config for Snowpark
            connection_config = {
                'account': config['account'],
                'user': config['user'],
                'private_key': private_key_bytes,
                'role': config.get('role'),
                'warehouse': config.get('warehouse'),
                'database': config.get('database'),
                'schema': config.get('schema')
            }
        except ValueError as e:
            if 'password' in str(e).lower():
                print("❌ Private key is encrypted but passphrase is incorrect or missing")
                print("\n💡 Update private_key_passphrase in config or regenerate without passphrase")
            else:
                print(f"❌ Error loading private key: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading private key: {e}")
            return False
    else:
        print(f"   Auth: Password")
        connection_config = config.copy()
    
    # Test connection
    try:
        print("\n🔌 Connecting to Snowflake...")
        from snowflake.snowpark import Session
        
        session = Session.builder.configs(connection_config).create()
        
        print("✅ Connection successful!")
        print("\n📊 Connection Details:")
        print(f"   Account: {session.get_current_account()}")
        print(f"   User: {session.get_current_user()}")
        print(f"   Role: {session.get_current_role()}")
        print(f"   Warehouse: {session.get_current_warehouse()}")
        print(f"   Database: {session.get_current_database()}")
        print(f"   Schema: {session.get_current_schema()}")
        
        # Test query
        print("\n🧪 Running test query...")
        result = session.sql("SELECT CURRENT_VERSION() AS VERSION").collect()
        print(f"   Snowflake Version: {result[0]['VERSION']}")
        
        session.close()
        print("\n✅ All tests passed! 🎉")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify your account identifier is correct")
        print("   2. Check that the public key is registered in Snowflake:")
        print("      DESC USER YOUR_USERNAME;")
        print("   3. Ensure the user has the specified role")
        print("   4. Verify warehouse exists and you have USAGE privilege")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

