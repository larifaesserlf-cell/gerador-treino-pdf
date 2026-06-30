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

_VIDEOS_CADASTRADOS = {
    "Supino Reto c/ Barra":         "https://www.youtube.com/watch?v=MTS2g0Im_Js",
    "Supino Inclinado c/ Halteres": "https://www.youtube.com/watch?v=JOVGGEwfhIk",
    "Crucifixo c/ Halteres":        "https://www.youtube.com/watch?v=NI3tAZ9OAag",
    "Tríceps Pulley":               "https://www.youtube.com/watch?v=WUPk8Gq20cs",
    "Tríceps Testa c/ Barra":       "https://www.youtube.com/watch?v=f7IVPwvq5_o",
    "Agachamento Livre c/ Barra":   "https://www.youtube.com/watch?v=A7OelH9OBbk",
    "Leg Press 45 graus":           "https://www.youtube.com/watch?v=NcmQ-wVlQdc",
    "Stiff c/ Barra":               "https://www.youtube.com/watch?v=Jtb6ZCvyXbc",
    "Cadeira Extensora":            "https://www.youtube.com/watch?v=A1Cah1KDAlo",
    "Cadeira Flexora":              "https://www.youtube.com/watch?v=W5T_LubhXHU",
    "Panturrilha em Pé":            "https://www.youtube.com/watch?v=FURGALhnSks",
}

VIDEOS_EXERCICIOS = {nome: _VIDEOS_CADASTRADOS.get(nome, "") for nome in TODOS_EXERCICIOS}
