"""Generate a fresh shared credential pair, without replacing existing files."""
from pathlib import Path
import os
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main():
    folder = Path(__file__).resolve().parents[1] / '.credentials'
    folder.mkdir(mode=0o700, exist_ok=True)
    paths = [folder / name for name in ('python.env', 'akadverse.env')]
    if any(path.exists() for path in paths):
        raise SystemExit('Credential files already exist; reuse them or choose a deliberate rotation workflow.')
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode().replace('\n', '\\n')
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                          serialization.PublicFormat.SubjectPublicKeyInfo).decode().replace('\n', '\\n')
    shared = (f'PRODUCTIVITY_AI_SERVICE_TOKEN={secrets.token_urlsafe(48)}\n'
              f'PRODUCTIVITY_AI_JWT_PUBLIC_KEY="{public}"\n'
              'PRODUCTIVITY_AI_JWT_KEY_ID=productivity-v1\n')
    values = [shared, shared + f'PRODUCTIVITY_AI_JWT_PRIVATE_KEY="{private}"\n']
    for path, value in zip(paths, values):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(value)
    print('Created .credentials/python.env and .credentials/akadverse.env. Copy values to the respective server secret stores; see README.md for remaining settings.')


if __name__ == '__main__':
    main()
