import re
import requests
import urllib3
from pathlib import Path
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.cache import SqliteCache
from zeep.exceptions import Fault
from zeep.transports import Transport


class log(object):
    """
    The Log Collection service and the File Retrieval (DimeGetFile) service provide 
    the ability to list and retrieve trace or log files from CUCM on-demand.
    Tested with Python 3.8.10 and 3.9.5
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
        :param username: axl username
        :param password: axl password
        :param cucm: fqdn or IP address of CUCM
        :param cucm_version: CUCM version
        """

        wsdl = f"https://{cucm}:8443/logcollectionservice2/services/LogCollectionPortTypeService?wsdl"
        
        # create a session
        session = Session()

        # disable certificate verification and insecure request warnings
        session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        requests.packages.urllib3.disable_warnings( )

        # to enable SSL cert verification, copy the CUCM tomcat .pem file and uncomment the following lines
        # CERT = 'cucmtomcat.pem'
        # session.verify = CERT

        session.auth = HTTPBasicAuth(username, password)
        transport = Transport(session=session, timeout=10, cache=SqliteCache())
        settings = Settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True)
        log_client = Client(wsdl, settings=settings, transport=transport) 

        self.wsdl = wsdl
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)
        self.client = log_client.create_service("{http://schemas.cisco.com/ast/soap}LogCollectionPortSoapBinding", f"https://{cucm}:8443/logcollectionservice2/services/LogCollectionPortTypeService")

    def listNodeServiceLogs(self):
        """
        This method returns the node names in the cluster and the lists of associated service names.

        :param ListRequest: value needs to be left empty
        :return: result list
        """
        try:
            return self.client.listNodeServiceLogs(ListRequest={})
        except Fault as e:
            return e

    def selectLogFiles(self, to_date="", from_date="", service_logs=[], 
                         system_logs=[], job_type="DownloadtoClient", sftp_port="", sftp_ip="", 
                         sftp_user="", sftp_pass="", sftp_directory=""
    ):
        """
        CAUTION: Function returns all(!) log files, ignoring any time range filtering.
        Relative time range filtering is not currently supported - RelText and RelTime are ignored.
        The fixed time range filtering does not seem to work at all.

        Lists available service log files, or requests 'push' delivery of service log files 
        based on a selection criteria.

        Log names can be found using the listNodeServiceLogs() method.

        If the JobType element is set to DownloadtoClient, then the service will simply retrieve 
        a list of matching available log files. Note: no files are actually downloaded.
        
        If the JobType element is set to PushtoSFTPServer, then the system will attempt to 
        sign into the SSH-FTP server with the provided credentials and deliver the log files.

        Note: Relative time range filtering is not currently supported - RelText and RelTime are ignored
        https://developer.cisco.com/docs/sxml/#!log-collection-and-dimegetfileservice-api-reference/log-collection-api

        :return: result dict
        """
        FileSelectionCriteria = {
            'ServiceLogs': service_logs,
            'SystemLogs': system_logs,
            'SearchStr': '',
            'Frequency': 'OnDemand',
            'JobType': job_type,
            'ToDate': '',
            'FromDate': '',
            'TimeZone': '',
            'RelText': 'Minutes',
            'RelTime': 60,
            'Port': sftp_port,
            'IPAddress': sftp_ip,
            'UserName': sftp_user,
            'Password': sftp_pass,
            'ZipInfo': False,
            'RemoteFolder': sftp_directory
        }
        
        try:
            return self.client.selectLogFiles(FileSelectionCriteria=FileSelectionCriteria)["Node"]["ServiceList"]
        except Fault as e:
            return e

    def GetOneFile(self, file_name):
        """
        This method uses the DimeGetFileService API to retrieve either a server
        or system logfile through the standard Direct Internet Message Encapsulation
        (DIME) protocol.

        The selectLogFiles() method returns the absolute file name of log files.

        :param file_name: The absolute file name of the file to be collected
                e.g. var/log/active/tomcat/logs/ccmservice/ccmservice00010.log
        :return: bytes object 
        
        """
        try:
            return self.client.GetOneFile(file_name)
        except Fault as e:
            return e
