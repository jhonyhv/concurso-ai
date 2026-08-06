# BB Master AI

MVP de uma plataforma pessoal para preparação para o concurso do Banco do Brasil.

## Recursos

- painel com horas, questões e percentual de acertos;
- plano semanal proporcional ao peso das matérias;
- banco inicial de questões com correção comentada;
- registro de sessões de estudo;
- conteúdo programático inicial;
- armazenamento local em SQLite.

## Instalação no Windows

1. Instale o Python 3.11 ou superior.
2. Extraia a pasta do projeto.
3. Abra o PowerShell dentro da pasta.
4. Execute:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá em `http://localhost:8501`.

## Próximas versões

- importação do edital em PDF;
- cadastro e importação de questões por CSV;
- flashcards com revisão espaçada;
- simulados completos e cronômetro;
- autenticação e sincronização online;
- professor com IA;
- exportação do desempenho.

## Aviso

O conteúdo programático incluído é apenas uma base inicial inspirada na seleção anterior. O edital oficial vigente deve sempre ser a fonte principal.
