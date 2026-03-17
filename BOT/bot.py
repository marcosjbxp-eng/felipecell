from neonize.client import NewClient
from neonize.events import MessageEv
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
import requests
import os

client = NewClient(r"C:\bot_zap\bot.sqlite3")
webhook_url = 'http://localhost:8000/api/webhook/'

def enviar(mensagem_obj, acao, dados):
    chat_objeto = mensagem_obj.Info.MessageSource.Chat
    numero = chat_objeto.User
    
    payload = {
        'remetente': numero,
        'acao': acao, 
        'dados': dados
    }
    
    try:
        resposta = requests.post(webhook_url, json=payload)
        if resposta.status_code == 200:
            dadosjg = resposta.json()
            text = dadosjg.get("msg")
            if text:
                client.send_message(chat_objeto, Message(conversation=str(text)))
    except Exception:
        pass

@client.event(MessageEv)
def on_message(client, message: MessageEv):
    texto = message.Message.conversation or message.Message.extendedTextMessage.text
    if not texto:
        return
        
    comando = texto
    if comando:
        enviar(message, comando, None)

client.connect()