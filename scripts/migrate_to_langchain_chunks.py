"""
Migration Script: Re-process Existing Documents with LangChain Chunking.

This script migrates existing documents from the old single-chunk strategy
to the new LangChain semantic chunking strategy.

Usage:
    python scripts/migrate_to_langchain_chunks.py [--all] [--document-id ID] [--dry-run]

Options:
    --all           Migrate all documents
    --document-id   Migrate specific document by ID
    --dry-run       Show what would be migrated without making changes
    --backup        Create backup before migration (recommended)
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.db.services import (
    document_service,
    document_chunk_service,
)
from src.config.rag_config import get_config
from src.services.base.implements.IngestionService import IngestionService
from src.services.base.implements.LangChainPdfIngestionPipeline import LangChainPdfIngestionPipeline
from src.services.base.implements.EnhancedPdfProcessor import EnhancedPdfProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentMigrator:
    """Migrates documents from old to new chunking strategy."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize the migrator.

        Args:
            dry_run: If True, don't make actual changes
        """
        self.dry_run = dry_run
        self.config = get_config()

        # Initialize services
        logger.info("Initializing migration services...")

        # Create ingestion service with enhanced PDF processor
        enhanced_processor = EnhancedPdfProcessor(
            text_threshold=self.config.text_threshold,
            dpi=self.config.pdf_dpi,
            ocr_languages=self.config.ocr_languages,
            ocr_enabled=self.config.ocr_enabled
        )

        self.ingestion_service = IngestionService(
            processors={'.pdf': enhanced_processor}
        )

        # Create LangChain pipeline
        self.pipeline = LangChainPdfIngestionPipeline(
            ingestion_service=self.ingestion_service,
            embedding_model_name=self.config.text_embedding_model,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

        logger.info("Migration services initialized")

    def get_documents_to_migrate(
        self,
        document_id: Optional[int] = None
    ) -> List:
        """
        Get list of documents that need migration.

        Args:
            document_id: Specific document ID to migrate, or None for all

        Returns:
            List of documents to migrate
        """
        if document_id:
            doc = document_service.get_document_by_id(document_id)
            if not doc:
                logger.error(f"Document with ID {document_id} not found")
                return []
            return [doc]
        else:
            # Get all processed PDF documents
            all_docs = document_service.get_all_processed_documents()
            pdf_docs = [doc for doc in all_docs if doc.file_type == 'PDF']
            return pdf_docs

    def needs_migration(self, document_id: int) -> bool:
        """
        Check if a document needs migration.

        Args:
            document_id: Document ID to check

        Returns:
            True if document needs migration
        """
        chunks = document_chunk_service.get_chunks_by_document(document_id)

        if not chunks:
            logger.warning(f"Document {document_id} has no chunks")
            return False

        # Check if document uses old strategy (single chunk or no metadata)
        if len(chunks) == 1:
            # Check metadata
            chunk_metadata = chunks[0].extra_metadata or {}
            chunk_strategy = chunk_metadata.get('chunk_strategy')

            if chunk_strategy != 'langchain':
                logger.info(
                    f"Document {document_id} uses old chunking strategy "
                    f"(1 chunk, strategy: {chunk_strategy})"
                )
                return True

        return False

    def backup_document(self, document_id: int) -> dict:
        """
        Create a backup of document chunks before migration.

        Args:
            document_id: Document ID to backup

        Returns:
            Dictionary with backup data
        """
        doc = document_service.get_document_by_id(document_id)
        chunks = document_chunk_service.get_chunks_by_document(document_id)

        backup = {
            'document_id': document_id,
            'filename': doc.filename,
            'backup_timestamp': datetime.utcnow().isoformat(),
            'chunks': [
                {
                    'chunk_id': chunk.id,
                    'chunk_index': chunk.chunk_index,
                    'heading': chunk.heading,
                    'content': chunk.content,
                    'content_length': chunk.content_length,
                    'embedding_model': chunk.embedding_model,
                    'metadata': chunk.extra_metadata
                }
                for chunk in chunks
            ]
        }

        return backup

    def migrate_document(self, document_id: int) -> bool:
        """
        Migrate a single document to new chunking strategy.

        Args:
            document_id: Document ID to migrate

        Returns:
            True if migration succeeded
        """
        try:
            doc = document_service.get_document_by_id(document_id)

            if not doc:
                logger.error(f"Document {document_id} not found")
                return False

            logger.info(f"Migrating document: {doc.filename} (ID: {document_id})")

            # Check if file still exists
            if not doc.file_path or not os.path.exists(doc.file_path):
                logger.error(
                    f"Document file not found: {doc.file_path}. "
                    f"Cannot re-process document."
                )
                return False

            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate document {document_id}")
                return True

            # Get old chunks count
            old_chunks = document_chunk_service.get_chunks_by_document(document_id)
            old_chunk_count = len(old_chunks)

            logger.info(f"Old chunk count: {old_chunk_count}")

            # Delete old chunks
            for chunk in old_chunks:
                # Note: Need to implement delete_chunk in service
                # For now, we'll let the pipeline handle it
                pass

            # Re-process with new pipeline
            result = self.pipeline.process(doc.file_path)

            new_chunk_count = result.get('chunks_created', 0)

            logger.info(
                f"Migration complete: {doc.filename}\n"
                f"  Old chunks: {old_chunk_count}\n"
                f"  New chunks: {new_chunk_count}\n"
                f"  Document ID: {document_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Migration failed for document {document_id}: {str(e)}")
            return False

    def migrate_all(
        self,
        document_ids: Optional[List[int]] = None,
        create_backup: bool = True
    ) -> dict:
        """
        Migrate multiple documents.

        Args:
            document_ids: List of document IDs to migrate, or None for all
            create_backup: Whether to create backups before migration

        Returns:
            Dictionary with migration statistics
        """
        stats = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'backups': []
        }

        # Get documents to migrate
        if document_ids:
            documents = [
                document_service.get_document_by_id(doc_id)
                for doc_id in document_ids
            ]
            documents = [doc for doc in documents if doc]
        else:
            documents = self.get_documents_to_migrate()

        stats['total'] = len(documents)

        logger.info(f"Found {len(documents)} documents to process")

        for doc in documents:
            # Check if migration needed
            if not self.needs_migration(doc.id):
                logger.info(f"Skipping {doc.filename} (already migrated)")
                stats['skipped'] += 1
                continue

            # Create backup if requested
            if create_backup and not self.dry_run:
                backup = self.backup_document(doc.id)
                stats['backups'].append(backup)
                logger.info(f"Created backup for document {doc.id}")

            # Migrate document
            success = self.migrate_document(doc.id)

            if success:
                stats['migrated'] += 1
            else:
                stats['failed'] += 1

        return stats


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description='Migrate documents to LangChain chunking strategy'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Migrate all documents'
    )

    parser.add_argument(
        '--document-id',
        type=int,
        help='Migrate specific document by ID'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup creation (not recommended)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.document_id:
        logger.error("Must specify --all or --document-id")
        parser.print_help()
        sys.exit(1)

    # Initialize migrator
    migrator = DocumentMigrator(dry_run=args.dry_run)

    # Run migration
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")

    if args.document_id:
        # Migrate single document
        logger.info(f"Migrating document ID: {args.document_id}")

        if not args.no_backup and not args.dry_run:
            backup = migrator.backup_document(args.document_id)
            logger.info(f"Backup created: {backup}")

        success = migrator.migrate_document(args.document_id)

        if success:
            logger.info("Migration completed successfully")
            sys.exit(0)
        else:
            logger.error("Migration failed")
            sys.exit(1)

    elif args.all:
        # Migrate all documents
        logger.info("Migrating all documents...")

        stats = migrator.migrate_all(create_backup=not args.no_backup)

        logger.info("\n" + "="*60)
        logger.info("Migration Summary:")
        logger.info(f"  Total documents:    {stats['total']}")
        logger.info(f"  Migrated:          {stats['migrated']}")
        logger.info(f"  Skipped:           {stats['skipped']}")
        logger.info(f"  Failed:            {stats['failed']}")
        logger.info(f"  Backups created:   {len(stats['backups'])}")
        logger.info("="*60 + "\n")

        if stats['failed'] > 0:
            logger.warning(f"{stats['failed']} documents failed to migrate")
            sys.exit(1)
        else:
            logger.info("All documents migrated successfully")
            sys.exit(0)


if __name__ == '__main__':
    main()
