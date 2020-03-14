# noinspection PyUnresolvedReferences
import json
# noinspection PyUnresolvedReferences
from datetime import datetime

import urllib3
from requests import Session

# noinspection PyUnresolvedReferences
import demistomock as demisto
from CommonServerPython import *
# noinspection PyUnresolvedReferences
from CommonServerUserPython import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

def _response_error(message, response):
    """

    :param message:
    :param response:
    :return:
    """
    if response.status_code == 200:
        return
    raise Exception(
        f"""
Message:{message}.
Response code returned:{response.status_code}.
        """
    )


class Unifi:
    def __init__(
            self,
            username,
            password,
            base_url,
            site,
            insecure
    ):
        """
        Class Initializes session with UNIFI Controller
        :param username: controller username to authenticate session.
        :param password: controller password to authenticate session
        :param base_url: controller bse URL (ex: https://controll.unifi.com:8443)
        :param site: Controller site for alerts (ex: default)
        :param insecure: Ignore Insecure Request Warning
        """
        self._creds = {
            'username': username,
            'password': password
        }
        self.base_url = base_url
        self.site = site
        self.session = self._login(insecure)

    def _api_request(self, url, error_message):
        """
        Return JSON data from Controller Request
        :param url: URL for API Request
        :param error_message: Error message for error
        :return: Returns JSON data from request
        """
        headers = {'Content-Type': 'application/json'}
        response = self.session.get(url, headers=headers)
        _response_error(error_message, response)
        return response.json()['data']

    # Authenticate to UNIFI, return session after successful authentication
    def _login(self, session_verify):
        """
        Authenticate with UNIFI Controller
        :param session_verify: Verify SSL Certificate
        :return: Return established session
        """
        login_api = urljoin(self.base_url, '/api/login')

        # Auth data
        auth = json.dumps({**self._creds, **{'remember': False, 'strict': True}})

        # Create Session and Login to Controller
        session = Session()
        response = session.post(login_api, data=auth, verify=session_verify)
        _response_error(f"Failed to authenticate", response)

        return session

    # logout of UNIFI, return session after successful authentication
    def logout(self):
        """
        Logout of UNIFI Controller session
        """
        logout_api = urljoin(self.base_url, '/api/logout')

        response = self.session.post(logout_api)
        _response_error(f"Failed to logout", response)

    def get_clients(self, site_name):
        """
        Return all clients from Unifi Controller for specified site
        :param site_name: Name of the site to query
        :return: Return list of clients
        """
        clients_url = urljoin(self.base_url, f"/api/s/{site_name}/stat/sta")
        return self._api_request(clients_url, f"`get_clients` Failed\r\nurl: {clients_url}")

    def get_sites(self):
        """
        Return all Site from Unifi Controller
        :return: Return list of sites
        """
        site_url = urljoin(self.base_url, f"/api/self/sites")
        return self._api_request(site_url, f"`get_sites` Failed\r\nurl: {site_url}")

    def get_users(self, site_name):
        """
        Return list of users
        :param site_name: Name of the site to query
        :return: Return list of users
        """
        users_url = urljoin(self.base_url, f"/api/s/{site_name}/list/user")
        return self._api_request(users_url, f"`get_users` Failed\r\nurl: {users_url}")

    def get_user_details(self, site_name, user_id):
        """
        Return details for specified user
        :param site_name: Name of the site to query
        :param user_id: User ID returned in event data
        :return: Return user details in list
        """
        request_user = urljoin(self.base_url, f"/api/s/{site_name}/stat/user/{user_id}")
        return self._api_request(request_user, f"`get_user_details` Failed\r\nurl: {request_user}")


    def get_alarms(self):
        """
        Using established session, collect alarms from Console
        :return: Return list of alarms from controller
        """
        alarms_api = urljoin(self.base_url, f"/api/s/{self.site}/stat/alarm")
        return self._api_request(alarms_api, f"`geT_alarms` Failed\r\nurl: {alarms_api}")

    def get_new_alarms(self, earliest_timestamp, latest_timestamp):
        """
        Get Alarms between earliest and latest epoch time.
        :param earliest_timestamp: Earliest alert epoch time
        :param latest_timestamp: Latest alert epoch time
        :return: Return all events between earliest and latest
        """
        array_alarms = []

        for alarm in self.get_alarms():
            if alarm['key'] == 'EVT_IPS_IpsAlert' and 'timestamp' in alarm and (
                    int(earliest_timestamp) < int(alarm['timestamp']) < int(latest_timestamp)):
                array_alarms.append(alarm)
        return array_alarms


