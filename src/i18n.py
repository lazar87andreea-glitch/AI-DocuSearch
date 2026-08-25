"""
Internationalization (i18n) module for AI DocuSearch.
Detects user language from browser Accept-Language header or IP geolocation,
and provides translation utilities.
"""

import os
import json
from typing import Optional, Dict
import streamlit as st

# Translation dictionary - add more languages/translations as needed
TRANSLATIONS = {
    "en": {
        "title": "AI DocuSearch",
        "description": "Don't remember what a document is all about? Upload your document, ask a question, and get instant answers using AI.",
        "upload_prompt": "Upload a PDF, DOCX or TXT file",
        "file_saved": "📁 File saved",
        "extracting": "⏳ Extracting text from document...",
        "extracted": "✅ Extracted",
        "chars": "chars",
        "mb": "MB",
        "pages": "pages",
        "in": "in",
        "seconds": "s",
        "ask_question": "Ask a question about the document...",
        "processing": "⏳ Processing your question...",
        "completed": "✅",
        "document_info": "Document Info",
        "positive": "Positive",
        "negative": "Negative",
        "upload_first": "👆 Please upload a document to get started",
        "failed_save": "❌ Failed to save file",
        "failed_extract": "❌ Failed to extract text",
        "ocr_note": "⚠️ **Note on scanned PDFs**",
        "ocr_tip": "📌 **Tip**: For best results, use PDFs with selectable text",
    },
    "ro": {
        "title": "AI DocuSearch",
        "description": "Nu-ți amintești ce conține un document? Încarcă documentul tău, pune o întrebare și obține răspunsuri instantanee folosind IA.",
        "upload_prompt": "Încarcă un fișier PDF, DOCX sau TXT",
        "file_saved": "📁 Fișier salvat",
        "extracting": "⏳ Se extrage textul din document...",
        "extracted": "✅ Extras",
        "chars": "caractere",
        "mb": "MB",
        "pages": "pagini",
        "in": "în",
        "seconds": "s",
        "ask_question": "Pune o întrebare despre document...",
        "processing": "⏳ Se procesează întrebarea...",
        "completed": "✅",
        "document_info": "Informații document",
        "positive": "Pozitiv",
        "negative": "Negativ",
        "upload_first": "👆 Te rog, încarcă mai întâi un document",
        "failed_save": "❌ Eșec la salvarea fișierului",
        "failed_extract": "❌ Eșec la extragerea textului",
        "ocr_note": "⚠️ **Notă privind PDF-urile scanate**",
        "ocr_tip": "📌 **Sfat**: Pentru rezultate optime, folosește PDF-uri cu text selectabil",
    },
    "fr": {
        "title": "AI DocuSearch",
        "description": "Vous ne vous souvenez pas de quoi parle un document? Téléchargez votre document, posez une question et obtenez des réponses instantanées en utilisant l'IA.",
        "upload_prompt": "Télécharger un fichier PDF, DOCX ou TXT",
        "file_saved": "📁 Fichier enregistré",
        "extracting": "⏳ Extraction du texte du document...",
        "extracted": "✅ Extrait",
        "chars": "caractères",
        "mb": "MB",
        "pages": "pages",
        "in": "en",
        "seconds": "s",
        "ask_question": "Posez une question sur le document...",
        "processing": "⏳ Traitement de votre question...",
        "completed": "✅",
        "document_info": "Informations du document",
        "positive": "Positif",
        "negative": "Négatif",
        "upload_first": "👆 Veuillez d'abord télécharger un document",
        "failed_save": "❌ Échec de la sauvegarde du fichier",
        "failed_extract": "❌ Échec de l'extraction du texte",
        "ocr_note": "⚠️ **Remarque sur les PDF numérisés**",
        "ocr_tip": "📌 **Conseil**: Pour de meilleurs résultats, utilisez des PDF avec du texte sélectionnable",
    },
    "es": {
        "title": "AI DocuSearch",
        "description": "¿No recuerdas de qué trata un documento? Carga tu documento, haz una pregunta y obtén respuestas instantáneas usando IA.",
        "upload_prompt": "Carga un archivo PDF, DOCX o TXT",
        "file_saved": "📁 Archivo guardado",
        "extracting": "⏳ Extrayendo texto del documento...",
        "extracted": "✅ Extraído",
        "chars": "caracteres",
        "mb": "MB",
        "pages": "páginas",
        "in": "en",
        "seconds": "s",
        "ask_question": "Haz una pregunta sobre el documento...",
        "processing": "⏳ Procesando tu pregunta...",
        "completed": "✅",
        "document_info": "Información del documento",
        "positive": "Positivo",
        "negative": "Negativo",
        "upload_first": "👆 Por favor, carga un documento primero",
        "failed_save": "❌ Error al guardar el archivo",
        "failed_extract": "❌ Error al extraer el texto",
        "ocr_note": "⚠️ **Nota sobre PDF escaneados**",
        "ocr_tip": "📌 **Consejo**: Para mejores resultados, usa PDF con texto seleccionable",
    },
    "de": {
        "title": "AI DocuSearch",
        "description": "Erinnerst du dich nicht, worum es in einem Dokument geht? Lade dein Dokument hoch, stelle eine Frage und erhalte sofortige Antworten mit KI.",
        "upload_prompt": "PDF-, DOCX- oder TXT-Datei hochladen",
        "file_saved": "📁 Datei gespeichert",
        "extracting": "⏳ Text aus Dokument wird extrahiert...",
        "extracted": "✅ Extrahiert",
        "chars": "Zeichen",
        "mb": "MB",
        "pages": "Seiten",
        "in": "in",
        "seconds": "s",
        "ask_question": "Stelle eine Frage zum Dokument...",
        "processing": "⏳ Verarbeitung deiner Frage...",
        "completed": "✅",
        "document_info": "Dokumentinformationen",
        "positive": "Positiv",
        "negative": "Negativ",
        "upload_first": "👆 Bitte laden Sie zunächst ein Dokument hoch",
        "failed_save": "❌ Fehler beim Speichern der Datei",
        "failed_extract": "❌ Fehler beim Extrahieren des Textes",
        "ocr_note": "⚠️ **Hinweis zu gescannten PDFs**",
        "ocr_tip": "📌 **Tipp**: Verwenden Sie für beste Ergebnisse PDF mit auswählbarem Text",
    },
}


