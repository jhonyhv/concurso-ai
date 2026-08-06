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
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Conhecimentos Bancários",
        "Política monetária",
        "Taxa Selic",
        "Média",
        "Qual instituição define a taxa Selic?",
        "Banco Central do Brasil",
        "CVM",
        "Banco do Brasil",
        "BNDES",
        None,
        "A",
        "A taxa Selic é definida pelo Copom, órgão do Banco Central.",
        "selic,copom,política monetária",
    ),
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Matemática Financeira",
        "Juros simples",
        "Fórmula dos juros",
        "Fácil",
        "Em juros simples, qual é a fórmula dos juros?",
        "J = C × i × t",
        "J = C × (1+i)^t",
        "M = C ÷ i",
        "J = C + i + t",
        None,
        "A",
        "Em juros simples, os juros são calculados sobre o capital inicial.",
        "juros simples,fórmula",
    ),
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Conhecimentos de Informática",
        "Segurança da informação",
        "Autenticação",
        "Fácil",
        "Qual prática aumenta a segurança de uma conta?",
        "Reutilizar a mesma senha",
        "Ativar autenticação em dois fatores",
        "Compartilhar a senha",
        "Desativar atualizações",
        None,
        "B",
        "A autenticação em dois fatores adiciona uma segunda camada de proteção.",
        "segurança,2fa,autenticação",
    ),
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Vendas e Negociação",
        "Venda consultiva",
        "Diagnóstico do cliente",
        "Média",
        "Na venda consultiva, a primeira etapa essencial é:",
        "Oferecer o produto mais caro",
        "Compreender as necessidades do cliente",
        "Encerrar rapidamente",
        "Evitar perguntas",
        None,
        "B",
        "A venda consultiva começa pelo diagnóstico das necessidades.",
        "vendas,negociação,cliente",
    ),
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Língua Portuguesa",
        "Concordância verbal",
        "Verbos impessoais",
        "Média",
        "Assinale a alternativa com concordância adequada:",
        "Fazem dois anos que estudo",
        "Houveram muitos candidatos",
        "Faz dois anos que estudo",
        "Existe muitas vagas",
        None,
        "C",
        "O verbo fazer indicando tempo decorrido é impessoal e fica no singular.",
        "português,concordância,verbo fazer",
    ),
    (
        "Banco do Brasil",
        "Cesgranrio",
        "Atualidades do Mercado Financeiro",
        "Meios de pagamento",
        "Pix",
        "Fácil",
        "O Pix é um sistema de pagamentos instantâneos criado por:",
        "Banco Central do Brasil",
        "Banco do Brasil",
        "Tesouro Nacional",
        "CVM",
        None,
        "A",
        "O Pix foi criado e é gerido pelo Banco Central do Brasil.",
        "pix,banco central,pagamentos",
    ),
]

QUESTION_MIGRATIONS = {
    "concurso": "TEXT",
    "banca": "TEXT",
    "assunto": "TEXT",
    "subassunto": "TEXT",
    "dificuldade": "TEXT",
    "option_e": "TEXT",
    "tags": "TEXT",
    "favorite": "INTEGER NOT NULL DEFAULT 0",
    "created_at": "TEXT",
}

ATTEMPT_MIGRATIONS = {
    "elapsed_seconds": "INTEGER NOT NULL DEFAULT 0",
}


def connect() -> sqlite3.Connection:
    """Abre uma conexão SQLite configurada para o aplicativo."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _apply_migrations(
    connection: sqlite3.Connection,
    table: str,
    migrations: dict[str, str],
) -> None:
    columns = _table_columns(connection, table)
    for column, definition in migrations.items():
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Cria e migra o banco sem apagar os dados existentes."""
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
                attempted_at TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );

            CREATE TABLE IF NOT EXISTS error_notebook (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER UNIQUE NOT NULL,
                error_count INTEGER NOT NULL DEFAULT 1,
                last_error_at TEXT NOT NULL,
                reviewed INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
            """
        )

        _apply_migrations(connection, "questions", QUESTION_MIGRATIONS)
        _apply_migrations(connection, "attempts", ATTEMPT_MIGRATIONS)

        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
            CREATE INDEX IF NOT EXISTS idx_questions_banca ON questions(banca);
            CREATE INDEX IF NOT EXISTS idx_questions_assunto ON questions(assunto);
            CREATE INDEX IF NOT EXISTS idx_questions_dificuldade ON questions(dificuldade);
            CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id);
            CREATE INDEX IF NOT EXISTS idx_attempts_date ON attempts(attempted_at);
            """
        )

        connection.executemany(
            "INSERT OR IGNORE INTO subjects(name, weight) VALUES (?, ?)",
            SUBJECTS,
        )

        if connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO questions(
                    concurso, banca, subject, assunto, subassunto, dificuldade,
                    statement, option_a, option_b, option_c, option_d, option_e,
                    answer, explanation, tags, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                QUESTIONS,
            )

        seed_metadata = [
            ("Política monetária", "Taxa Selic", "Média", "Qual instituição define a taxa Selic?"),
            ("Juros simples", "Fórmula dos juros", "Fácil", "Em juros simples, qual é a fórmula dos juros?"),
            ("Segurança da informação", "Autenticação", "Fácil", "Qual prática aumenta a segurança de uma conta?"),
            ("Venda consultiva", "Diagnóstico do cliente", "Média", "Na venda consultiva, a primeira etapa essencial é:"),
            ("Concordância verbal", "Verbos impessoais", "Média", "Assinale a alternativa com concordância adequada:"),
            ("Meios de pagamento", "Pix", "Fácil", "O Pix é um sistema de pagamentos instantâneos criado por:"),
        ]
        connection.executemany(
            """
            UPDATE questions
               SET assunto = COALESCE(NULLIF(assunto, ''), ?),
                   subassunto = COALESCE(NULLIF(subassunto, ''), ?),
                   dificuldade = COALESCE(NULLIF(dificuldade, ''), ?)
             WHERE statement = ?
            """,
            seed_metadata,
        )

        connection.execute(
            """
            UPDATE questions
               SET concurso = COALESCE(NULLIF(concurso, ''), 'Banco do Brasil'),
                   banca = COALESCE(NULLIF(banca, ''), 'Cesgranrio'),
                   assunto = COALESCE(NULLIF(assunto, ''), 'Geral'),
                   dificuldade = COALESCE(NULLIF(dificuldade, ''), 'Média'),
                   created_at = COALESCE(created_at, datetime('now'))
            """
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO error_notebook(
                question_id, error_count, last_error_at, reviewed
            )
            SELECT question_id, COUNT(*), MAX(attempted_at), 0
              FROM attempts
             WHERE correct = 0
             GROUP BY question_id
            """
        )
        connection.commit()


def execute(query: str, params: tuple = ()) -> int:
    """Executa uma alteração e devolve o id inserido."""
    with connect() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
        return int(cursor.lastrowid or 0)


def load_df(query: str, params: tuple = ()) -> pd.DataFrame:
    """Executa uma consulta e devolve um DataFrame."""
    with connect() as connection:
        return pd.read_sql_query(query, connection, params=params)
