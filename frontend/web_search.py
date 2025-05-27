import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import ollama
import time

class WebSearchHandler:
    def __init__(self):
        self.enabled = False
        self.max_results = 3
        self.last_search_time = 0
        self.last_search_failed = False
        
    def toggle_enabled(self, enabled: bool):
        self.enabled = enabled

    def perform_search(self, query: str) -> List[Dict]:
        self.last_search_failed = False
        if not self.enabled:
            return []

        current_time = time.time()
        if current_time - self.last_search_time < 2:
            time.sleep(2 - (current_time - self.last_search_time))
        self.last_search_time = time.time()

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
                'Accept-Language': 'ru-RU,ru;q=0.9'
            }
            
            response = requests.get(
                f"https://html.duckduckgo.com/html/?q={query}&kl=ru-ru",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            for result in soup.select('.result__body'):
                title_elem = result.select_one('.result__title a')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem and snippet_elem:
                    title = title_elem.text.strip()
                    snippet = snippet_elem.text.strip()
                    url = self._clean_ddg_url(title_elem.get('href', ''))
                    
                    if url and title and snippet:
                        results.append({
                            'title': title,
                            'url': url,
                            'content': snippet
                        })
                        if len(results) >= self.max_results * 2:
                            break
            
            return self._filter_relevant_results(query, results)[:self.max_results]
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            self.last_search_failed = True
            return []

    def _clean_ddg_url(self, url: str) -> str:
        if 'uddg=' in url:
            from urllib.parse import unquote
            return unquote(url.split('uddg=')[1])
        return url

    def _filter_relevant_results(self, query: str, results: List[Dict]) -> List[Dict]:
        if not results:
            return []

        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return results

        scored_results = []
        for result in results:
            text = f"{result['title']}\n{result['content']}"
            embedding = self._get_embedding(text)
            if not embedding:
                continue

            try:
                similarity = cosine_similarity([query_embedding], [embedding])[0][0]
                scored_results.append({
                    **result,
                    'similarity': similarity
                })
            except ValueError:
                continue

        return sorted(scored_results, key=lambda x: x['similarity'], reverse=True)

    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = ollama.embeddings(model='nomic-embed-text', prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return None
