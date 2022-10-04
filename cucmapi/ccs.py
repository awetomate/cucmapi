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


class ccs(object):
    """
    The Control Center Services API class sets up the connection to the call manager with methods that
    support service activation, service deactivation, gathering service lists, and service start, stop, and restart.
    This class contains methods for both the 'Control Center Services' and the 'Control Center Services Extended' APIs.
    Tested with Python 3.8.10 and 3.9.5
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
        :param username: axl username
        :param password: axl password
        :param cucm: fqdn or IP address of CUCM
        :param cucm_version: CUCM version
        """

        wsdl = f"https://{cucm}:8443/controlcenterservice2/services/ControlCenterServices?wsdl"
        wsdl_ex = f"https://{cucm}:8443/controlcenterservice2/services/ControlCenterServicesEx?wsdl"
        
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
        ccs_client = Client(wsdl, settings=settings, transport=transport)
        css_client_ex = Client(wsdl_ex, settings=settings, transport=transport)

        self.wsdl = wsdl
        self.wsdl_ex = wsdl_ex
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)
        self.client = ccs_client.create_service("{http://schemas.cisco.com/ast/soap}ControlCenterServicesBinding", f"https://{cucm}:8443/controlcenterservice2/services/ControlCenterServices")
        self.client_ex = css_client_ex.create_service("{http://schemas.cisco.com/ast/soap}ControlCenterServicesExBinding", f"https://{cucm}:8443/controlcenterservice2/services/ControlCenterServicesEx")

    def getProductInformationList(self, ServiceInfo=""):
        """
        Lists all product and service information including ProductID, ServiceName, and DependentServices
        for one server. Query each server in a cluster individually to get their info.

        :param ServiceInfo: ignore. All information is returned regardless of the value set, incl. a value of blank
        :return: result list
        """
        try:
            return self.client.getProductInformationList(ServiceInfo)
        except Fault as e:
            return e

    def soapDoControlServices(self, node, action, services):
        """
        Method to start or stop a list of services.
        The method does not allow clients to stop non-stop services such as 'Cisco DB' and 'Cisco Tomcat'.
        This method also does not allow clients to provide an empty list of services.

        Names of the services can be found using the soapGetServiceStatus() or get_production_information() methods.

        :param node: name of the local node
        :param action: action to perform. Can be 'Start', 'Stop', or 'Restart'
        :param services: list with names of the services to start, stop, or restart. Mustn't be empty.
        :return: result dict
        """
        ControlServiceRequest = {
            "NodeName": node,
            "ControlType": action,
            "ServiceList": {
                "item": services
            }
        }

        try:
            return self.client.soapDoControlServices(ControlServiceRequest)
        except Fault as e:
            return e
    
    def soapDoServiceDeployment(self, node, action, services):
        """
        Method to deploy or undeploy (activate/deactivate) a deployable service, where a deployable service 
        has the Deployable attribute set to True in the response from soapGetServiceStatus() method.
        This method also does not allow clients to provide an empty list of services.

        Names of the services can be found using the soapGetServiceStatus() or get_production_information() methods.

        :param node: name of the local node
        :param action: action to perform. Can be 'Deploy' or 'UnDeploy'
        :param services: list with names of the services to deploy or undeploy. Mustn't be empty.
        :return: result dict
        """
        DeploymentServiceRequest = {
            "NodeName": node,
            "DeployType": action,
            "ServiceList": {
                "item": services
            }
        }

        try:
            return self.client.soapDoServiceDeployment(DeploymentServiceRequest)
        except Fault as e:
            return e

    def soapGetServiceStatus(self, ServiceStatus=""):
        """
        Perform a status query for a service. Returns information to determine if a
        service is started or stopped, and activated or deactivated. Response also
        includes a timestamp for the last time it was started.

        :param ServiceStatus: leave blank to get all services or provide list with service names
        :return: result list
        """
        try:
            return self.client.soapGetServiceStatus(ServiceStatus)["ServiceInfoList"]["item"]
        except Fault as e:
            return e

    def soapGetStaticServiceList(self, ServiceInformationResponse=""):
        """
        Perform a query of all static specifications for services in CUCM.

        :param ServiceInformationResponse: ignore. All information is returned regardless of the value set, incl. a value of blank
        :return: result list
        """
        try:
            return self.client.soapGetStaticServiceList(ServiceInformationResponse)["item"]
        except Fault as e:
            return e

    def getFileDirectoryList(self, path):
        """
        This method lists the names of the files contained in the specified directory. 
        The files are not downloaded. Use this method prior to using the DimeGetFile Service API.

        Use LogCollectionPort get_log_files() to return the path for the service.

        :param path: directory path of the files. e.g. '/var/log/active/tomcat/logs/ccmservice'
        :return: result list
        """
        try:
            return self.client_ex.getFileDirectoryList(DirectoryPath=path)
        except Fault as e:
            return e

    def getStaticServiceListExtended(self, ServiceInformationResponse=""):
        """
        This method is an extended version of soapGetStaticServiceList().
        soapGetStaticServiceList() provides a detailed list of all the services.
        getStaticServiceListExtended() includes ProductID and Restriction information in addition
        
        :param ServiceInformationResponse: ignore. All information is returned regardless of the value set, incl. a value of blank
        :return: result list
        """
        try:
            return self.client_ex.getStaticServiceListExtended(ServiceInformationResponse)["Services"]["item"]
        except Fault as e:
            return e

    def soapDoControlServicesEx(self, pid, dependencies, action, services):
        """
        Method to start or stop a list of services in UCM and ELM (10.0 and above).
        The method does not allow clients to stop non-stop services such as 'Cisco DB' and 'Cisco Tomcat'.
        This method also does not allow clients to provide an empty list of services.

        Service Names, ProductId and dependencies can be found using the getStaticServiceListExtended() method.

        :param pid: ProductID, name of the product a service is associated to. Can be 'CallManager', 'Elm', or 'Common'
        :param dependencies: Some services are depended on others. 
                             Use 'Enforce' to start/restart dependent services.
                             Use 'None' if there are no dependent services 
        :param action: action to perform. Can be 'Start', 'Stop', or 'Restart'
        :param services: list with names of the services to start, stop, or restart. Mustn't be empty.
        :return: result dict
        """
        ControlServiceRequestEx = {
            "ProductId": pid,
            "DependencyType": dependencies,
            "ControlType": action,
            "ServiceList": {
                "item": services
            }
        }

        try:
            return self.client_ex.soapDoControlServicesEx(ControlServiceRequestEx)
        except Fault as e:
            return e
