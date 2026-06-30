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

# Vídeos de execução cadastrados — use o painel da professora (aba Vídeos)
# para adicionar/remover em tempo de execução; estes são os padrões de fábrica.
_VIDEOS_CADASTRADOS = {
    # ── Peito ──────────────────────────────────────────────────────────────
    "Supino Reto c/ Barra":         "https://www.youtube.com/shorts/AjTLUlx4nEs",
    "Supino Inclinado c/ Halteres": "https://www.youtube.com/shorts/eBT3llJhxU8",
    "Crucifixo c/ Halteres":        "https://www.youtube.com/shorts/s7gBuCccHNc",
    "Crossover no Cabo":            "https://www.youtube.com/shorts/VKLvdizQy9U",

    # ── Tríceps ────────────────────────────────────────────────────────────
    "Tríceps Pulley":               "https://www.youtube.com/shorts/6QhCR_pJvMM",
    "Tríceps Testa c/ Barra":       "https://www.youtube.com/shorts/vgJbQvdpJ8M",

    # ── Costas ────────────────────────────────────────────────────────────
    "Puxada Frontal c/ Barra":      "https://www.youtube.com/shorts/jSXyEBHbEbo",
    "Remada Curvada c/ Barra":      "https://www.youtube.com/shorts/r2BIpnqmoJA",
    "Remada Unilateral c/ Haltere": "https://www.youtube.com/shorts/A6Rjc6aUUB8",
    "Remada Alta c/ Barra":         "https://www.youtube.com/shorts/csF_uw7niTI",

    # ── Bíceps ────────────────────────────────────────────────────────────
    "Rosca Direta c/ Barra":        "https://www.youtube.com/shorts/zWIpVEn6Qdk",
    "Rosca Martelo c/ Halteres":    "https://www.youtube.com/shorts/L1JXNs-MgXg",

    # ── Pernas ────────────────────────────────────────────────────────────
    "Agachamento Livre c/ Barra":   "https://www.youtube.com/watch?v=ultWZbUMPL8",
    "Leg Press 45 graus":           "https://www.youtube.com/shorts/N2hvV6tvZ2w",
    "Stiff c/ Barra":               "https://www.youtube.com/shorts/clHs-3qx-O8",
    "Cadeira Extensora":            "https://www.youtube.com/shorts/eFYUSjPp0bc",
    "Cadeira Flexora":              "https://www.youtube.com/shorts/uExxDIJzFuE",
    "Panturrilha em Pé":            "https://www.youtube.com/shorts/S9kJU_vhzfo",

    # ── Glúteos / Feminino ────────────────────────────────────────────────
    "Elevação de Quadril c/ Barra": "https://www.youtube.com/shorts/h1lGpMfbwqQ",
    "Abdutor de Quadril (máquina)": "https://www.youtube.com/shorts/2INAfv6A0BY",
    "Afundo c/ Halteres":           "https://www.youtube.com/shorts/SgUl1OfUZ7U",

    # ── Ombros ────────────────────────────────────────────────────────────
    "Desenvolvimento c/ Barra":     "https://www.youtube.com/shorts/6fEzNQFsrNE",
    "Desenvolvimento c/ Halteres":  "https://www.youtube.com/shorts/fUqCp4WNKeM",
    "Desenvolvimento Militar c/ Barra": "https://www.youtube.com/shorts/tZH8QkgWkL0",
    "Elevação Lateral c/ Halteres": "https://www.youtube.com/shorts/XgfVRu3O-qY",

    # ── Core / Abdominal ──────────────────────────────────────────────────
    "Abdominais no Cabo":           "https://www.youtube.com/shorts/AO4pOT89bDE",
    "Prancha Frontal":              "https://www.youtube.com/shorts/fItKt4rP50w",
}

VIDEOS_EXERCICIOS = {nome: _VIDEOS_CADASTRADOS.get(nome, "") for nome in TODOS_EXERCICIOS}
