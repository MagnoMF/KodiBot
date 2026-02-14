import re
import os

class KodiNamer:
    """Classe responsável por renomear arquivos de filmes para o formato Kodi"""
    
    # Formato padrão Kodi: Movie Title (YYYY)
    KODI_FORMAT = "{title} ({year})"
    
    # Extensões de vídeo suportadas
    VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.m4v']
    
    @staticmethod
    def clean_filename(filename):
        """Remove extensão e caracteres especiais do nome do arquivo e captura o ano"""
        name, _ = os.path.splitext(filename)
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", name)
        year = int(year_match.group(1)) if year_match else None
        name = name.replace('.', ' ').replace('-', ' ')
        clean_name = name.lower()
        
        clean_name = re.sub(
            r"\b(\d{3,4}p|\d{3,4}i|4k|uhd|hdr|10bit|dublado|dual|dual\s*audio|dual\s*5\.1|5\.1|camrip|webrip|web[-\s]?dl|web\s*rip|web|hdrip|brrip|blu\s*ray|bluray|remux|proper|repack|extended|unrated|dc|ltd|xvid|x264|x265|h264|h265|dvdrip|dvd|subs|hdcam|cam|ts|tc|r5)\b",
            " ",
            clean_name,
            flags=re.IGNORECASE,
        )
        clean_name = re.sub(r'\s+', ' ', clean_name)
        clean_name = re.sub(r'[^\w\s]', '', clean_name)
        # Remove qualquer numero do nome
        clean_name = re.sub(r"\d+", " ", clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name)
        return clean_name.strip(), year
    
    @staticmethod
    def format_kodi_name(title, year):
        """
        Formata o nome do filme para o padrão Kodi
        
        Args:
            title: Título do filme
            year: Ano de lançamento
            
        Returns:
            Nome formatado conforme padrão Kodi
        """
        return KodiNamer.KODI_FORMAT.format(title=title.strip(), year=year)
    
    @staticmethod
    def suggest_kodi_filename(original_filename, tmdb_title, tmdb_year):
        """
        Sugere um novo nome de arquivo compatível com Kodi
        
        Args:
            original_filename: Nome do arquivo original
            tmdb_title: Título do TMDB
            tmdb_year: Ano do TMDB
            
        Returns:
            Novo nome de arquivo sugerido
        """
        _, ext = os.path.splitext(original_filename)
        kodi_name = KodiNamer.format_kodi_name(tmdb_title, tmdb_year)
        return kodi_name + ext
    
    @staticmethod
    def is_video_file(filename):
        """Verifica se o arquivo é um vídeo suportado"""
        _, ext = os.path.splitext(filename)
        return ext.lower() in KodiNamer.VIDEO_EXTENSIONS
