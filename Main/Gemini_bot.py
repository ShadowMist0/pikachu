import os
from cryptography.fernet import Fernet
from glob import glob

key = os.getenv("decryption_key")
print(key)
