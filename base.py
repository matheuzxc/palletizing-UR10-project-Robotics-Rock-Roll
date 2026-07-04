import socket
import time
import math
import struct

# Configurações de rede validadas
ROBOT_IP = '192.168.2.102'
PORT = 30003


def mover_robo_seguro(tipo_movimento, juntas_alvo):
    try:
        # 1. Criar a conexão
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(5)
        tcp_socket.connect((ROBOT_IP, PORT))

        # 2. Definir a posição (em radianos)
        # Exemplo: Posição "Base" (ajuste conforme sua necessidade)
        # Ordem das juntas: [Base, Ombro, Cotovelo, Pulso 1, Pulso 2, Pulso 3]

        # 3. CrIar o comando URScript
        # movej([q1,q2,q3,q4,q5,q6], a=1.2, v=0.2)
        # a = aceleração das juntas (rad/s^2), v = velocidade das juntas (rad/s)
        comando = f"if(is_within_safety_limits(p{juntas_alvo}):\n {tipo_movimento}(p{juntas_alvo}, a=0.5, v=0.1)\n"

        # 4. Enviar o comando
        print(f"Enviando movimento para {ROBOT_IP}...")
        tcp_socket.send(comando.encode('utf-8'))

        # Pequena pausa para o robô processar
        time.sleep(1)

        tcp_socket.close()
        print("Comando enviado com sucesso!")

    except Exception as e:
        print(f"Erro na comunicação: {e}")




if __name__ == "__main__":
tamanhox = 0.125
tamanhoy = 0.125
tamanho_pallet = 0.50

ponto_pegar_caixa = [0.438, -0.975, 0.65, 0.881, -2.986, 0.051]
ponto_caixa1 = [1.051, 0.191, -0.394, 2.55, -1.82, 0.061]
ponto_padrao = [0.438, -0.975, 0.65, 0.881, -2.986, 0.051]
ponto_caixa = [-64.95, -140.42, -82.51, 311.83, 87.61, 74.68]


tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.settimeout(5)
tcp_socket.connect((ROBOT_IP, PORT))

comando = "freedrive_mode()"
tcp_socket.send(comando.encode('utf-8'))
input("O robo esta no lugar certo?")

tcp_socket.close()

tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.settimeout(5)
tcp_socket.connect((ROBOT_IP, PORT))
packet = tcp_socket.recv(1060)

comando = "get_actual_tcp_pose()"
tcp_socket.send(comando.encode('utf-8'))
dados_raw = packet[252:300]
local_caixa = struct.unpack('!dddddd', dados_raw)
local_aproximacao_caixa = list(local_caixa)
local_aproximacao_caixa[2] += 0.15
print(local_caixa)
print(local_aproximacao_caixa)

# delta_diagonal = [0.15, 0.15, 0.15, 0.0, 0.0, 0.0]
# ponto_aproximacao_pallet = local_pallet + delta_diagonal

# # ordem das coisas ponto aproximacao caixa -> ponto caixa -> ponto aproximacao caixa
# # ponto aproximacao pallet -> local pallet ->
# for posicaoX in range(int(tamanho_pallet/tamanhox)):
# for posicaoY in range(int(tamanho_pallet/tamanhoy)):
# mover_robo_seguro("movej", ponto_pegar_caixa)
# mover_robo_seguro("movej", [1.051 -posicaoX*tamanhox, 0.191-posicaoY*tamanhoy, -0.394, 2.55, -1.82, 0.061])
# mover_robo_seguro("movel", [1.051-posicaoX*tamanhox, 0.191-posicaoY*tamanhoy, -0.394, 2.55, -1.82, 0.061])
# mover_robo_seguro("movel", [1.051-posicaoX*tamanhox, 0.191-posicaoY*tamanhoy, -0.394, 2.55, -1.82, 0.061])
# mover_robo_seguro("movej", ponto_pegar_caixa)
