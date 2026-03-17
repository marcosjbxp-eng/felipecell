import os
import sys
import time
import subprocess

arquivo_alvo = "bot.py"

def iniciar_processo():
    return subprocess.Popen([sys.executable, arquivo_alvo])

def main():
    print(f"Monitorando {arquivo_alvo}...")
    processo = iniciar_processo()
    ultima_modificacao = os.stat(arquivo_alvo).st_mtime

    try:
        while True:
            time.sleep(1)
            nova_modificacao = os.stat(arquivo_alvo).st_mtime

            if nova_modificacao != ultima_modificacao:
                print("Alteracao detectada. Reiniciando...")
                processo.terminate()
                processo.wait()
                ultima_modificacao = nova_modificacao
                processo = iniciar_processo()

    except KeyboardInterrupt:
        processo.terminate()

if __name__ == "__main__":
    main()