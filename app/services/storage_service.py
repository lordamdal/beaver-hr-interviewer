# app/services/storage_service.py

import os
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound
import logging
import mimetypes
import uuid
from pathlib import Path
from app.config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        """Initialize Google Cloud Storage client"""
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(settings.BUCKET_NAME)
            if not self.bucket.exists():
                self.bucket = self.client.create_bucket(settings.BUCKET_NAME)
                logger.info(f"Created new bucket: {settings.BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {str(e)}")
            raise

    def _get_safe_filename(self, filename: str) -> str:
        """Generate a safe filename with UUID"""
        ext = Path(filename).suffix
        return f"{uuid.uuid4()}{ext}"

    def _get_file_path(self, user_id: str, file_type: str, filename: str) -> str:
        """Generate a structured file path"""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        return f"{file_type}/{user_id}/{timestamp}/{filename}"

    def upload_file(self, 
                   file_data: bytes, 
                   original_filename: str, 
                   user_id: str, 
                   file_type: str = 'general') -> Tuple[bool, Optional[str]]:
        """
        Upload a file to Google Cloud Storage
        
        Args:
            file_data: The file content in bytes
            original_filename: Original name of the file
            user_id: ID of the user uploading the file
            file_type: Type of file (e.g., 'resume', 'recording')
            
        Returns:
            Tuple of (success_status, file_url)
        """
        try:
            # Generate safe filename and path
            safe_filename = self._get_safe_filename(original_filename)
            file_path = self._get_file_path(user_id, file_type, safe_filename)
            
            # Create blob and upload
            blob = self.bucket.blob(file_path)
            
            # Set content type
            content_type = mimetypes.guess_type(original_filename)[0]
            if content_type:
                blob.content_type = content_type

            # Upload the file
            blob.upload_from_string(
                file_data,
                content_type=content_type
            )

            # Generate public URL
            url = blob.public_url

            logger.info(f"Successfully uploaded file: {file_path}")
            return True, url

        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            return False, None

    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download a file from Google Cloud Storage
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            File content in bytes if successful, None otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            return blob.download_as_bytes()
        except NotFound:
            logger.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            return None

    def generate_signed_url(self, file_path: str, 
                          expiration_minutes: int = 30) -> Optional[str]:
        """
        Generate a signed URL for temporary file access
        
        Args:
            file_path: Path to the file in storage
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Signed URL if successful, None otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()
            logger.info(f"Successfully deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

    def list_user_files(self, user_id: str, 
                       file_type: Optional[str] = None) -> List[dict]:
        """
        List all files for a specific user
        
        Args:
            user_id: ID of the user
            file_type: Optional filter by file type
            
        Returns:
            List of file information dictionaries
        """
        try:
            prefix = f"{file_type}/{user_id}/" if file_type else f"*/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name.split('/')[-1],
                    'path': blob.name,
                    'size': blob.size,
                    'created': blob.time_created,
                    'updated': blob.updated,
                    'url': blob.public_url
                })
            return files
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []

    def get_storage_usage(self, user_id: str) -> dict:
        """
        Get storage usage statistics for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_size = 0
            file_count = 0
            file_types = {}

            blobs = self.bucket.list_blobs(prefix=f"*/{user_id}/")
            
            for blob in blobs:
                total_size += blob.size
                file_count += 1
                
                # Count files by type
                file_type = blob.name.split('/')[0]
                if file_type in file_types:
                    file_types[file_type] += 1
                else:
                    file_types[file_type] = 1

            return {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'file_types': file_types
            }
        except Exception as e:
            logger.error(f"Failed to get storage usage: {str(e)}")
            return {
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'file_count': 0,
                'file_types': {}
            }

    def cleanup_old_files(self, days: int = 30) -> bool:
        """
        Clean up files older than specified days
        
        Args:
            days: Number of days to keep files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            blobs = self.bucket.list_blobs()
            
            for blob in blobs:
                if blob.time_created < cutoff_date:
                    blob.delete()
                    logger.info(f"Deleted old file: {blob.name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {str(e)}")
            return False

# Usage example
if __name__ == "__main__":
    # Test storage service
    storage_service = StorageService()
    
    # Test file upload
    test_content = b"Hello, World!"
    success, url = storage_service.upload_file(
        test_content,
        "test.txt",
        "test_user_id",
        "test"
    )
    
    if success:
        print(f"File uploaded successfully. URL: {url}")
        
        # Test file download
        content = storage_service.download_file("test/test_user_id/test.txt")
        if content:
            print(f"File content: {content.decode()}")
            
        # Test signed URL generation
        signed_url = storage_service.generate_signed_url("test/test_user_id/test.txt")
        if signed_url:
            print(f"Signed URL: {signed_url}")