# gemini_extractor.py

import re
from typing import Dict
import google.generativeai as genai
import json

GENAI_KEY = "AIzaSyCoLwTqTLIiA9hMCgguZmK2vLZKCrCROKc"
genai.configure(api_key=GENAI_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

PROMPT_DEFINITIONS = {
    "Nombres": {
        "prompt": "Extract all personal names mentioned in the text. Return a JSON array of unique names."
    },
    "Fechas": {
        "prompt": "Extract all dates mentioned in the text in any format. Return them in ISO format when possible (YYYY-MM-DD). Return a JSON array of dates."
    },
    "Lugares": {
        "prompt": "Extract all place names (cities, countries, neighborhoods, institutions) mentioned in the text. Return a JSON array of unique place names."
    },
    "Relaciones": {
        "prompt": "Identify and extract relationships between people mentioned in the text (e.g., mother, friend, spouse). Return a JSON array of relationship types or person-to-person relationships."
    },
    "Profesiones_u_Oficios": {
        "prompt": "Extract all professions, occupations, and job titles mentioned in the text. Return a JSON array of unique job-related terms."
    },
    "Nivel_Educativo": {
        "prompt": "Extract mentions of education level (e.g., primary school, college graduate, PhD). Return a JSON array of distinct educational levels."
    },
    "Instituciones_Educativas": {
        "prompt": "Extract names of educational institutions mentioned in the text (schools, universities, etc.). Return a JSON array of institutions."
    },
    "Religiones_y_Creenicas": {
        "prompt": "Extract mentions of religion, beliefs, or spiritual practices. Return a JSON array of belief systems."
    },
    "Ideologias_Politicas": {
        "prompt": "Extract mentions of political ideologies or affiliations. Return a JSON array of political ideas or parties."
    },
    "Lenguas": {
        "prompt": "Extract all languages mentioned in the text. Return a JSON array of language names."
    },
    "Grupos_Etnicos": {
        "prompt": "Extract mentions of ethnic groups, races, or cultural identities. Return a JSON array of group names."
    },
    "Discapacidades": {
        "prompt": "Extract mentions of physical, cognitive, or emotional disabilities. Return a JSON array of conditions."
    },
    "Condicion_Migratoria": {
        "prompt": "Extract references to immigration status (e.g., refugee, immigrant, undocumented). Return a JSON array of migration statuses."
    },
    "Pertenencia_Organizaciones": {
        "prompt": "Extract mentions of membership in organizations, unions, clubs, or collectives. Return a JSON array of organization names."
    },
    "Actividades_Sociales": {
        "prompt": "Extract social activities, leisure activities, and hobbies mentioned in the text. Return a JSON array of unique social activities."
    }
}

def extract_with_gemini(text: str, category: str) -> list:
    prompt = PROMPT_DEFINITIONS[category]["prompt"] + "\n\nThe text is:\n" + text
    try:
        response = model.generate_content(prompt)
        if not response.text:
            print(f"[WARN] Gemini no devolvió texto para la categoría '{category}'.")
            return None
        text_response = response.text.strip()
        
        try:
            if not text_response.startswith("["):
                text_response = re.search(r"\[.*\]", text_response, re.DOTALL).group()
            data = json.loads(text_response)
            return data if isinstance(data, list) else None
        except Exception as e:
            print(f"[ERROR] JSON inválido para categoría '{category}': {e}\nTexto devuelto:\n{text_response}")
            return None
    except Exception as e:
        print(f"[ERROR] Error de conexión Gemini en categoría '{category}': {e}")
        return None

def parse_text_enhanced(text: str) -> Dict:
    results = {}
    for category in PROMPT_DEFINITIONS:
        gemini_data = extract_with_gemini(text, category)
        if gemini_data:
            results[category] = gemini_data
        else:
            results[category] = "no mencionado"
    return results

def parse_file_enhanced(filepath: str, pid: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {
            "pid": pid,
            "archivo": filepath.split('/')[-1],
            "error": f"Error al leer archivo: {str(e)}"
        }

    info = parse_text_enhanced(content)
    info["pid"] = pid
    info["archivo"] = filepath.replace("\\", "/").split("/")[-1]
    return info
