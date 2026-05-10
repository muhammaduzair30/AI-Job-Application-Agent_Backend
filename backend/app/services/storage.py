import logging
import uuid
from io import BytesIO

from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("aiaa.storage")

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
BUCKET_NAME = "cv-uploads"

def upload_file_to_supabase(file_bytes: bytes, filename: str, user_id: uuid.UUID) -> str:
    """
    Uploads a file to Supabase storage under a user-specific folder.
    Returns the file path within the bucket.
    """
    try:
        # Create a unique filename to prevent collisions
        file_extension = filename.split(".")[-1] if "." in filename else ""
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Path format: {user_id}/{unique_filename}
        file_path = f"{user_id}/{unique_filename}"
        
        # Upload the file
        res = supabase.storage.from_(BUCKET_NAME).upload(
            file=file_bytes,
            path=file_path,
            file_options={"content-type": "application/pdf" if file_extension == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
        
        logger.info(f"Successfully uploaded {filename} to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error uploading file to Supabase: {e}")
        raise

def generate_presigned_url(file_path: str, expiration_seconds: int = 3600) -> str:
    """
    Generates a secure signed URL to download/view the file.
    """
    try:
        res = supabase.storage.from_(BUCKET_NAME).create_signed_url(
            path=file_path,
            expires_in=expiration_seconds
        )
        return res.get("signedURL", "")
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise

def delete_file_from_supabase(file_path: str):
    """
    Deletes a file from Supabase storage.
    """
    try:
        if file_path:
            supabase.storage.from_(BUCKET_NAME).remove([file_path])
            logger.info(f"Successfully deleted {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        # We might not want to throw an exception here so that CV deletion from DB still succeeds
        pass
