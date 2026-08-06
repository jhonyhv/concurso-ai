import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bb_master.db"

SUBJECTS = [
    ("Língua Portuguesa", 15),
    ("Língua Inglesa", 5),
    ("Matemática", 5),
    ("Atualidades do Mercado Financeiro", 5),
    ("Matemática Financeira", 5),
    ("Conhecimentos Bancários", 10),
    ("Conhecimentos de Informática", 15),
    ("Vendas e Negociação", 15),
]

QUESTIONS = [
    ("Conhecimentos Bancários", "Qual instituição define a taxa Selic?", "Banco Central do Brasil", "CVM", "Banco do Brasil", "BNDES", "A", "A taxa Selic é definida pelo Copom, órgão do Banco Central."),
    ("Matemática Financeira", "Em juros simples, qual é a fórmula dos juros?", "J = C × i × t", "J = C × (1+i)^t", "M = C ÷ i", "J = C + i + t", "A", "Em juros simples, os juros são calculados sobre o capital inicial."),
    ("Conhecimentos de Informática", "Qual prática aumenta a segurança de uma conta?", "Reutilizar a mesma senha", "Ativar autenticação em dois fatores", "Compartilhar a senha", "Desativar atualizações", "B", "A autenticação em dois fatores adiciona uma segunda camada de proteção."),
    ("Vendas e Negociação", "Na venda consultiva, a primeira etapa essencial é:", "Oferecer o produto mais caro", "Compreender as necessidades do cliente", "Encerrar rapidamente", "Evitar perguntas", "B", "A venda consultiva começa pelo diagnóstico das necessidades."),
    ("Língua Portuguesa", "Assinale a alternativa com concordância adequada:", "Fazem dois anos que estudo", "Houveram muitos candidatos", "Faz dois anos que estudo", "Existe muitas vagas", "C", "O verbo fazer indicando tempo decorrido é impessoal e fica no singular."),
    ("Atualidades do Mercado Financeiro", "O Pix é um sistema de pagamentos instantâneos criado por:", "Banco Central do Brasil", "Banco do Brasil", "Tesouro Nacional", "CVM", "A", "O Pix foi criado e é gerido pelo Banco Central do Brasil."),
]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                weight INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                statement TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                answer TEXT NOT NULL,
                explanation TEXT
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                selected TEXT NOT NULL,
                correct INTEGER NOT NULL,
                attempted_at TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO subjects(name, weight) VALUES (?, ?)", SUBJECTS
        )
        if connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO questions(subject, statement, option_a, option_b, option_c,
                                      option_d, answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                QUESTIONS,
            )
        connection.commit()


def load_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with connect() as connection:
        return pd.read_sql_query(query, connection, params=params)
