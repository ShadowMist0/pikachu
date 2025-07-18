from cryptography.fernet import Fernet
import os

key = os.getenv("decryption_key")
fernet = Fernet(key)


with open("info/group-training-data.shadow", "rb") as file:
    training_data = fernet.decrypt(file.read()).decode("utf-8")
    print(training_data)