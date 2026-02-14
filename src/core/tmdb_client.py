import os
from pathlib import Path
import requests
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class TMDBClient:
    """Cliente para interagir com a API do TheMovieDB"""
    
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self):
        # Recarrega o .env para pegar valores atualizados
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        self.api_key = os.getenv('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError("TMDB_API_KEY não configurada no arquivo .env")
        
    def search_movie(self, query, year=None):
        print(f"Buscando filme: {query}")
        """
        Busca um filme na base de dados do TMDB
        
        Args:
            query: Nome do filme a buscar
            year: Ano opcional do filme
            
        Returns:
            Lista de filmes encontrados
        """
        endpoint = f"{self.BASE_URL}/search/movie"
        params = {
            'api_key': self.api_key,
            'query': query,
            'language': os.getenv('APP_LANGUAGE', 'en')
        }
        
        if year:
            params['year'] = year
            
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            print(response.json())
            return response.json().get('results', [])
        except requests.RequestException as e:
            raise Exception(f"Erro ao buscar filme: {str(e)}")

    def search_tv(self, query, year=None):
        print(f"Buscando serie: {query}")
        """
        Busca uma serie na base de dados do TMDB
        
        Args:
            query: Nome da serie a buscar
            year: Ano opcional da serie (primeira exibicao)
            
        Returns:
            Lista de series encontradas
        """
        endpoint = f"{self.BASE_URL}/search/tv"
        params = {
            'api_key': self.api_key,
            'query': query,
            'language': os.getenv('APP_LANGUAGE', 'en')
        }
        
        if year:
            params['first_air_date_year'] = year
            
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            print(response.json())
            return response.json().get('results', [])
        except requests.RequestException as e:
            raise Exception(f"Erro ao buscar serie: {str(e)}")
    
    def get_movie_details(self, movie_id):
        """
        Obtém detalhes completos de um filme
        
        Args:
            movie_id: ID do filme no TMDB
            
        Returns:
            Dicionário com detalhes do filme
        """
        endpoint = f"{self.BASE_URL}/movie/{movie_id}"
        params = {
            'api_key': self.api_key,
            'language': os.getenv('APP_LANGUAGE', 'en')
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            print(response.json())
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Erro ao buscar detalhes: {str(e)}")

    def get_tv_details(self, tv_id):
        endpoint = f"{self.BASE_URL}/tv/{tv_id}"
        params = {
            'api_key': self.api_key,
            'language': os.getenv('APP_LANGUAGE', 'en')
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Erro ao buscar detalhes da serie: {str(e)}")

    def get_tv_season_details(self, tv_id, season_number):
        endpoint = f"{self.BASE_URL}/tv/{tv_id}/season/{season_number}"
        params = {
            'api_key': self.api_key,
            'language': os.getenv('APP_LANGUAGE', 'en')
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Erro ao buscar temporada: {str(e)}")
