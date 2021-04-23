import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
# credit docs-im.easemob.com for ideas


class ClientEncryptor:
    def __init__(self):
        self.keyring = dict()
        self.rsa1024_key = None
        self.aes128_key = None

    def load_key(self, filename):
        pass

    def generate_rsa1024_key(self):
        pass

    def generate_aes128_key(self):
        pass

    def export_key(self):
        pass

    @staticmethod
    def pad(content):
        pass

    @staticmethod
    def un_pad(content):
        pass

    def negotiate_aes(self, rsa_public_key,
                      encrypted_aes_key, sha256_hash, signature):  # return aes128 key
        pass

# key file format:
# --- START SHA_256 PUBLIC KEY ---
# xxx
# --- END SHA_256 PUBLIC KEY ---
# --- START SHA_256 PRIVATE KEY ---
# xxx
# --- END SHA_256 PRIVATE KEY ---
# --- START AES128 KEY ---
# xxx
# --- END AES128 KEY ---
# --- START KeyRing ---
# "name":AES128







