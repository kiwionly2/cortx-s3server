"""This is utility class used for Authorization."""
import string
import hmac
import hashlib
from hashlib import sha1, sha256
import urllib
import datetime
from s3backgrounddelete.eos_core_config import EOSCoreConfig

class EOSCoreUtil(object):
   """Generate Authorization headers to validate requests."""
   _config = None

   def __init__(self, config):
        """Initialise config."""
        if (config is None):
            self._config = EOSCoreConfig()
        else:
            self._config = config

   def create_canonical_request(self, method, canonical_uri, canonical_query_string, body, epoch_t, host):
       """Create canonical request based on uri and query string."""
       signed_headers = 'host;x-amz-date'
       payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
       canonical_headers = 'host:' + host + '\n' + \
           'x-amz-date:' + self.get_amz_timestamp(epoch_t) + '\n'
       canonical_request = method + '\n' + canonical_uri + '\n' + canonical_query_string + '\n' + \
           canonical_headers + '\n' + signed_headers + '\n' + payload_hash
       return canonical_request

   def sign(self, key, msg):
       """Return hmac value based on key and msg."""
       return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

   def getV4SignatureKey(self, key, dateStamp, regionName, serviceName):
       """Generate v4SignatureKey based on key, datestamp, region and service name."""
       kDate = self.sign(('AWS4' + key).encode('utf-8'), dateStamp)
       kRegion = self.sign(kDate, regionName)
       kService = self.sign(kRegion, serviceName)
       kSigning = self.sign(kService, 'aws4_request')
       return kSigning

   def create_string_to_sign_v4(self, method='', canonical_uri='', canonical_query_string='', body='', epoch_t='',
                                algorithm='', host='', service='', region=''):
       """Generates string_to_sign for authorization key generation."""

       canonical_request = self.create_canonical_request(method, canonical_uri,canonical_query_string,
                                                    body, epoch_t, host)
       credential_scope = self.get_date(epoch_t) + '/' + \
           region + '/' + service + '/' + 'aws4_request'

       string_to_sign = algorithm + '\n' + self.get_amz_timestamp(epoch_t) + '\n' + credential_scope \
           + '\n' + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
       return string_to_sign

   def sign_request_v4(self, method=None, canonical_uri='/', canonical_query_string='', body='', epoch_t='',
                       host='', service='', region=''):
       """Generate authorization request header."""
       if method is None:
           print("method can not be null")
           return None
       credential_scope = self.get_date(epoch_t) + '/' + region + \
           '/' + service + '/' + 'aws4_request'

       signed_headers = 'host;x-amz-date'

       algorithm = 'AWS4-HMAC-SHA256'

       access_key = self._config.get_eos_core_access_key()
       secret_key = self._config.get_eos_core_secret_key()

       string_to_sign = self.create_string_to_sign_v4(method, canonical_uri, canonical_query_string, body, epoch_t,
                                                 algorithm, host, service, region)

       signing_key = self.getV4SignatureKey(
           secret_key, self.get_date(epoch_t), region, service)

       signature = hmac.new(
           signing_key,
           (string_to_sign).encode('utf-8'),
           hashlib.sha256).hexdigest()

       authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
           credential_scope + ', ' + 'SignedHeaders=' + signed_headers + \
           ', ' + 'Signature=' + signature
       return authorization_header

   def get_date(self, epoch_t):
       """Return date in Ymd format."""
       return epoch_t.strftime('%Y%m%d')

   def get_amz_timestamp(self, epoch_t):
       """Return timestamp in YMDTHMSZ format."""
       return epoch_t.strftime('%Y%m%dT%H%M%SZ')

   def prepare_signed_header(self, http_request, request_uri, query_params, body):
       """Generate headers used for authorization requests."""
       url_parse_result  = urllib.parse.urlparse(self._config.get_eos_core_endpoint())
       epoch_t = datetime.datetime.utcnow();
       headers = {'content-type': 'application/x-www-form-urlencoded',
               'Accept': 'text/plain'}
       headers['Authorization'] = self.sign_request_v4(http_request, request_uri ,query_params, body, epoch_t, url_parse_result.netloc,
           self._config.get_eos_core_service(), self._config.get_eos_core_region());
       headers['X-Amz-Date'] = self.get_amz_timestamp(epoch_t);
       return headers
