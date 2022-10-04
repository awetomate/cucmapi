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


class cdr(object):
    """
    The Call Detail Records on Demand (CDRonDemand) SOAP service is a public SOAP/HTTPS 
    interface exposed to third-party applications to allow queries of the Cisco 
    Unified Communications Manager (Unified CM) Call Detail Records (CDR) Repository Node.
    The CDRonDemand Service allows applications to obtain CDR files in a two-step process:
    1. The application requests a list of CDR files based on a specific time interval.
    2. The application then requests one CDR file from the CDR file list. 
       The file is returned via a FTP or SSH-FTP session.
       
    To retrieve individual CDR files as needed, use the CDRonDemand API. However, 
    to retrieve all of the CDR files all of the time, it is recommended to use 
    the CDR Repository Manager to directly FTP or SSH-FTP the files to your server
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
        :param username: axl username
        :param password: axl password
        :param cucm: fqdn or IP address of CUCM
        :param cucm_version: CUCM version
        """

        wsdl = f"https://{cucm}:8443/CDRonDemandService2/services/CDRonDemandService?wsdl"
        
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
        cdr_client = Client(wsdl, settings=settings, transport=transport) 

        self.wsdl = wsdl
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)
        self.client = cdr_client.create_service("{http://schemas.cisco.com/ast/soap}CDRonDemandSoapBinding", f"https://{cucm}:8443/CDRonDemandService2/services/CDRonDemandService")

    def get_file(self, sftp_ip, sftp_user, sftp_pass, sftp_directory, file_name, sftp="true"):
        """
        This method allows to request a specific CDR file that matches the specified filename. 
        The matching CDR file is sent to a server via  FTP or SFTP. 
        The only constraint is the service processes one file per request.

        :param sftp_ip: Hostname of the SFTP server
        :param sftp_user: Username for the SFTP server
        :param sftp_pass: Password for the SFTP server
        :param sftp_directory: Remote, target directory on the SFTP server
        :param file_name: Filename of the CDR file to send from CUCM to SFTP server
        :param sftp: Boolean to speficy whether to use SFTP (true) vs FTP (false)
                     Always use SFTP - leave this set to true
        :return: none if successful
        """

        try:
            return self.client.get_file(in0=sftp_ip, in1=sftp_user, in2=sftp_pass, in3=sftp_directory, in4=file_name, in5=sftp)
        except Fault as e:
            return e

    def get_file_list(self, start_time, end_time, all_files="true"):
        """
        This method allows an application to query the CDR Repository Node for a list 
        of all files that match a specified time interval. The time interval of the 
        request cannot exceed one hour. To get a list of files that span more than 
        the one hour interval allowed, multiple requests to the service must be made.

        :param start_time: Starting time in UTC for the search interval. 
                           The format is a string: YYYYMMDDHHMM
        :param end_time:   Ending time in UTC for the search interval. 
                           The format is a string: YYYYMMDDHHMM
        :param all_files:  Boolean to tell service whether to include files that 
                           were successfully sent to the specified server.
                           True = include both files (successfully sent and failed to be sent)
                           False = send only files that failed to be sent
        :return: result list
        """

        try:
            return self.client.get_file_list(in0=start_time, in1=end_time, in2=all_files)
        except Fault as e:
            return e
