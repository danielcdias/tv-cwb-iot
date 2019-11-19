import zlib
import sys

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode


KEY_SIZE = 32
KEY_LENGTH = 44
NONCE_LENGTH = 24
TAG_LENGTH = 24


def zip_message(message):
    zip_zlib = b64encode(zlib.compress(
        bytes(message, 'utf-8'))).decode('utf-8')
    return zip_zlib


def unzip_message(message):
    unzip_zlip = zlib.decompress(b64decode(
        bytes(message, 'utf-8'))).decode('utf-8')
    return unzip_zlip


def scramble(encrypted_message):
    result = encrypted_message[0:2]
    for i in range(2, len(encrypted_message) - 2, 2):
        result += encrypted_message[(i + 1):(i + 2)] + \
            encrypted_message[i:(i + 1)]
    result += encrypted_message[-2:]
    return result


def encrypt(plain_text):
    key = get_random_bytes(KEY_SIZE)
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(bytes(plain_text, 'utf8'))
    result_key = b64encode(key).decode('utf-8')
    result_nonce = b64encode(cipher.nonce).decode('utf-8')
    result_ciphertext = b64encode(ciphertext).decode('utf-8')
    result_tag = b64encode(tag).decode('utf-8')
    result = result_key + result_nonce + result_tag + result_ciphertext
    return zip_message(scramble(result))


def decrypt(scrambled_message):
    if scrambled_message[0:4] == "ENC(" and scrambled_message[-1:] == ")":
        scrambled_message = scrambled_message[4:-1]
    encrypted_message = scramble(unzip_message(scrambled_message))
    key = b64decode(bytes(encrypted_message[0:KEY_LENGTH], 'utf-8'))
    nonce = b64decode(
        bytes(encrypted_message[KEY_LENGTH:(KEY_LENGTH+NONCE_LENGTH)], 'utf-8'))
    tag = b64decode(
        bytes(encrypted_message[(KEY_LENGTH+NONCE_LENGTH):(KEY_LENGTH+NONCE_LENGTH+TAG_LENGTH)], 'utf-8'))
    ciphertext = b64decode(
        bytes(encrypted_message[(KEY_LENGTH+NONCE_LENGTH+TAG_LENGTH):], 'utf-8'))
    cipher = AES.new(key, AES.MODE_EAX, nonce)
    result = cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
    return result


def main():
    if len(sys.argv) > 1:
        print("Input:  {}".format(sys.argv[1]))
        print("Output: {}".format(encrypt(sys.argv[1])))
    else:
        print("*** Please, inform something to be encrypted.")
    sys.exit(0)


if __name__ == '__main__':
    main()
