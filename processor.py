from bearychat import RTMClient
import re
import requests

class Process:
    def __init__(self, hubot_token):
        self.client = RTMClient(hubot_token, 'https://api.bearychat.com/v1')
        self.token_client = None
        self.token_client_header = None
        self.message_re = re.compile(r'(use (?P<token>\S+) )?send (?P<message>random|.+\!) to (?P<toSource>vchannel|user) (?P<toDetail>=\S+)( with attachment (?P<attachment>random|\S+))? count (?P<count>\d+)')
        self.help_text = "Usage: [use (<token>) ]send (random|<message>!) to (vchannel|user) (=bwxxx)[with attachment] (random|<message>!) count (\d)"
        self.example = "use fsdkaljfs send hello world! to vchannel =bw123 with attachment random count 100"

    def _get(self, *args, **argv):
        return self.client.get(*args, **argv).resp.json()

    def _post(self, *args, **argv):
        return self.client.post(*args, **argv).resp.json()

    def read_message(self, msg):
        '''
        return {
          method: (help|senduser|sendvchannel),
          detail: {
            token: null or string,
            message: string,
            toDetail: =xxxxx,
            attachment: string or null,
            count: int
          }
        }
        '''
        m = self.message_re.match(msg)
        if m is None:
            return {
                'method': 'help',
                'detail': None
            }
        return {
            'method': 'send' + m.group('toSource'),
            'detail': {
                'token': m.group('token'),
                'message': m.group('message'),
                'toDetail': m.group('toDetail'),
                'attachment': m.group('attachment'),
                'count': m.group('count')
            }
        }
    def build_token_client(self, token):
        self.token_client = requests.session()
        self.token_client_header = {
            'authorization': 'bearer ' + token,
            'Content-type': 'application/json'
        }
    
    def send_to_vchannel(self, detail):
        if detail['attachment'] is not None:
            detail['attachment'] = [{
                'color': 'gold',
                'text': detail['attachment']
            }]
        else:
            detail['attachment'] = []
        if detail['token'] is None:
            for i in range(int(detail['count'])):
                res = self._post('message.create', json={
                    'vchannel_id': detail['toDetail'],
                    'text': detail['message'],
                    'attachments': detail['attachment']
                })
        else:
            for i in range(int(detail['count'])):
                self.token_client.post('https://beary.bearychat.com/api/vchannels/' + detail['toDetail'] + '/messages', headers=self.token_client_header, data='{"text": "' + detail['message'] + '"}')

    def send_message(self, detail, sender, message):
        try:
            if detail['method'] is 'help':
                sender.send(message.refer(self.help_text))
                sender.send(message.refer('example: {}'.format(self.example)))
                return
            if detail['detail']['token'] is not None:
                self.build_token_client(detail['detail']['token'])
            if detail['method'] == 'senduser':
                sendJson = {
                    'user_id': detail['detail']['toDetail']
                }
                if detail['detail']['token'] is None:
                    detail['detail']['toDetail'] = self._post('p2p.create', json=sendJson)['vchannel_id']
                else:
                    res = self.token_client.get('https://beary.bearychat.com/api/members?all=true', headers = self.token_client_header).json()
                    for i in res['result']:
                        if i['id'] == detail['detail']['toDetail']:
                            detail['detail']['toDetail'] = i['vchannel_id']
                            break
            self.send_to_vchannel(detail['detail'])
        except:
            sender.send(message.refer('something error'))
