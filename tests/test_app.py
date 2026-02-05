import json
import app


def test_analizar_con_gemini_exito(monkeypatch):
    class FakeResp:
        def __init__(self, text):
            self.text = text

    class GoodModel:
        def generate_content(self, prompt, generation_config=None):
            return FakeResp('{"texto_corregido":"Texto ok","paciente":"Juan","edad":45,"motivo":"Dolor torácico","diagnostico":"Sospecha IAM","tratamiento":"Aspirina"}')

    def fake_factory(model_id):
        return GoodModel()

    monkeypatch.setattr(app.genai, "GenerativeModel", fake_factory)

    salida = app.analizar_con_gemini("texto cualquiera")
    datos = json.loads(salida)
    assert datos["paciente"] == "Juan"
    assert datos["edad"] == 45


def test_analizar_con_gemini_fallback_y_correcciones(monkeypatch):
    class FakeRespBad:
        def __init__(self, text):
            self.text = text

    class BadModel:
        def generate_content(self, prompt, generation_config=None):
            # devuelve JSON con comillas simples y una coma extra
            return FakeRespBad("{'texto_corregido':'X', 'paciente':'Ana', 'edad':30,}")

    class GoodModel:
        def generate_content(self, prompt, generation_config=None):
            return FakeRespBad('{"texto_corregido":"X","paciente":"Ana","edad":30}')

    def factory(model_id):
        if model_id.endswith("-flash"):
            return BadModel()
        return GoodModel()

    monkeypatch.setattr(app.genai, "GenerativeModel", factory)

    salida = app.analizar_con_gemini("texto que falla primero")
    datos = json.loads(salida)
    assert datos["paciente"] == "Ana"
    assert datos["edad"] == 30
