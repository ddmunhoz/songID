import requests
import base64
import urllib
import io

class signalBot:
    """Simple class to send messages using Telegram Bot API """

    def __init__(self, sigSender, sigGroup, sigEndpoint):
        self.sigSender = sigSender
        self.sigGroup = sigGroup
        self.sigEndpoint = sigEndpoint
    
    def getIpInformation(self, ip):
        ipPayloadResponse = f'http://ip-api.com/json/{ip}'
        response = requests.get(ipPayloadResponse)
        return response.json()
    
    def sendMessage(self, bot_message, silently = False, type = 'text', binPayload = None):
        try:
            if type == 'text':
                send_text = {
                                "message": f"{bot_message}",
                                "number": f"{self.sigSender}",
                                "recipients": [
                                    f"{self.sigGroup}"
                                ]
                }
                response = requests.post(f'{self.sigEndpoint}/v2/send',json=send_text)
                return response.json()
        
            if type == 'image':
                send_text = {
                                "message": f"{bot_message}",
                                "base64_attachments": [binPayload],
                                "number": f"{self.sigSender}",
                                "recipients": [
                                                f"{self.sigGroup}"
                                ]
                }

            response = requests.post(f'{self.sigEndpoint}/v2/send',json=send_text)
            return response.json()
            return
        except requests.ConnectionError:
            print('Signal message send failed')
            
       