def unifi_get_users_list(unifi_session, site_name):
    """
    Get all users for specified UNIFI Controller site
    :param unifi_session: Unifi Session from Unifi class
    :param site_name: Name of the site to query
    """
    result = unifi_session.get_users(site_name)
    markdown = tableToMarkdown("Unifi User List", result)
    return_outputs(markdown, {"ContentsFormat": formats['json'], "Contents": json.dumps(result)})


def unifi_get_clients_list(unifi_session, site_name):
    """
    Get client list from UNIFI Controller for specified site name
    :param unifi_session: Unifi Session from Unifi class
    :param site_name: Name of the site to query
    """
    result = unifi_session.get_clients(site_name)
    markdown = tableToMarkdown("Unifi Client List", result)
    return_outputs(markdown, {"ContentsFormat": formats['json'], "Contents": json.dumps(result)})


def unifi_get_site_list(unifi_session):
    """
    Get all sites from UNIFI Controller
    :param unifi_session: Unifi Session from Unifi class
    """
    result = unifi_session.get_sites()
    markdown = tableToMarkdown("Unifi Site List", result)
    return_outputs(markdown, {"ContentsFormat": formats['json'], "Contents": json.dumps(result)})


def unifi_get_user_details(unifi_session, user_id, site_name):
    """
    Get user details for specified user id and site name
    :param unifi_session: Unifi Session from Unifi class
    :param user_id: User ID returned in event data
    :param site_name: Name of the site to query
    """
    user_details = unifi_session.get_user_details(site_name, user_id)
    markdown = tableToMarkdown("User Details", user_details)
    return_outputs(markdown, {"ContentsFormat": formats['json'], "Contents": json.dumps(user_details)})


def test_module(unifi_session):
    """
    Test Module for Demisto
    :param unifi_session: Unifi Session from Unifi class
    :return: Return 'OK' if success
    """
    result = False
    if unifi_session.base_url:
        result = "ok"
    return result


def fetch_incidents(unifi_session, first_fetch_time):
    """
    Fetch incident from Unifi Controller (Alerts)
    :param unifi_session: Unifi Session from Unifi class
    :param first_fetch_time:
    :return:
    """
    if 'last_fetch' in demisto.getLastRun():
        utc_dt = datetime.strptime(demisto.getLastRun()['last_fetch'], DATE_FORMAT)
        earliest_timestamp = int((utc_dt.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds())
    else:
        earliest_timestamp = int(first_fetch_time)

    latest_timestamp = int((datetime.now() - datetime(1970, 1, 1)).total_seconds())
    string_latest_timestamp = str(time.strftime(DATE_FORMAT, time.gmtime(latest_timestamp)))

    # Collect alerts between earliest and latest timestamps.
    alerts = unifi_session.get_new_alarms(earliest_timestamp, latest_timestamp)

    # Collect incidents to array.
    incidents = []
    for alert in alerts:
        incident = {
            'name': alert['catname'],
            'occured': alert['datetime'],
            'rawJSON': json.dumps(alert)
        }
        incidents.append(incident)

    return incidents, {'last_fetch': string_latest_timestamp}


def main():
    """
        PARSE AND VALIDATE INTEGRATION PARAMS
    """
    username = demisto.params()['credentials']['identifier']
    password = demisto.params()['credentials']['password']
    base_url = urljoin(demisto.params()['base_url'])
    site = demisto.params()['site']
    insecure = not demisto.params()['insecure']
    first_fetch_time = demisto.params()['first_fetch_time']
    user_id = ""
    site_name = ""

    if 'user_id' in demisto.args():
        user_id = demisto.args()['user_id']
    if 'site_name' in demisto.args():
        site_name = demisto.args()['site_name']

    LOG(f'Command being called is {demisto.command()}')
    try:
        unifi_session = Unifi(
            username=username,
            password=password,
            base_url=base_url,
            site=site,
            insecure=insecure,
        )
        if demisto.command() == 'test-module':
            # This is the call made when pressing the integration Test button.
            result = test_module(unifi_session)
            demisto.results(result)
        elif demisto.command() == 'fetch-incidents':
            # Set and define the fetch incidents command to run after activated via integration settings
            incidents, last_fetch = fetch_incidents(unifi_session, first_fetch_time)
            demisto.setLastRun(last_fetch)
            demisto.incidents(incidents)
        elif demisto.command() == 'unifi-get-clients-list':
            unifi_get_clients_list(unifi_session, site_name)
        elif demisto.command() == 'unifi-get-site-list':
            unifi_get_site_list(unifi_session)
        elif demisto.command() == 'unifi-get-user-details':
            unifi_get_user_details(unifi_session, user_id, site_name)
        elif demisto.command() == 'unifi-get-users-list':
            unifi_get_users_list(unifi_session, site_name)
        unifi_session.logout()
    # Log exceptions
    except Exception as e:
        return_error(f'Failed to execute {demisto.command()} command. Error: {str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
