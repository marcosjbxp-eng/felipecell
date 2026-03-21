import uuid
import json
import os
import hmac
import hashlib
from datetime import datetime, timedelta

from django.conf import settings as django_settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from .forms import UserProfileForm

# ── HELPERS ───────────────────────────────────────────────────────────────────

def conectar_google():
    """Conecta à planilha via conta de serviço Google.
    Prioriza variável de ambiente GOOGLE_CREDENTIALS_JSON para produção,
    com fallback para o arquivo api-google.json em desenvolvimento local.
    """
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        # Produção: credenciais via variável de ambiente
        import json as _json
        creds_dict = _json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Desenvolvimento local: arquivo JSON
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        keyfile = os.path.join(base_dir, 'api-google.json')
        creds = ServiceAccountCredentials.from_json_keyfile_name(keyfile, scope)
    
    cliente = gspread.authorize(creds)
    return cliente.open('Bot').sheet1


def salvar(data, nome, numero, dispositivo):
    sheet = conectar_google()
    sheet.append_row([data, nome, numero, dispositivo])


# ── VIEWS AUTENTICADAS ────────────────────────────────────────────────────────

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('settings')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'settings.html', {'form': form})


@login_required
def home(request):
    sheet = conectar_google()
    dados_brutos = sheet.get_all_values()
    dados_processados = []
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)

    lucro_dia = 0.0
    lucro_semana = 0.0
    lucro_mes = 0.0
    total_pendentes = 0
    total_garantia = 0
    linhas = dados_brutos[1:] if len(dados_brutos) > 0 and dados_brutos[0][0].lower() == 'id' else dados_brutos

    for row in linhas:
        while len(row) < 9:
            row.append("")
        id_servico = row[0]
        data_entrada_str = row[1]
        nome = row[2]
        numero = row[3]
        aparelho = row[4]
        defeito = row[5]
        valor_str = row[6].replace('R$', '').replace('.', '').replace(',', '.').strip()
        data_saida_str = row[7].strip()
        garantia_str = row[8].strip()
        prazo_garantia = int(garantia_str) if garantia_str.isdigit() else 90

        valor_float = 0.0
        status_texto = "Pendente"
        classe_status = "pending"
        dias_restantes = 0

        if valor_str:
            try:
                valor_float = float(valor_str)
            except ValueError:
                valor_float = 0.0

            if data_saida_str:
                try:
                    data_saida_obj = datetime.strptime(data_saida_str, '%d/%m/%Y').date()
                except ValueError:
                    data_saida_obj = None

                if data_saida_obj:
                    if prazo_garantia == 0:
                        status_texto = "Sem Garantia"
                        classe_status = "expired"
                        if data_saida_obj == hoje:
                            lucro_dia += valor_float
                        if data_saida_obj >= inicio_semana:
                            lucro_semana += valor_float
                        if data_saida_obj >= inicio_mes:
                            lucro_mes += valor_float
                    else:
                        dias_passados = (hoje - data_saida_obj).days
                        if dias_passados <= prazo_garantia:
                            dias_restantes = prazo_garantia - dias_passados
                            status_texto = f"Garantia ({dias_restantes} dias)"
                            classe_status = "warranty"
                            total_garantia += 1
                            if data_saida_obj == hoje:
                                lucro_dia += valor_float
                            if data_saida_obj >= inicio_semana:
                                lucro_semana += valor_float
                            if data_saida_obj >= inicio_mes:
                                lucro_mes += valor_float
                        else:
                            status_texto = "Garantia Expirada"
                            classe_status = "expired"
            else:
                status_texto = "Concluído (Sem Data)"
                classe_status = "expired"
        else:
            status_texto = "Pendente"
            classe_status = "pending"
            total_pendentes += 1

        dados_processados.append({
            'id': id_servico,
            'data_entrada': data_entrada_str,
            'data_saida': data_saida_str,
            'nome': nome,
            'numero': numero,
            'aparelho': aparelho,
            'defeito': defeito,
            'valor': row[6],
            'status': status_texto,
            'classe_status': classe_status,
            'prazo_garantia': prazo_garantia,
        })

    ordem_status = {'pending': 0, 'warranty': 1, 'expired': 2}

    def safe_parse_date(d):
        try:
            return datetime.strptime(d, '%d/%m/%Y') if d else datetime.min
        except ValueError:
            return datetime.min

    dados_processados.sort(
        key=lambda x: (ordem_status.get(x['classe_status'], 99), safe_parse_date(x['data_entrada']))
    )

    context = {
        'dados': json.dumps(dados_processados),
        'kpi': {
            'dia': f"{lucro_dia:,.2f}".replace('.', ','),
            'semana': f"{lucro_semana:,.2f}".replace('.', ','),
            'mes': f"{lucro_mes:,.2f}".replace('.', ','),
            'pendentes': total_pendentes,
            'garantias_ativas': total_garantia,
        }
    }
    return render(request, 'home.html', context)


