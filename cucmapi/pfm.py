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


class pfm(object):
    """
    The Performance Monitoring API, also referred to as PerfMon, provides real-time 
    event feeds to monitor the status and health of Cisco Unified CM.
    - Collect and monitor PerfMon performance data either session-based or single-transaction
    - Retrieve a list of all PerfMon objects and counter names installed on a particular host
    - Retrieve a list of the current instances of a PerfMon object
    - Retrieve textual description of a PerfMon counter

    In session-based PerfMon data collection, the following related operations are used in sequence:
    - perfmonOpenSession --> perfmonOpenSession
    - perfmonAddCounter --> add_counter
    - perfmonCollectSessionData (repeated) --> perfmonCollectSessionData
    - perfmonCloseSession --> perfmonCloseSession
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
        :param username: axl username
        :param password: axl password
        :param cucm: fqdn or IP address of CUCM
        :param cucm_version: CUCM version
        """

        wsdl = f"https://{cucm}:8443/perfmonservice2/services/PerfmonService?wsdl"

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
        pfm_client = Client(wsdl, settings=settings, transport=transport) 

        self.wsdl = wsdl
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)
        self.client = pfm_client.create_service("{http://schemas.cisco.com/ast/soap}PerfmonBinding", f"https://{cucm}:8443/perfmonservice2/services/PerfmonService")

    def perfmonAddCounter(self, token, counters):
        """
        Use this method to add a list of counters to an existing session handle.

        Use 'perfmonListCounter()' method to get possible counters for an object.
        Use 'perfmonListInstance()' method to get possible instances for an object.
        
        To construct a counter name use the following format:
            \\cucm hostname\object\counter
            e.g. r"\\servername\Cisco CallManager\CallsActive" (use raw strings)

        Some objects have instances. If the value of MultiInstance returned by 'perfmonListCounter()' is true, 
        then the object has instances. To construct a counter name with an instance use the following format:
            \\cucm hostname\object(instance)\counter
            e.g. r"\\servername\Cisco Transcode Device(name-of-transcoding-resource)\ResourceTotal" (use raw strings)

        :param token: the unique session ID the 'perfmonOpenSession()' method returned
        :param counters: list of a least one counter to be added to the session handle
        :return: none if successful
        """
        counters_data = {
                    "Counter": []
        }

        for counter in counters:
            counters_data["Counter"].append(
                {
                    "Name": counter
                }
            )

        try:
            return self.client.perfmonAddCounter(SessionHandle=token, ArrayOfCounter=counters_data)
        except Fault as e:
            return e

    def perfmonCloseSession(self, token):
        """
        Use this method to close the session handle that 'perfmonOpenSession()' previously opened.

        :param token: the unique session ID the 'perfmonOpenSession()' method returned
        :return: none if successful
        """
        try:
            return self.client.perfmonCloseSession(SessionHandle=token)
        except Fault as e:
            return e

    def perfmonCollectCounterData(self, host, perfmon_object):
        """
        Returns the perfmon data for all counters that belong to an object on a 
        particular host. Unlike the session-based perfmon data collection, this 
        operation collects all data in a single request and response transaction. 
        For an object with multiple instances, data for all instances is returned.

        Use 'perfmonListCounter()' method to get a list of available objects.

        :param host: Host name or IP of target server from which to retrieve the info
        :param perfmon_object: name of the PerfMon object
        :return: result list
        """
        try:
            return self.client.perfmonCollectCounterData(Host=host, Object=perfmon_object)
        except Fault as e:
            return e

    def perfmonCollectSessionData(self, token):
        """
        Use this method to  collect the PerfMon data for all counters that have been 
        added with 'perfmonAddCounter()' to the session handle returned from 'perfmonOpenSession()'.

        :param token: the unique session ID the 'perfmonOpenSession()' method returned
        :return: result list
        """
        try:
            return self.client.perfmonCollectSessionData(SessionHandle=token)
        except Fault as e:
            return e

    def perfmonListCounter(self, host):
        """
        This method returns the list of available PerfMon objects and counters 
        on a particular host.
        No session needed.

        :param host: Host name from which to retrieve counter information
        :return: result list
        """
        try:
            return self.client.perfmonListCounter(Host=host)
        except Fault as e:
            return e

    def perfmonListInstance(self, host, perfmon_object):
        """
        This method returns a list of instances of a PerfMon object on a particular host. 
        Instances of an object can dynamically change. This operation returns the most recent list.
        No session needed.

        Use 'perfmonListCounter()' method to get a list of available objects.

        :param host: host name of the target server
        :param perfmon_object: name of the PerfMon object
        :return: result list
        """
        try:
            return self.client.perfmonListInstance(Host=host, Object=perfmon_object)
        except Fault as e:
            return e

    def perfmonOpenSession(self):
        """
        Use this method to request to obtain a session handle. The client needs 
        a session handle to do session-based PerfMon counter data collection.
        Use the returned SessionHandle token in subsequent requests.
        :return: session ID string
        """
        try:
            return self.client.perfmonOpenSession()
        except Fault as e:
            return e
  
    def perfmonQueryCounterDescription(self, counter_name):
        """
        Returns the detailed, human-readable description of the requested counter.
        No session needed.

        Use 'perfmonListCounter()' method to get possible counters for an object.
        Use 'perfmonListInstance()' method to get possible instances for an object.
        
        To construct a counter name use the following format:
            \\cucm hostname\object\counter
            e.g. r"\\servername\Cisco CallManager\CallsActive" (use raw strings)

        Some objects have instances. If the value of MultiInstance returned by 'perfmonListCounter()' is true, 
        then the object has instances. To construct a counter name with an instance use the following format:
            \\cucm hostname\object(instance)\counter
            e.g. r"\\servername\Cisco Transcode Device(name-of-transcoding-resource)\ResourceTotal" (use raw strings)

        :param counter_name: name of the counter (use raw strings or escape each backslash)
        :result: string
        """
        try:
            return self.client.perfmonQueryCounterDescription(Counter=counter_name)
        except Fault as e:
            return e
      
    def perfmonRemoveCounter(self, token, counters):
        """
        Use this method to remove a list of counters from an existing session handle.

        Use 'perfmonListCounter()' method to get possible counters for an object.
        Use 'perfmonListInstance()' method to get possible instances for an object.
        
        To construct a counter name use the following format:
            \\cucm hostname\object\counter
            e.g. r"\\servername\Cisco CallManager\CallsActive" (use raw strings)

        Some objects have instances. If the value of MultiInstance returned by 'perfmonListCounter()' is true, 
        then the object has instances. To construct a counter name with an instance use the following format:
            \\cucm hostname\object(instance)\counter
            e.g. r"\\servername\Cisco Transcode Device(name-of-transcoding-resource)\ResourceTotal" (use raw strings)

        :param token: the unique session ID the 'perfmonOpenSession()' method returned
        :param counters: list of a least one counter to be added to the session handle
        :return: none if successful
        """
        counters_data = {
                    "Counter": []
        }

        for counter in counters:
            counters_data["Counter"].append(
                {
                    "Name": counter
                }
            )

        try:
            return self.client.perfmonRemoveCounter(SessionHandle=token, ArrayOfCounter=counters_data)
        except Fault as e:
            return e
