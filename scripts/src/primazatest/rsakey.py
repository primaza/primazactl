import argparse
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path


def create_key(key_file):
    certificate = rsa.generate_private_key(public_exponent=65537,
                                           key_size=2048)
    certificate_private_key = certificate.private_bytes(
            format=serialization.PrivateFormat.PKCS8,
            encoding=serialization.Encoding.PEM,
            encryption_algorithm=serialization.NoEncryption()).decode("utf-8")

    with open(key_file, "w") as key:
        key.write(certificate_private_key)


def main():
    parser = argparse.ArgumentParser(
        prog='rsa_key',
        description='Create a rsa private key for testing')

    parser.add_argument("key_file", type=str,
                        help="file to write rsa private key. Must not exist")

    args = parser.parse_args()

    key_file = Path(args.key_file)
    if key_file.is_file():
        parser.error("[ERROR] --key_file already exists")
    key_file_dir = Path(key_file.resolve().parent)
    key_file_dir.mkdir(parents=True, exist_ok=True)

    create_key(args.key_file)

    print(f"private key file was created: {key_file.resolve()}")


if __name__ == "__main__":
    main()
