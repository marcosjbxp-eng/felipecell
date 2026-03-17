from django.shortcuts import render, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserProfileForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import datetime
import json

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
@login_required
def home(request):
    # Conexão direta sem fallback
    sheet = conectar_google()
    
    # Estrutura esperada agora:
    # [0:ID, 1:DataEntrada, 2:Nome, 3:Numero, 4:Aparelho, 5:Defeito, 6:Valor, 7:DataSaida]
    dados_brutos = sheet.get_all_values()

    dados_processados = []
    
    # Variáveis para Relatório Financeiro e KPIs
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)

    lucro_dia = 0.0
    lucro_semana = 0.0
    lucro_mes = 0.0
    total_pendentes = 0
    total_garantia = 0

    # Remove cabeçalho se existir
    linhas = dados_brutos[1:] if len(dados_brutos) > 0 and dados_brutos[0][0].lower() == 'id' else dados_brutos

    for row in linhas:
        # Garante que a linha tenha colunas suficientes (até índice 7/H)
        while len(row) < 8:
            row.append("")

        id_servico = row[0]
        data_entrada_str = row[1]
        nome = row[2]
        numero = row[3]
        aparelho = row[4]
        defeito = row[5]
        valor_str = row[6].replace('R$', '').replace('.', '').replace(',', '.').strip()
        data_saida_str = row[7] # Nova coluna de data de saída

        # Lógica de Status e Garantia
        valor_float = 0.0
        status_texto = "Pendente"
        classe_status = "pending" # pending, warranty, expired
        dias_restantes = 0
        
        if valor_str:
            valor_float = float(valor_str)
            
            # Se tem valor, verificamos a garantia
            if data_saida_str:
                data_saida_obj = datetime.strptime(data_saida_str, '%d/%m/%Y').date()
                dias_passados = (hoje - data_saida_obj).days
                prazo_garantia = 90 # Configuração de 90 dias
                
                if dias_passados <= prazo_garantia:
                    dias_restantes = prazo_garantia - dias_passados
                    status_texto = f"Garantia ({dias_restantes} dias)"
                    classe_status = "warranty"
                    total_garantia += 1
                    
                    # Contabiliza lucro (baseado na data de saída)
                    if data_saida_obj == hoje:
                        lucro_dia += valor_float
                    if data_saida_obj >= inicio_semana:
                        lucro_semana += valor_float
                    if data_saida_obj >= inicio_mes:
                        lucro_mes += valor_float
                else:
                    status_texto = "Garantia Expirada"
                    classe_status = "expired"
                    # Não soma nos KPIs de lucro corrente pois já expirou (passado)
            else:
                # Caso legado: tem valor mas não tem data de saída salva
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
            'classe_status': classe_status
        })

    # Ordenação: Pendentes -> Em Garantia -> Expirados
    ordem_status = {'pending': 0, 'warranty': 1, 'expired': 2}
    dados_processados.sort(key=lambda x: (ordem_status[x['classe_status']], datetime.strptime(x['data_entrada'], '%d/%m/%Y') if x['data_entrada'] else datetime.min), reverse=False)

    context = {
        'dados': json.dumps(dados_processados),
        'kpi': {
            'dia': f"{lucro_dia:,.2f}".replace('.', ','),
            'semana': f"{lucro_semana:,.2f}".replace('.', ','),
            'mes': f"{lucro_mes:,.2f}".replace('.', ','),
            'pendentes': total_pendentes,
            'garantias_ativas': total_garantia
        }
    }
    return render(request, 'home.html', context)

@csrf_exempt
@login_required
def atualizar_servico(request):
    """ Recebe ID e Valor. Salva Valor e Data de Saída (Hoje). """
    if request.method == 'POST':
        dados = json.loads(request.body)
        servico_id = dados.get('id')
        valor_raw = dados.get('valor')

        if not servico_id or not valor_raw:
            return JsonResponse({'success': False, 'msg': 'Dados incompletos.'})

        sheet = conectar_google()
        cell = sheet.find(servico_id)
        
        data_saida = datetime.now().strftime('%d/%m/%Y')

        # Atualiza Coluna 7 (Valor) e Coluna 8 (Data Saída)
        # gspread usa índice base 1
        # G=7, H=8
        sheet.update_cell(cell.row, 7, valor_raw)
        sheet.update_cell(cell.row, 8, data_saida)

        return JsonResponse({'success': True, 'msg': 'Serviço finalizado e garantia iniciada!'})
            
    return JsonResponse({'success': False, 'msg': 'Método inválido'})

def login(request):
    return render(request, 'login.html')


def none(request):
    redirect('/home')


def conectar_google():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('api-google.json', scope)
    cliente = gspread.authorize(creds)
    return cliente.open('Bot').sheet1

def salvar(data, nome, numero, dispositivo):
    sheet = conectar_google()
    sheet.append_row([data, nome, numero, dispositivo])

@csrf_exempt
def receber(request):
    dados = json.loads(request.body)
    comando = dados.get('acao')
    number = dados.get('remetente')
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

def cobrar(request):
    pass

def add_planilha(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        numero = request.POST.get('numero', '').strip()
        aparelho = request.POST.get('aparelho', '').strip()
        sistema = request.POST.get('sistema', '').strip()
        defeito = request.POST.get('defeito', '').strip()
        if not nome:
            messages.error(request, 'O campo Nome é obrigatório.')
            return redirect('/add')
        if numero:
            digitos = ''.join(filter(str.isdigit, numero))
            if len(digitos) < 10:
                 numero = digitos
            else:
                 numero = f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}" if len(digitos) == 11 else numero
        dispositivo_final = aparelho
        if sistema:
            dispositivo_final = f"{aparelho} ({sistema})"
        data_atual = datetime.now().strftime('%d/%m/%Y')
        id_unico = str(uuid.uuid4())
        sheet = conectar_google()
        sheet.append_row([id_unico, data_atual, nome, numero, dispositivo_final, defeito, ""])
        messages.success(request, 'Ordem de Serviço aberta com sucesso!')
        return redirect('/add')

@login_required
def addcliet(request):
    return render(request, 'adicionar.html')

def conslta(request):
    pass

def note(request):
    pass