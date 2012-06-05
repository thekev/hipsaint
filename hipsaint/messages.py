import logging
from jinja2.loaders import FileSystemLoader
from os import path
import requests
from hipsaint.options import COLORS
import socket
from jinja2 import Environment, PackageLoader

class HipchatMessage(object):
    url = "https://api.hipchat.com/v1/rooms/message"
    default_color = 'red'

    def __init__(self, type, inputs, token, user, room_id, notify, **kwargs):
        self.type = type
        self.inputs = inputs
        self.token = token
        self.user = user
        self.room_id = room_id
        self.notify = notify
        self.deliver_payload()

    def deliver_payload(self):
        ''' Makes HTTP GET request to HipChat containing the message from nagios
            according to API Documentation https://www.hipchat.com/docs/api/method/rooms/message
        '''
        message_body = self.render_message()
        message = {'room_id': self.room_id,
                   'from': self.user,
                   'message': message_body,
                   'color':  self.message_color,
                   'notify': int(self.notify),
                   'auth_token': self.token
        }
        raw_response = requests.get(self.url, params=message)
        response_data = raw_response.json
        if 'error' in response_data:
            error_message = response_data['error'].get('message')
            error_type = response_data['error'].get('type')
            error_code = response_data['error'].get('code')
            logging.error('%s - %s: %s' % (error_code, error_type, error_message))
        elif not 'status' in response_data:
            logging.error('Unexpected response')

    def render_message(self):
        ''' Unpacks Nagios inputs and renders the appropriate template depending
            on the notification type.
        '''
        template_type = self.type
        if template_type == 'host':
            hostname, timestamp, ntype, hostaddress, hoststate, hostoutput = self.inputs.split('|')
        elif template_type == 'service':
            servicedesc, hostalias, timestamp, ntype, hostaddress, servicestate, serviceoutput = self.inputs.split('|')
        else:
            raise Exception, 'Invalid notification type'

        self.message_color = COLORS.get(ntype) or self.default_color
        nagios_host    = socket.gethostname().split('.')[0]

        template_path = path.realpath(path.join(path.dirname(__file__), 'templates'))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template('%s.html' % template_type)
        context = locals()
        context.pop('self')
        return template.render(**context)