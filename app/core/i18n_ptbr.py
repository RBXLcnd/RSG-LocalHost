"""Brazilian Portuguese, derived from the European Portuguese table (app/core/i18n_pt.py).

Most of the text is the same; what differs is vocabulary (ficheiro -> arquivo), the progressive
(a correr -> rodando) and the way the user is addressed (tu -> você). Those differences are listed
here as rules, so a new European Portuguese entry gets a Brazilian version automatically. A word
that is not in the lists below simply stays as the European text.
"""
from __future__ import annotations

import re

from app.core.i18n_pt import EXACT as PT_EXACT, PATTERNS as PT_PATTERNS

# Whole phrases first (case sensitive, applied in order).
PROGRESSIVE = {
    "correr": "rodando", "criar": "criando", "decorrer": "em andamento", "descarregar": "baixando", "colar": "colando",
    "esconder": "escondendo", "explicar": "explicando", "lançar": "lançando", "limitar": "limitando",
    "manter": "mantendo", "usar": "usando",
}

PHRASES = [
    (r"> Aspeto\b", "> Aparência"), (r"^Aspeto$", "Aparência"), (r"o\.teu\.tunnel", "seu.tunnel"),
    (r"\bpára\b", "para"), (r"Copiar diagnóstico copia\b", "Copiar diagnóstico copia"),
    (r"\ba app verifica\b", "a app verifica"),
    (r"\bA consola está vazia\b", "O console está vazio"), (r"\bna consola\b", "no console"),
    (r"\ba consola\b", "o console"), (r"\bjá não é válid([ao])", r"não é mais válid\1"),
    (r"\bInicia sessão\b", "Faça login"), (r"\binicia sessão\b", "faça login"),
    (r"\bÍnício de sessão\b", "Login"), (r"\bínício de sessão\b", "login"),
    (r"\bCarrega em\b", "Clique em"), (r"\bCarregar em\b", "Clicar em"),
    (r"\bA aguardar\b", "Aguardando"), (r"\bA carregar\b", "Carregando"), (r"\bA inicializar\b", "Inicializando"),
    (r"\bA iniciar\b", "Iniciando"), (r"\bA medir\b", "Medindo"), (r"\bA preparar\b", "Preparando"),
    (r"\bA reiniciar\b", "Reiniciando"), (r"\bA testar\b", "Testando"), (r"\bA verificar\b", "Verificando"),
    (r"(?<!para )(?<!volta )(?<!de )(?<!pronta )\ba (?:correr|criar|decorrer|descarregar|colar|esconder|explicar|lançar|limitar|manter|usar)\b", None),
    (r"\bpossível ligar ao\b", "possível conectar ao"), (r"^Ligar$", "Conectar"),
    (r"\bligar-se\b", "conectar-se"), (r"\bsó tu a vês\b", "só você a vê"),
]

# Single words (lower case; capitalisation is kept).
WORDS = {
    "secção": "seção", "largar": "soltar", "entra": "entre", "partilha": "compartilhe",
    "ficheiro": "arquivo", "ficheiros": "arquivos", "consola": "console", "definições": "configurações",
    "descarregar": "baixar", "descarregado": "baixado", "descarregá": "baixá", "telemóvel": "celular",
    "utilizador": "usuário", "aspeto": "visual", "grelha": "grade", "contacto": "contato",
    "detetar": "detectar", "detetado": "detectado", "guardar": "salvar", "guarda": "salva",
    "guardada": "salva", "guardado": "salvo", "guardares": "salvar", "registo": "registro",
    "partilhar": "compartilhar", "arranca": "inicia", "arrancar": "iniciar",
    "arranque": "início", "ligação": "conexão", "ligações": "conexões", "ligado": "conectado",
    "ligados": "conectados", "desligados": "desconectados", "sítio": "lugar", "pára": "pare",
    "teu": "seu", "tua": "sua", "teus": "seus", "tuas": "suas", "tu": "você", "vês": "vê",
    "queres": "quer", "podes": "pode", "estás": "está", "usas": "usa", "obteres": "obter",
    "pedires": "pedir", "colares": "colar", "levares": "levar", "terminares": "terminar",
    "quiseres": "quiser", "iniciaste": "iniciou", "abres": "abre",
    "abre": "abra", "cola": "cole", "corre": "execute", "escolhe": "escolha", "clica": "clique",
    "tenta": "tente", "verifica": "verifique", "indica": "informe", "apaga": "apague", "instala": "instale",
    "usa": "use", "larga": "solte", "lê": "leia", "aguarda": "aguarde", "preenche": "preencha",
    "copia": "copie", "salta": "pule", "arrasta": "arraste", "aponta": "aponte", "alterna": "alterne",
    "adiciona": "adicione", "reencaminha": "encaminha", "cria": "crie", "inicia": "inicie", "minimiza": "minimize",
    "usá": "usá", "desligá": "desligá",
}

_word = re.compile(r"[A-Za-zÀ-ÿ]+")


def _case(src: str, dst: str) -> str:
    return dst[:1].upper() + dst[1:] if src[:1].isupper() else dst


PROTECTED = ("a app verifica", "Copiar diagnóstico copia")


def convert(text: str) -> str:
    for i, phrase in enumerate(PROTECTED):
        text = text.replace(phrase, f"\x00{i}\x00")
    text = re.sub(PHRASES[0][0], PHRASES[0][1], text)
    for pattern, repl in PHRASES[1:]:
        if repl is None:
            text = re.sub(pattern, lambda m: PROGRESSIVE[m.group(0)[2:]], text)
        else:
            text = re.sub(pattern, repl, text)
    text = _word.sub(
        lambda m: _case(m.group(0), WORDS[m.group(0).lower()]) if m.group(0).lower() in WORDS else m.group(0), text
    )
    for i, phrase in enumerate(PROTECTED):
        text = text.replace(f"\x00{i}\x00", phrase)
    return text


EXACT = {key: convert(value) for key, value in PT_EXACT.items()}
PATTERNS = {key: convert(value) for key, value in PT_PATTERNS.items()}