def detect_language_from_header() -> Optional[str]:
    """Detect language from browser Accept-Language header."""
    try:
        # Try to get Accept-Language header from Streamlit context
        from streamlit.server.server import Server
        server = Server.get_current()
        if server and hasattr(server, '_session_state'):
            headers = getattr(server, 'headers', {})
            if isinstance(headers, dict):
                accept_lang = headers.get('Accept-Language', '')
                if accept_lang:
                    # Parse Accept-Language: en-US,en;q=0.9,fr;q=0.8
                    langs = [lang.split('-')[0].lower() for lang in accept_lang.split(',')]
                    for lang in langs:
                        if lang.strip() in TRANSLATIONS:
                            return lang.strip()
    except Exception:
        pass
    return None


def detect_language_from_ip() -> Optional[str]:
    """Detect language from user IP using free API (fallback)."""
    try:
        import requests
        # Use free IP geolocation API
        response = requests.get('http://ip-api.com/json/?fields=countryCode', timeout=2)
        if response.status_code == 200:
            data = response.json()
            country_code = data.get('countryCode', '').lower()
            
            # Map country codes to languages
            country_to_lang = {
                'ro': 'ro',  # Romania -> Romanian
                'fr': 'fr',  # France -> French
                'es': 'es',  # Spain -> Spanish
                'de': 'de',  # Germany -> German
                'at': 'de',  # Austria -> German
                'ch': 'de',  # Switzerland -> German (primary)
                'be': 'fr',  # Belgium -> French
                'gb': 'en',  # UK -> English
                'us': 'en',  # USA -> English
            }
            lang = country_to_lang.get(country_code)
            if lang in TRANSLATIONS:
                return lang
    except Exception:
        pass
    return None


def get_user_language() -> str:
    """
    Detect user language with fallback chain:
    1. Cached in session state
    2. Browser Accept-Language header
    3. IP geolocation
    4. Default to English
    """
    if "user_language" not in st.session_state:
        # Try Accept-Language header first (most accurate)
        lang = detect_language_from_header()
        
        # Fall back to IP geolocation
        if not lang:
            lang = detect_language_from_ip()
        
        # Default to English
        if not lang:
            lang = "en"
        
        st.session_state.user_language = lang
        print(f"[i18n] Detected language: {lang}", flush=True)
    
    return st.session_state.user_language


def translate(key: str, default: Optional[str] = None) -> str:
    """
    Get translated text for a key in the user's language.
    
    Args:
        key: Translation key (e.g., "upload_prompt")
        default: Fallback text if key not found
    
    Returns:
        Translated text
    """
    lang = get_user_language()
    text = TRANSLATIONS.get(lang, {}).get(key, None)
    
    if text is None:
        # Fall back to English if not found in user's language
        text = TRANSLATIONS.get("en", {}).get(key, None)
    
    if text is None:
        # Fall back to provided default or key itself
        text = default or key
    
    return text


def set_language(language_code: str) -> None:
    """Allow user to manually override language."""
    if language_code in TRANSLATIONS:
        st.session_state.user_language = language_code
    else:
        raise ValueError(f"Unsupported language: {language_code}")


def get_supported_languages() -> Dict[str, str]:
    """Get list of supported languages."""
    return {
        "en": "English",
        "ro": "Română",
        "fr": "Français",
        "es": "Español",
        "de": "Deutsch",
    }


def add_language_selector_sidebar() -> None:
    """Add language selector to Streamlit sidebar."""
    with st.sidebar:
        st.markdown("### 🌍 Language / Limbă")
        current_lang = get_user_language()
        supported = get_supported_languages()
        
        selected_lang = st.selectbox(
            "Select language",
            options=list(supported.keys()),
            format_func=lambda x: f"{supported[x]} ({x.upper()})",
            index=list(supported.keys()).index(current_lang),
            key="language_selector"
        )
        
        if selected_lang != current_lang:
            set_language(selected_lang)
            st.rerun()
