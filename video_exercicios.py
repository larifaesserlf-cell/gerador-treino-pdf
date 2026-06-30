from exercicios import EXERCICIOS as _EXERCICIOS


def _coletar_nomes():
    nomes = set()
    for genero in _EXERCICIOS.values():
        for divisao in genero.values():
            for treino in divisao.values():
                for ex in treino:
                    if isinstance(ex, dict):
                        nomes.add(ex["nome"])
    return sorted(nomes)


TODOS_EXERCICIOS = _coletar_nomes()

# Dicionário base: nome_do_exercicio → link_ou_caminho_video
# Preencha aqui ou use o painel da professora (aba Vídeos) para gerenciar
VIDEOS_EXERCICIOS = {nome: "" for nome in TODOS_EXERCICIOS}
