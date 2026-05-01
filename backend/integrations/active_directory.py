from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ADUser:
    """Active Directory User representation"""
    def __init__(
        self,
        email: str,
        full_name: str,
        department: str,
        organization: str,
        title: str,
        is_active: bool = True
    ):
        self.email = email
        self.full_name = full_name
        self.department = department
        self.organization = organization
        self.title = title
        self.is_active = is_active

    def to_dict(self) -> Dict:
        return {
            'email': self.email,
            'full_name': self.full_name,
            'department': self.department,
            'organization': self.organization,
            'title': self.title,
            'is_active': self.is_active
        }


class ActiveDirectoryIntegration:
    """
    Mock integration with Active Directory

    In production, this would use python-ldap3 or similar to connect to actual AD
    """

    def __init__(self, server: str = "ldap://example.com", base_dn: str = "DC=example,DC=com"):
        self.server = server
        self.base_dn = base_dn
        self.connected = False
        logger.info(f"Initialized AD integration (Mock mode) - Server: {server}")

    async def connect(self) -> bool:
        """
        Connect to Active Directory

        Mock implementation - always succeeds
        In production: Use ldap3.Connection
        """
        logger.info("Connecting to Active Directory (Mock)")
        self.connected = True
        return True

    async def disconnect(self):
        """Disconnect from Active Directory"""
        logger.info("Disconnecting from Active Directory (Mock)")
        self.connected = False

    async def get_all_users(
        self,
        organization_filter: Optional[str] = None,
        department_filter: Optional[str] = None,
        only_active: bool = True
    ) -> List[ADUser]:
        """
        Get all users from Active Directory

        Mock implementation returns sample data
        In production: Query LDAP with appropriate filters
        """
        logger.info(
            f"Fetching users from AD (Mock) - "
            f"org={organization_filter}, dept={department_filter}, active={only_active}"
        )

        # Mock data - government employees
        mock_users = [
            ADUser(
                email="director@ministry.gov.ru",
                full_name="Иванов Иван Иванович",
                department="Управление информационных технологий",
                organization="Министерство цифрового развития",
                title="Директор департамента",
                is_active=True
            ),
            ADUser(
                email="security@ministry.gov.ru",
                full_name="Петров Петр Петрович",
                department="Отдел информационной безопасности",
                organization="Министерство цифрового развития",
                title="Начальник отдела",
                is_active=True
            ),
            ADUser(
                email="developer@ministry.gov.ru",
                full_name="Сидоров Сидор Сидорович",
                department="Управление информационных технологий",
                organization="Министерство цифрового развития",
                title="Ведущий разработчик",
                is_active=True
            ),
            ADUser(
                email="admin@fsb.gov.ru",
                full_name="Алексеев Алексей Алексеевич",
                department="Управление кибербезопасности",
                organization="ФСБ России",
                title="Администратор систем",
                is_active=True
            ),
            ADUser(
                email="analyst@fsb.gov.ru",
                full_name="Михайлов Михаил Михайлович",
                department="Аналитический отдел",
                organization="ФСБ России",
                title="Аналитик",
                is_active=True
            ),
            ADUser(
                email="old.user@ministry.gov.ru",
                full_name="Устаревский Устарел Устаревич",
                department="Архивный отдел",
                organization="Министерство цифрового развития",
                title="Архивариус",
                is_active=False
            ),
        ]

        # Apply filters
        filtered_users = mock_users

        if only_active:
            filtered_users = [u for u in filtered_users if u.is_active]

        if organization_filter:
            filtered_users = [
                u for u in filtered_users
                if organization_filter.lower() in u.organization.lower()
            ]

        if department_filter:
            filtered_users = [
                u for u in filtered_users
                if department_filter.lower() in u.department.lower()
            ]

        logger.info(f"Returning {len(filtered_users)} users from AD (Mock)")

        return filtered_users

    async def get_user_by_email(self, email: str) -> Optional[ADUser]:
        """
        Get specific user by email

        Mock implementation searches in sample data
        In production: LDAP query with email filter
        """
        logger.info(f"Fetching user {email} from AD (Mock)")

        all_users = await self.get_all_users(only_active=False)

        for user in all_users:
            if user.email.lower() == email.lower():
                return user

        return None

    async def import_government_emails(
        self,
        organizations: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Import government employee emails for registry

        Args:
            organizations: List of organization names to filter by

        Returns:
            List of user data dictionaries ready for registry import
        """
        logger.info(f"Importing government emails (Mock) - orgs: {organizations}")

        all_users = await self.get_all_users(only_active=True)

        # Filter by organizations if specified
        if organizations:
            filtered_users = []
            for user in all_users:
                for org in organizations:
                    if org.lower() in user.organization.lower():
                        filtered_users.append(user)
                        break
            users_to_import = filtered_users
        else:
            users_to_import = all_users

        # Convert to registry format
        registry_data = []
        for user in users_to_import:
            domain = user.email.split('@')[1] if '@' in user.email else ''

            registry_data.append({
                'email_address': user.email,
                'domain': domain,
                'organization_name': user.organization,
                'full_name': user.full_name,
                'department': user.department,
                'title': user.title,
                'source': 'active_directory'
            })

        logger.info(f"Prepared {len(registry_data)} entries for import from AD")

        return registry_data


# Mock EGRUL (Russian business registry) integration
class EGRULIntegration:
    """
    Mock integration with EGRUL (Единый государственный реестр юридических лиц)

    In production, this would use actual EGRUL API
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        logger.info("Initialized EGRUL integration (Mock mode)")

    async def search_contractors(
        self,
        inn_list: Optional[List[str]] = None,
        organization_type: str = "government_contractor"
    ) -> List[Dict]:
        """
        Search for contractors in EGRUL

        Mock implementation returns sample contractor data
        In production: Call EGRUL API
        """
        logger.info(f"Searching contractors in EGRUL (Mock) - type: {organization_type}")

        # Mock contractor data
        mock_contractors = [
            {
                'inn': '7700000001',
                'ogrn': '1027700000001',
                'organization_name': 'ООО "Техно-Безопасность"',
                'email': 'info@technosec.ru',
                'domain': 'technosec.ru',
                'contact_email': 'sales@technosec.ru',
                'type': 'government_contractor',
                'is_active': True,
                'contract_count': 15
            },
            {
                'inn': '7700000002',
                'ogrn': '1027700000002',
                'organization_name': 'ЗАО "Системы защиты информации"',
                'email': 'contact@infosec-systems.ru',
                'domain': 'infosec-systems.ru',
                'contact_email': 'manager@infosec-systems.ru',
                'type': 'government_contractor',
                'is_active': True,
                'contract_count': 8
            },
            {
                'inn': '7700000003',
                'ogrn': '1027700000003',
                'organization_name': 'АО "КиберЩит"',
                'email': 'office@cybershield.ru',
                'domain': 'cybershield.ru',
                'contact_email': 'contracts@cybershield.ru',
                'type': 'government_contractor',
                'is_active': True,
                'contract_count': 22
            },
        ]

        # Filter by INN if provided
        if inn_list:
            filtered = [c for c in mock_contractors if c['inn'] in inn_list]
        else:
            filtered = mock_contractors

        logger.info(f"Found {len(filtered)} contractors in EGRUL (Mock)")

        return filtered

    async def import_contractor_emails(
        self,
        min_contract_count: int = 5
    ) -> List[Dict]:
        """
        Import contractor emails for registry

        Args:
            min_contract_count: Minimum number of government contracts

        Returns:
            List of contractor data for registry import
        """
        logger.info(f"Importing contractor emails (Mock) - min_contracts: {min_contract_count}")

        contractors = await self.search_contractors()

        # Filter by contract count
        qualified = [c for c in contractors if c['contract_count'] >= min_contract_count]

        # Convert to registry format
        registry_data = []
        for contractor in qualified:
            # Add primary contact email
            registry_data.append({
                'email_address': contractor['contact_email'],
                'domain': contractor['domain'],
                'organization_name': contractor['organization_name'],
                'inn': contractor['inn'],
                'ogrn': contractor['ogrn'],
                'contract_count': contractor['contract_count'],
                'source': 'egrul'
            })

        logger.info(f"Prepared {len(registry_data)} contractor entries for import")

        return registry_data
