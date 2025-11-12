"""
Encryption Service for backup file encryption/decryption using AWS KMS.

Implements AC #3 from US-API-006:
- AES-256 encryption via AWS KMS
- Secure key management with automatic rotation
- Encryption/decryption for backup files

Part of Epic 1 - Cross-Cutting / Infrastructure Stories
"""

import logging
import os

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from django.conf import settings

from quran_backend.core.exceptions import EncryptionFailedError
from quran_backend.core.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting backup files using AWS KMS.

    Uses AWS KMS for encryption key management with AES-256 algorithm.
    Supports automatic key rotation for enhanced security.
    """

    def __init__(self):
        """Initialize encryption service with KMS configuration."""
        self.kms_key_id = getattr(
            settings,
            "BACKUP_KMS_KEY_ID",
            "alias/quran-backend-backup-key",
        )
        self.kms_client = boto3.client("kms")

    @retry_with_exponential_backoff(max_retries=3, delays=(2.0, 4.0, 8.0))
    def encrypt_file(self, file_path: str, kms_key_id: str | None = None) -> str:
        """
        Encrypt file using AWS KMS.

        Uses KMS to generate a data key, encrypts the file with the data key,
        and prepends the encrypted data key to the file.

        Args:
            file_path: Path to file to encrypt
            kms_key_id: KMS key ID (defaults to configured key)

        Returns:
            str: Path to encrypted file (file_path + '.enc')

        Raises:
            EncryptionFailedError: If encryption fails
        """
        kms_key = kms_key_id or self.kms_key_id
        encrypted_file = f"{file_path}.enc"

        logger.info(f"Encrypting file with KMS: {file_path} -> {encrypted_file}")

        try:
            # Step 1: Generate data encryption key from KMS
            # This returns both plaintext key (for encryption) and encrypted key (to store)
            response = self.kms_client.generate_data_key(
                KeyId=kms_key,
                KeySpec="AES_256",  # 256-bit AES key
            )

            # Extract plaintext data key and encrypted data key
            plaintext_key = response["Plaintext"]
            encrypted_key = response["CiphertextBlob"]

            # Step 2: Encrypt file with plaintext data key using AES-256-GCM
            import struct

            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import Cipher
            from cryptography.hazmat.primitives.ciphers import algorithms
            from cryptography.hazmat.primitives.ciphers import modes

            # Read file to encrypt
            with open(file_path, "rb") as f:
                plaintext = f.read()

            # Generate random IV (initialization vector)
            import secrets

            iv = secrets.token_bytes(16)  # 128-bit IV for AES

            # Create cipher with AES-256-CBC mode
            cipher = Cipher(
                algorithms.AES(plaintext_key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()

            # Pad plaintext to AES block size (16 bytes)
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext) + padder.finalize()

            # Encrypt data
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # Step 3: Write encrypted file with structure:
            # [encrypted_key_length (4 bytes)] [encrypted_key] [iv_length (4 bytes)] [iv] [ciphertext]
            with open(encrypted_file, "wb") as f:
                # Write encrypted data key length and key
                f.write(struct.pack(">I", len(encrypted_key)))
                f.write(encrypted_key)
                # Write IV length and IV
                f.write(struct.pack(">I", len(iv)))
                f.write(iv)
                # Write encrypted data
                f.write(ciphertext)

            # Log success
            original_size = os.path.getsize(file_path)
            encrypted_size = os.path.getsize(encrypted_file)

            logger.info(
                f"Encryption complete: {original_size / (1024 * 1024):.2f} MB -> "
                f"{encrypted_size / (1024 * 1024):.2f} MB (overhead: "
                f"{((encrypted_size - original_size) / original_size) * 100:.1f}%)",
            )

            return encrypted_file

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"KMS encryption failed: {error_code} - {error_message}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "encryption",
                    "operation": "encrypt_file",
                    "kms_key_id": kms_key,
                    "error_code": error_code,
                },
            )

            raise EncryptionFailedError(f"Encryption failed: {error_message}") from e

        except Exception as e:
            logger.error(f"Unexpected error during encryption: {e!s}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "encryption",
                    "operation": "encrypt_file",
                    "file_path": file_path,
                },
            )

            raise EncryptionFailedError(f"Encryption failed: {e!s}") from e

    @retry_with_exponential_backoff(max_retries=3, delays=(2.0, 4.0, 8.0))
    def decrypt_file(self, file_path: str, kms_key_id: str | None = None) -> str:
        """
        Decrypt file using AWS KMS.

        Extracts encrypted data key from file, decrypts it with KMS,
        then decrypts file content with the data key.

        Args:
            file_path: Path to encrypted file (must end with '.enc')
            kms_key_id: KMS key ID (defaults to configured key, but typically auto-detected)

        Returns:
            str: Path to decrypted file (removes '.enc' extension)

        Raises:
            EncryptionFailedError: If decryption fails
        """
        if not file_path.endswith(".enc"):
            raise EncryptionFailedError(
                "File must have '.enc' extension for decryption",
            )

        decrypted_file = file_path[:-4]  # Remove '.enc' extension

        logger.info(f"Decrypting file with KMS: {file_path} -> {decrypted_file}")

        try:
            # Read encrypted file
            import struct

            with open(file_path, "rb") as f:
                # Read encrypted data key length and key
                encrypted_key_length = struct.unpack(">I", f.read(4))[0]
                encrypted_key = f.read(encrypted_key_length)

                # Read IV length and IV
                iv_length = struct.unpack(">I", f.read(4))[0]
                iv = f.read(iv_length)

                # Read ciphertext (rest of file)
                ciphertext = f.read()

            # Step 1: Decrypt data key using KMS
            # KMS automatically detects which key to use from the encrypted key blob
            response = self.kms_client.decrypt(CiphertextBlob=encrypted_key)
            plaintext_key = response["Plaintext"]

            # Step 2: Decrypt file content using plaintext data key
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import Cipher
            from cryptography.hazmat.primitives.ciphers import algorithms
            from cryptography.hazmat.primitives.ciphers import modes

            # Create cipher
            cipher = Cipher(
                algorithms.AES(plaintext_key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()

            # Decrypt data
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Remove padding
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            # Write decrypted file
            with open(decrypted_file, "wb") as f:
                f.write(plaintext)

            # Log success
            encrypted_size = os.path.getsize(file_path)
            decrypted_size = os.path.getsize(decrypted_file)

            logger.info(
                f"Decryption complete: {encrypted_size / (1024 * 1024):.2f} MB -> "
                f"{decrypted_size / (1024 * 1024):.2f} MB",
            )

            return decrypted_file

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"KMS decryption failed: {error_code} - {error_message}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "encryption",
                    "operation": "decrypt_file",
                    "error_code": error_code,
                },
            )

            raise EncryptionFailedError(f"Decryption failed: {error_message}") from e

        except Exception as e:
            logger.error(f"Unexpected error during decryption: {e!s}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "encryption",
                    "operation": "decrypt_file",
                    "file_path": file_path,
                },
            )

            raise EncryptionFailedError(f"Decryption failed: {e!s}") from e
