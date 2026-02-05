from utils_audio import limpiar_texto


def test_limpiar_texto_quita_muletillas():
    texto = "Paciente, eh, tiene dolor, este, y mmm fatiga"
    limpio = limpiar_texto(texto)
    assert "eh" not in limpio
    assert "este" not in limpio
    assert "mmm" not in limpio
    assert "Paciente" in limpio
    assert "fatiga" in limpio


def test_limpiar_texto_normaliza_espacios():
    texto = "Paciente    con    varios   espacios"
    assert "  " not in limpiar_texto(texto)  # no dobles espacios
