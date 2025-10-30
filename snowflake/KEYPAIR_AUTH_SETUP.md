# Snowflake Key-Pair Authentication Setup Guide

This guide will help you set up **key-pair authentication** for Snowflake, which is **more secure** than password-based authentication.

---

## 🔐 Why Key-Pair Authentication?

✅ **More Secure**: Private keys are harder to compromise than passwords  
✅ **No Password Expiration**: Keys don't expire like passwords  
✅ **Auditable**: Better tracking of authentication events  
✅ **Recommended for Production**: Industry best practice  

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Generate Key Pair

Run the automated setup script:

```bash
cd snowflake
python setup_keypair_auth.py
```

This will:
- Generate an RSA 2048-bit key pair
- Prompt for a passphrase (recommended for security)
- Save the private key as `snowflake_rsa_key.p8`
- Save the public key as `snowflake_rsa_key_pub.pem`
- Display the public key value for Snowflake registration

**Example output:**
```
==================================================================
  Snowflake Key-Pair Authentication Setup
==================================================================

📝 Generating RSA key pair...

🔐 Passphrase Protection
   (Press Enter to skip passphrase - not recommended for production)
   Enter passphrase for private key: ********
   Confirm passphrase: ********
   ✅ Passphrase set

✅ Private key saved: ./snowflake_rsa_key.p8
   Permissions: 600 (read/write for owner only)
✅ Public key saved: ./snowflake_rsa_key_pub.pem

==================================================================
  🎯 Next Steps - Register Public Key with Snowflake
==================================================================

1️⃣  Copy the public key value below:
──────────────────────────────────────────────────────────────────
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA... [YOUR PUBLIC KEY]
──────────────────────────────────────────────────────────────────
```

### Step 2: Register Public Key in Snowflake

Copy the public key value from Step 1 and execute this SQL in Snowflake:

```sql
-- Login to Snowflake Web UI or use SnowSQL
-- Run as ACCOUNTADMIN or a user with ALTER USER privilege

USE ROLE ACCOUNTADMIN;

-- Replace YOUR_USERNAME with your actual Snowflake username
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<PASTE_PUBLIC_KEY_HERE>';

-- Verify it was set correctly
DESC USER YOUR_USERNAME;
```

**Verify in output:** Look for `RSA_PUBLIC_KEY_FP` (fingerprint) to confirm the key is registered.

### Step 3: Update Configuration

Edit `snowflake_config.json` with your details:

```json
{
  "account": "abc12345.us-east-1",
  "user": "YOUR_USERNAME",
  "authenticator": "SNOWFLAKE_JWT",
  "private_key_path": "./snowflake_rsa_key.p8",
  "private_key_passphrase": "YOUR_PASSPHRASE",
  "role": "SYSADMIN",
  "warehouse": "LOG_ANALYZER_WH",
  "database": "LOG_ANALYTICS",
  "schema": "ANOMALY_DETECTION"
}
```

**Fields to update:**
- `account`: Your Snowflake account identifier
- `user`: Your Snowflake username (same as in Step 2)
- `private_key_path`: Path to your private key file
- `private_key_passphrase`: The passphrase you set (or remove this line if no passphrase)
- `role`: Your Snowflake role

---

## ✅ Test Connection

Test that key-pair authentication is working:

```bash
cd snowflake
python test_connection.py
```

**Expected output:**
```
==============================================================
  Testing Snowflake Connection (Key-Pair Auth)
==============================================================

📄 Loading config from: snowflake_config.json
✅ Config loaded
   Account: abc12345.us-east-1
   User: YOUR_USERNAME
   Role: SYSADMIN
   Auth: Key-Pair (JWT)
   Private Key: ./snowflake_rsa_key.p8

🔑 Loading private key...
✅ Private key loaded successfully

🔌 Connecting to Snowflake...
✅ Connection successful!

📊 Connection Details:
   Account: ABC12345
   User: YOUR_USERNAME
   Role: SYSADMIN
   Warehouse: LOG_ANALYZER_WH
   Database: LOG_ANALYTICS
   Schema: ANOMALY_DETECTION

🧪 Running test query...
   Snowflake Version: 8.x.x

✅ All tests passed! 🎉
```

---

## 📖 Manual Key Generation (Advanced)

If you prefer to generate keys manually using OpenSSL:

### Generate Private Key (Encrypted)

```bash
cd snowflake
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 des3 -inform PEM -out snowflake_rsa_key.p8
```

You'll be prompted for a passphrase.

