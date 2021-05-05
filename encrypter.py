import Crypto
import base64
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Cipher import PKCS1_OAEP
import pickle
# credit docs-im.easemob.com for ideas


class ClientEncryptor:
    BLOCK_SIZE = 16

    def __init__(self):
        self.keyring = dict()
        self.rsa_keyring = dict()
        self.name = ""
        self.rsa1024_key = None
        self.aes128_key = None

        self.filename_public = "client_rsa1024_pub.key"
        self.filename_private = "client_rsa1024_pri.key"
        self.filename_aes = "client_aes128.key"
        self.filename_keyring = "client_ring.key"

    def start(self, name):
        self.name = name
        self.filename_public = self.name + "\client_rsa1024_pub.key"
        self.filename_private = self.name + "\client_rsa1024_pri.key"
        self.filename_aes = self.name + "\client_aes128.key"
        self.filename_keyring = self.name + "\client_ring.key"

        try:
            self.load_key()
        except FileNotFoundError as err:
            self.generate_key()

    @staticmethod
    def any_rsa_instance(key_str):
        return RSA.importKey(key_str)

    def load_key(self):
        file_pointer = open(self.filename_keyring, 'rb')
        self.keyring = pickle.load(file_pointer)
        file_pointer.close()

        file_pointer = open(self.filename_private, 'rb')
        lines = file_pointer.readlines()
        lines = b''.join(i for i in lines)
        self.rsa1024_key = RSA.importKey(lines)
        file_pointer.close()

        file_pointer = open(self.filename_public, 'rb')
        lines = file_pointer.readlines()
        lines = b''.join(i for i in lines)
        self.rsa1024_key.publickey = RSA.importKey(lines)
        file_pointer.close()

        file_pointer = open(self.filename_aes, 'rb')
        self.aes128_key = file_pointer.readline()
        file_pointer.close()

    def export_key(self):
        file_pointer = open(self.filename_private, 'wb')
        line = self.rsa1024_key.exportKey(format="PEM")
        file_pointer.write(line)
        file_pointer.close()

        file_pointer = open(self.filename_public, 'wb')
        line = self.rsa1024_key.publickey.exportKey(format="PEM")
        file_pointer.write(line)
        file_pointer.close()

        file_pointer = open(self.filename_aes, 'w')
        line = self.aes128_key
        file_pointer.write(line)
        file_pointer.close()

        file_pointer = open(self.filename_keyring, 'wb')
        pickle.dump(self.keyring, file_pointer, protocol=1)
        file_pointer.close()

    def generate_key(self):
        self.generate_rsa1024_key()
        self.generate_aes128_key()

    def generate_rsa1024_key(self):
        random_generator = Random.new().read
        self.rsa1024_key = RSA.generate(1024, random_generator)

    def generate_aes128_key(self):
        self.aes128_key = Random.get_random_bytes(32)

    @staticmethod
    def pad(s):  # credit. Francesco de Guytenaere
        return s + (ClientEncryptor.BLOCK_SIZE - len(s) % ClientEncryptor.BLOCK_SIZE) \
                    * chr(ClientEncryptor.BLOCK_SIZE - len(s) % ClientEncryptor.BLOCK_SIZE)

    @staticmethod
    def un_pad(s):  # credit. Francesco de Guytenaere
        return s[:-ord(s[len(s) - 1:])]

    def add_keyring(self, name, aes_key):
        self.keyring[name] = aes_key

    def aes_encrypt(self, content):
        content = ClientEncryptor.pad(content)
        iv = Random.new().read(ClientEncryptor.BLOCK_SIZE)
        encryptor = AES.new(self.aes128_key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + encryptor.encrypt(content))

    @staticmethod
    def aes_decrypt(ciphertext, set_aes_key):
        ciphertext = base64.b64decode(ciphertext)
        iv = ciphertext[:ClientEncryptor.BLOCK_SIZE]
        encryptor = AES.new(set_aes_key, AES.MODE_CBC, iv)
        return ClientEncryptor.un_pad(encryptor.decrypt(ciphertext[ClientEncryptor.BLOCK_SIZE:]))

    def rsa_signature(self, ciphertext):
        return self.rsa1024_key.sign(ciphertext, 0)

    def rsa_verify(self, ciphertext, signature):
        return self.rsa1024_key.verify(ciphertext, signature)

    @staticmethod
    def hash_text(content):
        h = SHA256.new(content)
        return h.hexdigest()

    def negotiate_aes(self, name, rsa_public_key,
                      encrypted_aes_key, signature):  # return aes128 key
        cipher = PKCS1_OAEP.new(self.rsa1024_key)
        actual_aes_key = cipher.decrypt(encrypted_aes_key)
        local_hash = self.hash_text(actual_aes_key)
        if rsa_public_key.verify(local_hash, signature):
            self.add_keyring(name, actual_aes_key)
            return True
        else:
            print("Verification failed")
            return False
            # do something

    def create_negotiate_pack(self, rsa_public_key):
        cipher = PKCS1_OAEP.new(rsa_public_key)
        encrypted_aes_key = cipher.encrypt(self.aes128_key)
        local_hash = self.hash_text(self.aes128_key)
        signature = self.rsa1024_key.sign(local_hash, 0)
        return encrypted_aes_key, signature


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
