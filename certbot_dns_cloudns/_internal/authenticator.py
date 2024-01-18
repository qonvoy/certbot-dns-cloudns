"""DNS Authenticator using CLouDNS API."""
import functools
import logging

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common

from certbot_dns_cloudns._internal.client import ClouDNSClient
from certbot_dns_cloudns._internal.resolve import resolve_alias

logger = logging.getLogger(__name__)

DEFAULT_NETWORK_TIMEOUT = 45


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator using CLouDNS API
    This Authenticator uses the ClouDNS API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record '
                   '(if you are using ClouDNS for DNS).')
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=60
        )
        add('credentials', help='ClouDNS credentials INI file.')
        add('nameserver', help='The nameserver used to resolve CNAME aliases.')

    @staticmethod
    def more_info():
        return ('This plugin configures a DNS TXT record to respond to a '
                'dns-01 challenge using the ClouDNS API.')

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'ClouDNS credentials INI file',
            {
                'auth-password': 'API password',
            },
            self._validate_user_ids
        )

    @staticmethod
    def _validate_user_ids(credentials):
        required_keys = ('auth-id', 'sub-auth-id', 'sub-auth-user')
        user_count = sum(int(credentials.conf(key) is not None)
                         for key in required_keys)

        if user_count != 1:
            raise errors.PluginError(
                f"{'Missing' if user_count == 0 else 'Unexpected'} "
                f"{'property' if user_count <= 2 else 'properties'} in "
                f"credentials configuration file "
                f"{credentials.confobj.filename}:\n * Expected exactly one of "
                f"{', '.join(map(credentials.mapper, required_keys))}; "
                f"found {user_count}."
            )

    def _perform(self, _domain, validation_name, validation):
        self._get_client().add_txt_record(
            _domain, self._resolve_alias(validation_name), validation, self.ttl
        )

    def _cleanup(self, _domain, validation_name, validation):
        self._get_client().del_txt_record(
            _domain, self._resolve_alias(validation_name), validation
        )

    def _resolve_alias(self, validation_name):
        return resolve_alias(validation_name,
                             nameserver=self.conf('nameserver'))

    @functools.lru_cache(maxsize=None)
    def _get_client(self):
        return ClouDNSClient(self.credentials)
