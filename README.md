# Renomeador de Filmes - TMDB

Aplicativo desktop desenvolvido em Python para renomear filmes automaticamente usando dados da API do TheMovieDB (TMDB), garantindo compatibilidade com Kodi.

## Funcionalidades

- 🔍 **Busca de Filmes**: Integração com API do TMDB para buscar informações precisas
- 📝 **Renomeação Automática**: Formata nomes conforme padrão Kodi (Movie Title (YYYY))
- 🎬 **Suporte Múltiplos Formatos**: mkv, mp4, avi, mov, flv, wmv, m4v
- 💻 **Interface Gráfica**: Moderna e intuitiva com PyQt6
- ⚡ **Thread de Busca**: Operações não-bloqueantes na UI

## Requisitos

- Python 3.8+
- Windows 10+ (ou outro SO com suporte a Linux/macOS)

## Instalação

### 1. Clone ou Extraia o Projeto

```bash
cd renomeadorFilmes
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
4. Copie o arquivo `.env.example` para `.env`
5. Edite o arquivo `.env` e substitua `your_api_key_here` pela sua chave real

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

1. **Selecionar Pasta**: Clique em "Procurar Pasta" e selecione a pasta com seus filmes
2. **Buscar Filme**: Digite o nome no campo de busca e clique em "Buscar"
3. **Selecionar Resultado**: Escolha o resultado correto na tabela de resultados
4. **Revisar Sugestões**: Os nomes sugeridos aparecerão na coluna "Nome Sugerido"
5. **Renomear**: Clique em "Renomear Selecionados" para aplicar as mudanças

## Estrutura do Projeto

```
renomeadorFilmes/
├── main.py                    # Ponto de entrada
├── requirements.txt           # Dependências Python
├── .env.example               # Exemplo de configuração
├── .env                       # Configuração (não commitado)
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

O aplicativo formata os nomes conforme padrão Kodi:

```
Film Title (YYYY).ext
```

**Exemplos:**
- `The Matrix (1999).mkv`
- `Inception (2010).mp4`
- `Interstellar (2014).avi`

## Troubleshooting

### "TMDB_API_KEY não configurada"
Certifique-se de que:
- Arquivo `.env` existe no diretório raiz
- A chave está corretamente preenchida
- Não há espaços extras antes ou depois da chave

### "Nenhum filme encontrado"
- Verifique a digitação do nome
- Tente buscar apenas pelo título principal
- Use o campo "Ano" para filtrar resultados

### Erro de Conexão com TMDB
- Verifique sua conexão com internet
- Verifique se a API Key é válida
- TMDB pode estar momentaneamente indisponível

## Desenvolvimento

### Estrutura de Código

**tmdb_client.py**: Cliente para comunicação com TMDB
- `search_movie()`: Busca filmes por título e ano
- `get_movie_details()`: Obtém informações detalhadas

**kodi_namer.py**: Lógica de renomeação
- `format_kodi_name()`: Formata o nome no padrão Kodi
- `is_video_file()`: Valida extensões de vídeo

**main_window.py**: Interface gráfica PyQt6
- Gerenciamento de pasta
- Busca em thread separada
- Preview de renomeação

## Futuras Melhorias

- [ ] Busca de legendas automática
- [ ] Criação de estrutura de pasta por gênero
- [ ] Edição em lote de metadados
- [ ] Suporte a séries de TV
- [ ] Backup automático antes de renomear
- [ ] Desfazer último(s) renomeação(ões)

## Licença

Este projeto é fornecido como está.

## Suporte

Para problemas ou sugestões, abra uma issue no repositório.

## Créditos

- [TheMovieDB](https://www.themoviedb.org/) - Banco de dados de filmes
- [Kodi](https://kodi.tv/) - Media center
- [PyQt6](https://riverbankcomputing.com/software/pyqt/) - Framework GUI
# KodiBot