@login_required
def atualizar_servico(request):
    """Recebe ID, Valor e Dias de Garantia.
    CORRIGIDO: removido @csrf_exempt — agora requer token CSRF válido.
    """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'msg': 'JSON inválido.'}, status=400)

        servico_id = dados.get('id')
        valor_raw = dados.get('valor')
        garantia_dias = dados.get('garantia', '90')

        if not servico_id or not valor_raw:
            return JsonResponse({'success': False, 'msg': 'Dados incompletos.'}, status=400)

        # Validação básica para evitar injeção de dados
        try:
            valor_float = float(
                str(valor_raw).replace('R$', '').replace('.', '').replace(',', '.').strip()
            )
            if valor_float < 0:
                raise ValueError
        except ValueError:
            return JsonResponse({'success': False, 'msg': 'Valor inválido.'}, status=400)

        try:
            garantia_int = int(garantia_dias)
            if garantia_int < 0:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'msg': 'Garantia inválida.'}, status=400)

        sheet = conectar_google()
        cell = sheet.find(servico_id)
        if not cell:
            return JsonResponse({'success': False, 'msg': 'Serviço não encontrado.'}, status=404)

        data_saida = datetime.now().strftime('%d/%m/%Y')
        sheet.update_cell(cell.row, 7, valor_raw)
        sheet.update_cell(cell.row, 8, data_saida)
        sheet.update_cell(cell.row, 9, garantia_dias)

        return JsonResponse({'success': True, 'msg': 'Serviço finalizado com sucesso!'})

    return JsonResponse({'success': False, 'msg': 'Método inválido.'}, status=405)


def login(request):
    return render(request, 'login.html')


def none(request):
    # CORRIGIDO: faltava `return` — o redirect nunca era executado
    return redirect('/home/')


# ── ENDPOINT DO BOT (WEBHOOK) ─────────────────────────────────────────────────

def _verificar_token_webhook(request):
    """Verifica o token secreto do webhook via header Authorization.
    O bot deve enviar: Authorization: Bearer <WEBHOOK_SECRET_TOKEN>
    """
    token_esperado = django_settings.WEBHOOK_SECRET_TOKEN
    if not token_esperado:
        # Se o token não estiver configurado, bloqueia tudo por segurança
        return False
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    token_recebido = auth_header[7:]
    # Comparação segura contra timing attacks
    return hmac.compare_digest(token_recebido, token_esperado)



def receber(request):
    """Webhook chamado pelo BOT.
    CORRIGIDO:
      - Removido @csrf_exempt. Como é chamada server-to-server, a autenticação
        é feita via Bearer Token no header, dispensando CSRF de forma segura.
      - Adicionada validação do token secreto.
      - Adicionada verificação de método HTTP.
      - Adicionado tratamento de erro no JSON parsing.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'erro', 'msg': 'Método inválido.'}, status=405)

    if not _verificar_token_webhook(request):
        return JsonResponse({'status': 'erro', 'msg': 'Não autorizado.'}, status=401)

    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'erro', 'msg': 'JSON inválido.'}, status=400)

    comando = dados.get('acao', '')
    number = dados.get('remetente', '')
    msg = ""
    limpo = comando.lower().strip()

    if limpo.startswith('.'):
        try:
            if '.add' in limpo:
                aux = limpo.replace('.add', '').strip().strip(',')
                ls = aux.split(',')
                name = ls[0].strip()
                numero = ls[1].strip()
                aparelho = ls[2].strip()
                data_atual = datetime.now().strftime('%d/%m/%Y')
                salvar(data_atual, name, numero, aparelho)
                msg = "salvo com sucesso!"
        except IndexError:
            msg = "adiciona as informações do cliente"

    return JsonResponse({'status': 'blz', 'msg': msg})


# ── ENDPOINT DE ADIÇÃO VIA FORMULÁRIO ─────────────────────────────────────────

@login_required
def add_planilha(request):
    """CORRIGIDO: adicionado @login_required. Antes qualquer pessoa podia
    acessar /d7s87d/ sem autenticação e inserir dados na planilha.
    """
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        numero = request.POST.get('numero', '').strip()
        aparelho = request.POST.get('aparelho', '').strip()
        sistema = request.POST.get('sistema', '').strip()
        defeito = request.POST.get('defeito', '').strip()

        if not nome:
            messages.error(request, 'O campo Nome é obrigatório.')
            return redirect('add-planilha')

        if numero:
            digitos = ''.join(filter(str.isdigit, numero))
            if len(digitos) < 10:
                numero = digitos
            else:
                numero = (
                    f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
                    if len(digitos) == 11 else numero
                )

        dispositivo_final = f"{aparelho} ({sistema})" if sistema else aparelho
        data_atual = datetime.now().strftime('%d/%m/%Y')
        id_unico = str(uuid.uuid4())

        sheet = conectar_google()
        sheet.append_row([id_unico, data_atual, nome, numero, dispositivo_final, defeito, ""])
        messages.success(request, 'Ordem de Serviço aberta com sucesso!')
        return redirect('add-planilha')

    return render(request, 'adicionar.html')


@login_required
def addcliet(request):
    return render(request, 'adicionar.html')


def cobrar(request):
    pass


def conslta(request):
    pass


def note(request):
    pass