### Generate Private Key (Unencrypted - Not Recommended)

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -inform PEM -out snowflake_rsa_key.p8
```

### Extract Public Key

```bash
openssl rsa -in snowflake_rsa_key.p8 -pubout -out snowflake_rsa_key_pub.pem
```

### Get Public Key for Snowflake

```bash
# Remove headers and format for Snowflake
grep -v "BEGIN PUBLIC" snowflake_rsa_key_pub.pem | \
grep -v "END PUBLIC" | \
tr -d '\n'
```

Copy the output and use in the `ALTER USER` SQL statement.

---

## 🔒 Security Best Practices

### 1. Protect Your Private Key

```bash
# Set restrictive permissions (done automatically by our script)
chmod 600 snowflake_rsa_key.p8

# Never commit to git
# (already in .gitignore)
```

### 2. Use Passphrases

Always encrypt your private key with a strong passphrase:
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Store securely (password manager, environment variable)

### 3. Environment Variables (Production)

For production, store the passphrase in an environment variable:

```bash
# In your shell or .bashrc
export SNOWFLAKE_KEY_PASSPHRASE="your_secure_passphrase"
```

Then update your code to read from environment:

```python
import os
config['private_key_passphrase'] = os.environ.get('SNOWFLAKE_KEY_PASSPHRASE')
```

### 4. Key Rotation

Rotate keys periodically (recommended: every 90 days):

```bash
# Generate new key pair
python setup_keypair_auth.py --key-name snowflake_rsa_key_v2

# Register new public key in Snowflake
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<NEW_PUBLIC_KEY>';

# Test with new key
# Update config to use new key
# Remove old key after confirming new key works

# Optional: Keep old key as backup for 24 hours
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY_2='<OLD_PUBLIC_KEY>';
```

### 5. Backup Keys Securely

- Store encrypted backup in secure location (NOT in git)
- Use encrypted vault or key management service
- Document recovery procedures

---

## 🔧 Troubleshooting

### Issue: "Private key is encrypted but passphrase is incorrect"

**Solution:**
- Verify you entered the correct passphrase
- Check for typos in `snowflake_config.json`
- Try regenerating the key pair

### Issue: "Public key not found for user"

**Solution:**
```sql
-- Verify key is registered
DESC USER YOUR_USERNAME;

-- Check for RSA_PUBLIC_KEY_FP field
-- If empty, re-run the ALTER USER command
```

### Issue: "User not authorized"

**Solution:**
- Verify the user has the specified role
- Check role has necessary privileges
- Ensure warehouse exists and user has USAGE privilege

### Issue: "Failed to connect to Snowflake"

**Solution:**
1. Verify account identifier is correct
2. Check network connectivity
3. Verify private key file exists and is readable
4. Check passphrase is correct
5. Confirm public key is registered

---

## 🔄 Switching from Password to Key-Pair Auth

If you already have password-based config:

```bash
# 1. Generate key pair
python setup_keypair_auth.py

# 2. Register public key in Snowflake (see Step 2 above)

# 3. Update config - change these fields:
#    OLD:                          NEW:
#    "password": "..."       →     "authenticator": "SNOWFLAKE_JWT",
#                                   "private_key_path": "./snowflake_rsa_key.p8",
#                                   "private_key_passphrase": "..."

# 4. Test connection
python test_connection.py

# 5. Done! Your password is no longer used
```

---

## 📚 Additional Resources

- [Snowflake Key-Pair Auth Documentation](https://docs.snowflake.com/en/user-guide/key-pair-auth.html)
- [Snowpark Python API Reference](https://docs.snowflake.com/en/developer-guide/snowpark/python/index.html)
- [Cryptography Library Docs](https://cryptography.io/)

---

## ✨ Quick Commands Reference

```bash
# Generate key pair (with passphrase)
python setup_keypair_auth.py

# Generate without passphrase (not recommended)
python setup_keypair_auth.py --no-passphrase

# Specify custom location and name
python setup_keypair_auth.py --output-dir /secure/location --key-name my_key

# Test connection
python test_connection.py

# Run analysis with key-pair auth
python snowpark_analyzer.py

# Launch Streamlit with key-pair auth
streamlit run streamlit_app.py
```

---

## 🎉 You're All Set!

Once you complete these steps, your Snowflake connection will use secure key-pair authentication! 🔐

All the Python scripts (`snowpark_analyzer.py`, `streamlit_app.py`, `quick_start.py`) will automatically detect and use key-pair authentication.

**Next steps:**
1. ✅ Test connection: `python test_connection.py`
2. ✅ Run setup SQL: See main deployment guide
3. ✅ Start analyzing logs!

