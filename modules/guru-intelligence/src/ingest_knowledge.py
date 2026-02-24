#!/usr/bin/env python3
"""
Guru Intelligence Knowledge Ingestion System
Ingests all SmarketSherpa IP into the Knowledge Graph for RAG retrieval

This activates the intelligence system by populating:
1. PostgreSQL with document chunks and metadata
2. Embeddings for semantic search
3. Structured rules for validation
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/guru-intelligence/logs/ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database connection
try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# For embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed. Embeddings disabled.")
    EMBEDDINGS_AVAILABLE = False


class KnowledgeIngester:
    """Ingests documents into Guru Intelligence Knowledge Graph"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.embedder = None
        
        # Document type mappings
        self.doc_types = {
            'playbook': 'Operational playbook with actionable guidelines',
            'framework': 'Strategic framework defining standards',
            'sop': 'Standard operating procedure',
            'rules': 'Validation rules for content quality',
            'guide': 'Educational guide with best practices',
            'analysis': 'Gap analysis or assessment document'
        }
        
        # Source document registry
        self.source_docs = {
            'AI-SEO-Playbook-Complete-2026.docx': {
                'type': 'playbook',
                'domain': 'ai-seo',
                'priority': 'P1',
                'description': 'Complete AI-SEO/AEO/GEO Playbook - Gold Standard'
            },
            'THE_MASTER_AI-SEO___GEO_BLUEPRINT__v6_01_7_0_.md': {
                'type': 'framework',
                'domain': 'ai-seo',
                'priority': 'P1',
                'description': 'Master AI-SEO & GEO Blueprint v6.0'
            },
            'THE_ENHANCED_AI-SEO_CONTENT_GUIDE__2026_EDITION_.md': {
                'type': 'guide',
                'domain': 'content',
                'priority': 'P1',
                'description': 'Enhanced AI-SEO Content Guide 2026'
            },
            'AI-SEO_AEO_AGE_CONTENT_GUIDE.md': {
                'type': 'guide',
                'domain': 'content',
                'priority': 'P1',
                'description': 'AI-SEO AEO Age Content Guide'
            },
            'TOP_25_LOCAL_SEARCH_RANKING_FACTORS.md': {
                'type': 'guide',
                'domain': 'local-seo',
                'priority': 'P1',
                'description': 'Top 25 Local Search Ranking Factors'
            },
            'RR-Automation-Gap-Analysis-v1.docx': {
                'type': 'analysis',
                'domain': 'rr-automation',
                'priority': 'P1',
                'description': 'R&R Automation Gap Analysis v1'
            },
            'RANK_EXPAND_ACADEMY_Merged_Master_Summar.md': {
                'type': 'framework',
                'domain': 'prompting',
                'priority': 'P2',
                'description': 'Rank Expand Academy Methodology'
            },
            '53-Site-Factory-Operations-Manual-V2.docx': {
                'type': 'sop',
                'domain': 'operations',
                'priority': 'P1',
                'description': '53-Site Factory Operations Manual'
            },
            '53_SITES_FACTORY_PLAYBOOK_12-18-25': {
                'type': 'playbook',
                'domain': 'operations',
                'priority': 'P1',
                'description': '53 Sites Factory Playbook'
            },
            'CORRECTED-DELIVERABLES-SUMMARY.md': {
                'type': 'sop',
                'domain': 'architecture',
                'priority': 'P2',
                'description': 'Corrected Deliverables Summary'
            },
            'SEO_Guru-Darren_Shaw___Whitespark__SaaS___Local_SEO_agency_.md': {
                'type': 'guide',
                'domain': 'local-seo',
                'priority': 'P2',
                'description': 'Darren Shaw Local SEO Insights'
            },
            'SEO_Strategy_for_Keyword_Grouping_and_Avoiding_Internal_Competition': {
                'type': 'guide',
                'domain': 'seo-strategy',
                'priority': 'P2',
                'description': 'SEO Keyword Grouping Strategy'
            }
        }
    
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def init_embedder(self):
        """Initialize sentence transformer for embeddings"""
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Embeddings model loaded")
            except Exception as e:
                logger.warning(f"Could not load embeddings model: {e}")
                self.embedder = None
    
    def create_tables(self):
        """Create knowledge ingestion tables"""
        cursor = self.conn.cursor()
        
        # Main knowledge chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id SERIAL PRIMARY KEY,
                source_file VARCHAR(255) NOT NULL,
                chunk_hash VARCHAR(64) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                content_type VARCHAR(50),
                domain VARCHAR(50),
                priority VARCHAR(10),
                section_title VARCHAR(500),
                chunk_index INTEGER,
                word_count INTEGER,
                embedding FLOAT8[],
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge_chunks(domain);
            CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_chunks(content_type);
            CREATE INDEX IF NOT EXISTS idx_knowledge_priority ON knowledge_chunks(priority);
        """)
        
        # Extracted rules table (for validation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_rules (
                id SERIAL PRIMARY KEY,
                rule_id VARCHAR(100) UNIQUE NOT NULL,
                rule_name VARCHAR(255) NOT NULL,
                rule_category VARCHAR(100) NOT NULL,
                rule_description TEXT NOT NULL,
                enforcement_level VARCHAR(50) DEFAULT 'recommended',
                priority_score INTEGER DEFAULT 50,
                applicable_page_types TEXT[],
                source_document VARCHAR(255),
                source_section VARCHAR(500),
                validation_logic TEXT,
                examples JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_rules_category ON extracted_rules(rule_category);
            CREATE INDEX IF NOT EXISTS idx_rules_enforcement ON extracted_rules(enforcement_level);
        """)
        
        # Document registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingested_documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                file_hash VARCHAR(64),
                doc_type VARCHAR(50),
                domain VARCHAR(50),
                priority VARCHAR(10),
                description TEXT,
                chunk_count INTEGER DEFAULT 0,
                rules_extracted INTEGER DEFAULT 0,
                ingested_at TIMESTAMP DEFAULT NOW(),
                last_updated TIMESTAMP DEFAULT NOW()
            );
        """)
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def read_document(self, filepath: str) -> str:
        """Read document content based on file type"""
        path = Path(filepath)
        
        if path.suffix.lower() == '.md':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif path.suffix.lower() == '.docx':
            # Use pandoc for DOCX conversion
            try:
                result = subprocess.run(
                    ['pandoc', filepath, '-t', 'markdown'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return result.stdout
                else:
                    logger.error(f"Pandoc error: {result.stderr}")
                    return ""
            except subprocess.TimeoutExpired:
                logger.error(f"Pandoc timeout for {filepath}")
                return ""
            except FileNotFoundError:
                logger.error("Pandoc not installed")
                return ""
        
        elif path.suffix == '' or path.suffix.lower() in ['.txt', '.json']:
            # Try reading as text
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return ""
        
        return ""
    
    def chunk_content(self, content: str, chunk_size: int = 1500, overlap: int = 200) -> List[Dict]:
        """
        Intelligently chunk content by sections/headers
        Returns list of chunks with metadata
        """
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_section = "Introduction"
        chunk_index = 0
        
        for line in lines:
            # Detect section headers
            if line.startswith('# '):
                current_section = line[2:].strip()
            elif line.startswith('## '):
                current_section = line[3:].strip()
            elif line.startswith('### '):
                current_section = line[4:].strip()
            
            current_chunk.append(line)
            current_text = '\n'.join(current_chunk)
            
            # Check if chunk is large enough
            if len(current_text.split()) >= chunk_size:
                chunks.append({
                    'content': current_text,
                    'section_title': current_section,
                    'chunk_index': chunk_index,
                    'word_count': len(current_text.split())
                })
                
                # Keep overlap for context
                overlap_lines = current_chunk[-10:] if len(current_chunk) > 10 else []
                current_chunk = overlap_lines
                chunk_index += 1
        
        # Add remaining content
        if current_chunk:
            current_text = '\n'.join(current_chunk)
            if current_text.strip():
                chunks.append({
                    'content': current_text,
                    'section_title': current_section,
                    'chunk_index': chunk_index,
                    'word_count': len(current_text.split())
                })
        
        return chunks
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text chunk"""
        if self.embedder and text.strip():
            try:
                embedding = self.embedder.encode(text[:8000])  # Limit input
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")
        return None
    
    def extract_rules_from_content(self, content: str, source_file: str) -> List[Dict]:
        """
        Extract structured rules from content
        Looks for patterns like:
        - Numbered rules
        - BLUF, QA-style headers, etc.
        - Checklists
        """
        rules = []
        
        # Rule extraction patterns
        rule_patterns = [
            # BLUF rules
            (r'BLUF|Bottom Line Up Front', 'BLUF & Answer-First', 'bluf'),
            # QA Headers
            (r'QA-Style|Question.*Header|H2.*question', 'QA-Style Headers', 'qa-headers'),
            # Voice Modality
            (r'Professor|Peer|Partner.*voice|Voice Modal', 'Voice Modality', 'voice'),
            # Entity rules
            (r'Entity.*First|Entity.*Density|Named Entit', 'Entity-First Structure', 'entity'),
            # Semantic Chunking
            (r'Semantic Chunk|Claim.*Evidence.*Relevance|3-sentence', 'Semantic Chunking', 'chunking'),
            # Numeric Specificity
            (r'Numeric Specific|concrete number|5\+ numbers', 'Numeric Specificity', 'numeric'),
            # Quotability
            (r'Quotab|40-60 word|self-contained', 'Quotability', 'quotable'),
            # Multi-Format
            (r'Multi-Format|bullet list|comparison table', 'Multi-Format Content', 'format'),
            # Local Proof
            (r'Local Proof|neighborhood|landmark|Google Maps', 'Local Proof', 'local'),
            # Voice Search
            (r'Voice Search|speakable|alt text', 'Voice Search Optimization', 'voice-search'),
            # Schema
            (r'Schema.*Align|structured data|JSON-LD', 'Schema Alignment', 'schema'),
            # Freshness
            (r'Freshness|dateModified|temporal signal', 'Freshness & Temporal', 'freshness'),
            # E-E-A-T
            (r'E-E-A-T|Experience.*Expertise|YMYL', 'E-E-A-T Signals', 'eeat'),
            # GEO Quality
            (r'GEO.*Quality|10-point|Quality Checklist', 'GEO Quality', 'geo'),
        ]
        
        import re
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            for pattern, category, rule_type in rule_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Extract context (surrounding lines)
                    start = max(0, i - 2)
                    end = min(len(lines), i + 10)
                    context = '\n'.join(lines[start:end])
                    
                    rule_id = f"{rule_type}-{hashlib.md5(context.encode()).hexdigest()[:8]}"
                    
                    rules.append({
                        'rule_id': rule_id,
                        'rule_name': line[:200].strip(),
                        'rule_category': category,
                        'rule_description': context[:2000],
                        'source_document': source_file,
                        'source_section': lines[max(0, i-5):i+1][-1] if i > 0 else 'Start'
                    })
        
        return rules
    
    def ingest_document(self, filepath: str) -> Dict:
        """Ingest a single document into the knowledge graph"""
        filename = Path(filepath).name
        logger.info(f"Ingesting: {filename}")
        
        # Get document metadata
        doc_meta = self.source_docs.get(filename, {
            'type': 'unknown',
            'domain': 'general',
            'priority': 'P3',
            'description': filename
        })
        
        # Read content
        content = self.read_document(filepath)
        if not content:
            logger.warning(f"Could not read: {filename}")
            return {'status': 'failed', 'reason': 'unreadable'}
        
        # Generate file hash
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Chunk content
        chunks = self.chunk_content(content)
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Extract rules
        rules = self.extract_rules_from_content(content, filename)
        logger.info(f"  Extracted {len(rules)} rules")
        
        cursor = self.conn.cursor()
        
        # Register document
        cursor.execute("""
            INSERT INTO ingested_documents 
            (filename, file_hash, doc_type, domain, priority, description, chunk_count, rules_extracted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (filename) DO UPDATE SET
                file_hash = EXCLUDED.file_hash,
                chunk_count = EXCLUDED.chunk_count,
                rules_extracted = EXCLUDED.rules_extracted,
                last_updated = NOW()
        """, (
            filename, file_hash, doc_meta['type'], doc_meta['domain'],
            doc_meta['priority'], doc_meta['description'],
            len(chunks), len(rules)
        ))
        
        # Insert chunks
        chunks_inserted = 0
        for chunk in chunks:
            chunk_hash = hashlib.md5(chunk['content'].encode()).hexdigest()
            embedding = self.generate_embedding(chunk['content'])
            
            try:
                cursor.execute("""
                    INSERT INTO knowledge_chunks
                    (source_file, chunk_hash, content, content_type, domain, priority,
                     section_title, chunk_index, word_count, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_hash) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = NOW()
                """, (
                    filename, chunk_hash, chunk['content'],
                    doc_meta['type'], doc_meta['domain'], doc_meta['priority'],
                    chunk['section_title'], chunk['chunk_index'], chunk['word_count'],
                    embedding, json.dumps({'source': filename})
                ))
                chunks_inserted += 1
            except Exception as e:
                logger.warning(f"  Chunk insert error: {e}")
        
        # Insert rules
        rules_inserted = 0
        for rule in rules:
            try:
                cursor.execute("""
                    INSERT INTO extracted_rules
                    (rule_id, rule_name, rule_category, rule_description, source_document, source_section)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rule_id) DO NOTHING
                """, (
                    rule['rule_id'], rule['rule_name'][:255], rule['rule_category'],
                    rule['rule_description'], rule['source_document'], rule['source_section'][:500]
                ))
                rules_inserted += 1
            except Exception as e:
                logger.warning(f"  Rule insert error: {e}")
        
        self.conn.commit()
        
        return {
            'status': 'success',
            'filename': filename,
            'chunks_inserted': chunks_inserted,
            'rules_inserted': rules_inserted
        }
    
    def ingest_all(self, source_dir: str) -> Dict:
        """Ingest all documents from source directory"""
        results = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'total_chunks': 0,
            'total_rules': 0,
            'details': []
        }
        
        source_path = Path(source_dir)
        
        for filename in self.source_docs.keys():
            filepath = source_path / filename
            if filepath.exists():
                results['total_files'] += 1
                result = self.ingest_document(str(filepath))
                results['details'].append(result)
                
                if result['status'] == 'success':
                    results['successful'] += 1
                    results['total_chunks'] += result.get('chunks_inserted', 0)
                    results['total_rules'] += result.get('rules_inserted', 0)
                else:
                    results['failed'] += 1
            else:
                logger.warning(f"File not found: {filepath}")
        
        return results
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main ingestion entry point"""
    
    # Database configuration (from environment or defaults)
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'knowledge_graph_db'),
        'user': os.getenv('DB_USER', 'knowledge_admin'),
        'password': os.getenv('DB_PASSWORD', 'your_password_here')
    }
    
    # Source directory (where documents are stored)
    source_dir = os.getenv('SOURCE_DIR', '/opt/guru-intelligence/documents')
    
    logger.info("=" * 60)
    logger.info("GURU INTELLIGENCE KNOWLEDGE INGESTION")
    logger.info("=" * 60)
    
    ingester = KnowledgeIngester(db_config)
    
    try:
        ingester.connect()
        ingester.create_tables()
        ingester.init_embedder()
        
        results = ingester.ingest_all(source_dir)
        
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info(f"  Files processed: {results['total_files']}")
        logger.info(f"  Successful: {results['successful']}")
        logger.info(f"  Failed: {results['failed']}")
        logger.info(f"  Total chunks: {results['total_chunks']}")
        logger.info(f"  Total rules: {results['total_rules']}")
        logger.info("=" * 60)
        
        return results
        
    finally:
        ingester.close()


if __name__ == '__main__':
    main()
