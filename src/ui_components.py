
def get_language_button():
    return """
        <style>
        .stButton > button {
            height: 100px !important;
        }
        .stButton > button p {
            font-size: 50px !important;
        }
        </style>
    """

def get_main_menu_text():
    return """
        <h1 style='text-align: center; margin-bottom: 20px;'>
            Choisis une langue pour jouer :
        </h1>
    """

def get_spinner_effect(status_text):
    return f"""
        <style>
        .spinner-container {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            z-index: 9999;
            background-color: rgba(255, 255, 255, 0.95);
        }}
        .spinner {{
            border: 8px solid #f3f3f3;
            border-top: 8px solid #3498db;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            animation: spin 1s linear infinite;
            margin-bottom: 30px;
        }}
        .status-text {{
            font-size: 18px;
            color: #333;
            font-weight: 500;
            text-align: center;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        <div class="spinner-container">
            <div class="spinner"></div>
            <div class="status-text">{status_text}</div>
        </div>
    """