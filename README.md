# KodiBot - Renomeador de Midia (TMDB)

Aplicativo desktop em Python para renomear arquivos de midia (filmes e series) usando dados da API do TheMovieDB (TMDB), com padrao compativel com Kodi.

## Funcionalidades

- 🔍 **Busca TMDB (Filmes e Series)**: selecione o tipo no app e busque direto na API
- 🧠 **Limpeza Inteligente de Nomes**: remove tags de release/qualidade e numeros antes da busca
- 📝 **Renomeacao Automatica**: aplica padrao Kodi no nome sugerido
- 🎬 **Suporte a Multiplos Formatos**: mkv, mp4, avi, mov, flv, wmv, m4v
- 💻 **Interface Grafica PyQt6**: lista de arquivos, ano detectado e selecao de resultado
- ⚡ **Busca em Thread**: UI responsiva durante as buscas
- 🔁 **Atualizar Lista**: recarrega arquivos da pasta com um clique
- 💾 **Ultima Pasta Salva**: carrega automaticamente ao iniciar
- 📅 **Seleção Automática do Mais Recente**: ordena resultados por ano (mais recente primeiro)
- 🛡️ **Sanitização de Nomes**: remove caracteres inválidos (`:`, `/`, `\`, `|`, `<`, `>`, `?`, `*`, `"`) para compatibilidade Windows/Linux

## Requisitos

- Python 3.8+
- Windows 10+ (ou outro SO com suporte a Linux/macOS)

## Instalação

### 1. Clone ou Extraia o Projeto

```bash
cd KodiBot
```

### 2. Crie um Ambiente Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure a API Key do TMDB

1. Acesse [TheMovieDB](https://www.themoviedb.org/)
2. Crie uma conta (se não tiver)
3. Vá para Settings > API para gerar sua chave API

**Configuração Automática (Recomendado):**
- Execute o aplicativo
- Na primeira vez, uma janela solicitará sua API key
- Informe a chave e o aplicativo criará automaticamente o arquivo `.env`

**Configuração Manual (Opcional):**
4. Crie o arquivo `.env` na raiz do projeto
5. Edite o arquivo `.env` e substitua `sua_chave_aqui` pela sua chave real

```
TMDB_API_KEY=sua_chave_aqui
APP_LANGUAGE=pt-BR
```

## Uso

### Iniciar a Aplicação

```bash
# Windows
python main.py

# Linux/macOS
python3 main.py
```

### Como Usar

1. **Selecionar Pasta**: Clique em "Procurar Pasta" e selecione a pasta com seus arquivos
2. **Escolher Tipo**: Selecione "Filmes" ou "Series"
3. **Buscar**: Clique em "Buscar Filmes" (vale para ambos os tipos)
4. **Selecionar Resultado**: Clique na coluna "Selecao" para escolher outro resultado
5. **Renomear**: Clique em "Renomear Arquivos" para aplicar as mudancas

**Nota:** O aplicativo automaticamente seleciona o resultado mais recente (por ano de lançamento) quando há múltiplos resultados. Você pode clicar na coluna "Seleção" para escolher outra versão se necessário.

## Estrutura do Projeto

```
KodiBot/
├── main.py                    # Ponto de entrada
├── requirements.txt           # Dependências Python
├── .env                       # Configuracao (nao commitar)
└── src/
    ├── __init__.py
    ├── core/                  # Lógica principal
    │   ├── __init__.py
    │   ├── tmdb_client.py     # Cliente da API TMDB
    │   └── kodi_namer.py      # Lógica de renomeação Kodi
    └── ui/                    # Interface gráfica
        ├── __init__.py
        └── main_window.py     # Janela principal PyQt6
```

## Dependências Principais

- **requests**: Requisições HTTP para API TMDB
- **PyQt6**: Framework para interface gráfica
- **python-dotenv**: Gerencimento de variáveis de ambiente

## Formato de Nomenclatura Kodi

O aplicativo sugere nomes no padrao Kodi:

```
Titulo (YYYY).ext
```

**Sanitização Automática de Caracteres:**
O aplicativo remove automaticamente caracteres inválidos para sistemas de arquivos Windows/Linux:

```
Spider-Man: No Way Home (2021).mkv  →  Spider-Man No Way Home (2021).mkv
The Matrix: Reloaded (2003).mkv     →  The Matrix Reloaded (2003).mkv
Movie | Part 1 (2020).mp4           →  Movie Part 1 (2020).mp4
```

Caracteres removidos: `:` `/` `\` `|` `<` `>` `?` `*` `"`

## Troubleshooting

### "TMDB_API_KEY não configurada"
Certifique-se de que:
- Arquivo `.env` existe no diretório raiz
- A chave está corretamente preenchida
- Não há espaços extras antes ou depois da chave

**Atenção Windows**: Se o aplicativo não estiver salvando ou encontrando o arquivo `.env`:
- O aplicativo agora salva automaticamente a API key quando você a informa pela primeira vez
- O arquivo `.env` é criado automaticamente na raiz do projeto com encoding UTF-8
- Se o problema persistir, verifique se o usuário tem permissões de escrita na pasta do projeto
- Certifique-se de que nenhum antivírus está bloqueando a criação de arquivos `.env`

### "Nenhum resultado encontrado"
- Verifique se o nome do arquivo esta muito curto
- Tente outra selecao na coluna "Selecao"
- Ajuste `APP_LANGUAGE` se quiser resultados em pt-BR

### Erro de Conexão com TMDB
- Verifique sua conexão com internet
- Verifique se a API Key é válida
- TMDB pode estar momentaneamente indisponível

## Desenvolvimento

### Estrutura de Código

**tmdb_client.py**: Cliente para comunicacao com TMDB
- `search_movie()`: Busca filmes por titulo e ano
- `search_tv()`: Busca series por titulo e ano

**kodi_namer.py**: Logica de renomeacao
- `clean_filename()`: Limpa nome para busca no TMDB
- `format_kodi_name()`: Formata o nome no padrao Kodi
- `is_video_file()`: Valida extensoes de video

**main_window.py**: Interface grafica PyQt6
- Gerenciamento de pasta
- Busca em thread separada
- Selecionar resultado por linha

## Futuras Melhorias

- [ ] Renomeacao de episodios (S01E01)
- [ ] Backup automatico antes de renomear
- [ ] Desfazer ultima(s) renomeacao(oes)

## Licença

Este projeto é fornecido como está.

## Suporte

Para problemas ou sugestões, abra uma issue no repositório.

## Creditos

- [TheMovieDB](https://www.themoviedb.org/) - Banco de dados de midia
- [Kodi](https://kodi.tv/) - Media center
- [PyQt6](https://riverbankcomputing.com/software/pyqt/) - Framework GUI
