#!/usr/bin/env python3
"""
Helper script to set up Snowflake Key-Pair Authentication
Generates key pair and provides instructions for registering with Snowflake
"""

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64

def generate_key_pair(output_dir="./", key_name="snowflake_rsa_key", key_size=2048, with_passphrase=True):
    """
    Generate RSA key pair for Snowflake authentication.
    
    Args:
        output_dir: Directory to save keys
        key_name: Base name for key files
        key_size: RSA key size (2048 recommended)
        with_passphrase: Whether to encrypt private key with passphrase
    """
    print("=" * 70)
    print("  Snowflake Key-Pair Authentication Setup")
    print("=" * 70)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate private key
    print("\n📝 Generating RSA key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    # Get passphrase if needed
    passphrase = None
    if with_passphrase:
        import getpass
        print("\n🔐 Passphrase Protection")
        print("   (Press Enter to skip passphrase - not recommended for production)")
        passphrase_input = getpass.getpass("   Enter passphrase for private key: ")
        if passphrase_input:
            passphrase_confirm = getpass.getpass("   Confirm passphrase: ")
            if passphrase_input == passphrase_confirm:
                passphrase = passphrase_input.encode()
                print("   ✅ Passphrase set")
            else:
                print("   ❌ Passphrases don't match. Generating without passphrase.")
        else:
            print("   ⚠️  Generating unencrypted private key")
    
    # Write private key
    private_key_path = os.path.join(output_dir, f"{key_name}.p8")
    encryption_algorithm = (
        serialization.BestAvailableEncryption(passphrase) 
        if passphrase 
        else serialization.NoEncryption()
    )
    
    with open(private_key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption_algorithm
            )
        )
    
    # Set restrictive permissions on private key
    os.chmod(private_key_path, 0o600)
    print(f"\n✅ Private key saved: {private_key_path}")
    print(f"   Permissions: 600 (read/write for owner only)")
    
    # Write public key (PEM format)
    public_key = private_key.public_key()
    public_key_path = os.path.join(output_dir, f"{key_name}_pub.pem")
    
    with open(public_key_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )
    
    print(f"✅ Public key saved: {public_key_path}")
    
    # Get public key fingerprint for Snowflake
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # For Snowflake, we need the public key without header/footer
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Remove header and footer, and newlines
    public_key_for_snowflake = public_key_pem.replace(
        '-----BEGIN PUBLIC KEY-----', ''
    ).replace(
        '-----END PUBLIC KEY-----', ''
    ).replace('\n', '').strip()
    
    # Print instructions
    print("\n" + "=" * 70)
    print("  🎯 Next Steps - Register Public Key with Snowflake")
    print("=" * 70)
    
    print("\n1️⃣  Copy the public key value below:")
    print("─" * 70)
    print(public_key_for_snowflake)
    print("─" * 70)
    
    print("\n2️⃣  Execute this SQL in Snowflake (replace YOUR_USERNAME):")
    print("─" * 70)
    print(f"""
-- Login to Snowflake as ACCOUNTADMIN or user with appropriate privileges
-- Then run this SQL:

USE ROLE ACCOUNTADMIN;

ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='{public_key_for_snowflake}';

-- Verify it was set correctly:
DESC USER YOUR_USERNAME;
""")
    print("─" * 70)
    
    print("\n3️⃣  Update your snowflake_config.json:")
    print("─" * 70)
    config_example = f"""
{{
  "account": "your_account.region",
  "user": "YOUR_USERNAME",
  "authenticator": "SNOWFLAKE_JWT",
  "private_key_path": "{os.path.abspath(private_key_path)}",
  "private_key_passphrase": "{"YOUR_PASSPHRASE" if passphrase else ""}",
  "role": "YOUR_ROLE",
  "warehouse": "LOG_ANALYZER_WH",
  "database": "LOG_ANALYTICS",
  "schema": "ANOMALY_DETECTION"
}}
"""
    print(config_example)
    print("─" * 70)
    
    if not passphrase:
        print("\n⚠️  WARNING: Private key is NOT encrypted!")
        print("   For production, regenerate with passphrase: python setup_keypair_auth.py")
    
    print("\n4️⃣  Test the connection:")
    print("─" * 70)
    print("   cd snowflake")
    print("   python test_connection.py")
    print("─" * 70)
    
    print("\n✅ Key pair generation complete!")
    print("\n💡 Security Tips:")
    print("   - Keep your private key secure and never commit to git")
    print("   - The private key file has been set to permissions 600")
    print("   - Store passphrase securely (e.g., environment variable)")
    print("   - Rotate keys periodically for security")
    
    return {
        'private_key_path': os.path.abspath(private_key_path),
        'public_key_path': os.path.abspath(public_key_path),
        'public_key_for_snowflake': public_key_for_snowflake
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate RSA key pair for Snowflake authentication"
    )
    parser.add_argument(
        "--output-dir",
        default="./",
        help="Directory to save keys (default: current directory)"
    )
    parser.add_argument(
        "--key-name",
        default="snowflake_rsa_key",
        help="Base name for key files (default: snowflake_rsa_key)"
    )
    parser.add_argument(
        "--no-passphrase",
        action="store_true",
        help="Generate private key without passphrase (not recommended)"
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        help="RSA key size in bits (default: 2048)"
    )
    
    args = parser.parse_args()
    
    result = generate_key_pair(
        output_dir=args.output_dir,
        key_name=args.key_name,
        key_size=args.key_size,
        with_passphrase=not args.no_passphrase
    )

