import os
import logging
from typing import Optional, List, Dict, Any
from elasticsearch import AsyncElasticsearch
from datetime import datetime

logger = logging.getLogger(__name__)

# Elasticsearch configuration
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTICSEARCH_TIMEOUT = int(os.getenv("ELASTICSEARCH_TIMEOUT", "30"))


class ElasticsearchClient:
    """
    Async Elasticsearch client wrapper for SPEAR-GUARD
    Handles full-text search, analytics, and threat intelligence indexing
    """

    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.indices = {
            "emails": "spearguard_emails",
            "threats": "spearguard_threats",
            "reports": "spearguard_reports",
            "analytics": "spearguard_analytics"
        }

    async def connect(self):
        """
        Initialize Elasticsearch connection
        """
        if not self.client:
            self.client = AsyncElasticsearch(
                hosts=[ELASTICSEARCH_URL],
                request_timeout=ELASTICSEARCH_TIMEOUT,
            )
            logger.info(f"Elasticsearch connected: {ELASTICSEARCH_URL}")

            # Create indices if they don't exist
            await self._create_indices()

    async def close(self):
        """
        Close Elasticsearch connection
        """
        if self.client:
            await self.client.close()
            logger.info("Elasticsearch connection closed")

    async def ping(self) -> bool:
        """
        Check if Elasticsearch is alive
        """
        if not self.client:
            await self.connect()
        return await self.client.ping()

    async def _create_indices(self):
        """
        Create indices with mappings if they don't exist
        """
        # Email analysis index
        email_mapping = {
            "mappings": {
                "properties": {
                    "message_id": {"type": "keyword"},
                    "from_address": {"type": "keyword"},
                    "from_domain": {"type": "keyword"},
                    "to_address": {"type": "keyword"},
                    "subject": {"type": "text", "analyzer": "standard"},
                    "body": {"type": "text", "analyzer": "standard"},
                    "risk_score": {"type": "float"},
                    "status": {"type": "keyword"},
                    "analyzed_at": {"type": "date"},
                    "user_id": {"type": "integer"},
                    "headers": {"type": "object"},
                    "technical_indicators": {
                        "properties": {
                            "spf_pass": {"type": "boolean"},
                            "dkim_pass": {"type": "boolean"},
                            "dmarc_pass": {"type": "boolean"}
                        }
                    },
                    "linguistic_indicators": {"type": "object"},
                    "urls": {"type": "keyword"},
                    "attachments": {"type": "nested"}
                }
            }
        }

        # Threat intelligence index
        threat_mapping = {
            "mappings": {
                "properties": {
                    "threat_type": {"type": "keyword"},
                    "severity": {"type": "keyword"},
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "indicators": {"type": "nested"},
                    "source_addresses": {"type": "keyword"},
                    "affected_users": {"type": "integer"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

        # Create indices
        for index_name, mapping in [
            (self.indices["emails"], email_mapping),
            (self.indices["threats"], threat_mapping)
        ]:
            if not await self.client.indices.exists(index=index_name):
                await self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"Created index: {index_name}")

    # Index operations
    async def index_document(
        self,
        index: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index a document
        """
        if not self.client:
            await self.connect()

        index_name = self.indices.get(index, index)

        result = await self.client.index(
            index=index_name,
            id=doc_id,
            body=document
        )
        return result

    async def get_document(
        self,
        index: str,
        doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID
        """
        if not self.client:
            await self.connect()

        index_name = self.indices.get(index, index)

        try:
            result = await self.client.get(index=index_name, id=doc_id)
            return result["_source"]
        except Exception as e:
            logger.error(f"Document not found: {e}")
            return None

    async def update_document(
        self,
        index: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a document
        """
        if not self.client:
            await self.connect()

        index_name = self.indices.get(index, index)

        result = await self.client.update(
            index=index_name,
            id=doc_id,
            body={"doc": document}
        )
        return result

    async def delete_document(
        self,
        index: str,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        Delete a document
        """
        if not self.client:
            await self.connect()

        index_name = self.indices.get(index, index)

        result = await self.client.delete(index=index_name, id=doc_id)
        return result

    # Search operations
    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Search documents
        """
        if not self.client:
            await self.connect()

        index_name = self.indices.get(index, index)

        body = {"query": query, "size": size, "from": from_}
        if sort:
            body["sort"] = sort

        result = await self.client.search(index=index_name, body=body)
        return result

    # SPEAR-GUARD specific methods
    async def index_email_analysis(
        self,
        message_id: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Index email analysis result
        """
        document = {
            "message_id": message_id,
            "indexed_at": datetime.utcnow().isoformat(),
            **analysis
        }
        return await self.index_document("emails", document, doc_id=message_id)

    async def search_emails_by_sender(
        self,
        sender: str,
        size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search emails by sender address
        """
        query = {
            "match": {
                "from_address": sender
            }
        }
        result = await self.search("emails", query, size=size)
        return [hit["_source"] for hit in result["hits"]["hits"]]

    async def search_emails_by_risk(
        self,
        min_risk: float,
        max_risk: float = 100.0,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search emails by risk score range
        """
        query = {
            "range": {
                "risk_score": {
                    "gte": min_risk,
                    "lte": max_risk
                }
            }
        }
        sort = [{"risk_score": {"order": "desc"}}]
        result = await self.search("emails", query, size=size, sort=sort)
        return [hit["_source"] for hit in result["hits"]["hits"]]

    async def search_threats_by_severity(
        self,
        severity: str,
        status: str = "active",
        size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search threats by severity and status
        """
        query = {
            "bool": {
                "must": [
                    {"match": {"severity": severity}},
                    {"match": {"status": status}}
                ]
            }
        }
        sort = [{"created_at": {"order": "desc"}}]
        result = await self.search("threats", query, size=size, sort=sort)
        return [hit["_source"] for hit in result["hits"]["hits"]]

    async def full_text_search(
        self,
        query_string: str,
        index: str = "emails",
        size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across subject and body
        """
        query = {
            "multi_match": {
                "query": query_string,
                "fields": ["subject^2", "body"],
                "type": "best_fields"
            }
        }
        result = await self.search(index, query, size=size)
        return [hit["_source"] for hit in result["hits"]["hits"]]

    async def get_analytics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get analytics aggregations
        """
        if not self.client:
            await self.connect()

        query = {
            "range": {
                "analyzed_at": {
                    "gte": start_date.isoformat(),
                    "lte": end_date.isoformat()
                }
            }
        }

        aggs = {
            "status_distribution": {
                "terms": {"field": "status"}
            },
            "risk_histogram": {
                "histogram": {
                    "field": "risk_score",
                    "interval": 10
                }
            },
            "top_senders": {
                "terms": {
                    "field": "from_domain",
                    "size": 10
                }
            }
        }

        result = await self.client.search(
            index=self.indices["emails"],
            body={"query": query, "aggs": aggs, "size": 0}
        )

        return result.get("aggregations", {})


# Global Elasticsearch client instance
es_client = ElasticsearchClient()


# Helper functions
async def get_elasticsearch() -> ElasticsearchClient:
    """
    Dependency for FastAPI to get Elasticsearch client
    """
    if not es_client.client:
        await es_client.connect()
    return es_client


if __name__ == "__main__":
    import asyncio

    async def test_elasticsearch():
        # Test connection
        await es_client.connect()
        print("✓ Elasticsearch connected")

        # Test ping
        pong = await es_client.ping()
        print(f"✓ Ping: {pong}")

        # Test indexing
        test_email = {
            "message_id": "test123",
            "from_address": "test@example.com",
            "to_address": "user@gov.ru",
            "subject": "Test email",
            "risk_score": 25.5,
            "status": "safe"
        }
        result = await es_client.index_email_analysis("test123", test_email)
        print(f"✓ Indexed document: {result['result']}")

        # Test search
        emails = await es_client.search_emails_by_sender("test@example.com")
        print(f"✓ Found {len(emails)} emails")

        # Close connection
        await es_client.close()
        print("✓ Elasticsearch connection closed")

    asyncio.run(test_elasticsearch())
