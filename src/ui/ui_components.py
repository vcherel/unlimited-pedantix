
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

def get_spinner_effect(status_text: str):
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

def get_winner_style():
    return """
        <style>
        .winbar {
            background: linear-gradient(135deg, #66ff99, #33cc7a);
            border-radius: 20px;
            padding: 1.2rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2rem;
            box-shadow: 0 8px 24px rgba(102,255,153,0.4);
            margin-bottom: 2rem;
        }
        .winbar .big {
            font-size: 2.2rem;
            font-weight: 800;
            color: #fff;
            text-shadow: 0 2px 4px rgba(0,0,0,.25);
        }
        .winbar a.wiki {
            font-size: 1.6rem;
            color: #fff;
            text-decoration: none;
            border: 2px solid #fff;
            border-radius: 12px;
            padding: .4rem 1rem;
            transition: .25s;
        }
        .winbar a.wiki:hover {
            background: #fff;
            color: #33cc7a;
        }
    """

def get_winner_bar(title: str, nb_guesses: int, url: str):
    return f"""
        <div class="winbar">
            <div class="big">🎉 Bravo !!! L'article était : <b>{title}</b></div>
            <div class="big">Essais : {nb_guesses}</div>
            <a class="wiki" href="{url}" target="_blank">Voir sur Wikipédia</a>
        </div>
    """

def get_text_input():
    return """
            <style>
            /* Fix text input at bottom */
            div[data-testid="stTextInput"] {
                position: fixed !important;
                bottom: 1.5rem !important;
                left: 12% !important;
                transform: translateX(-50%) !important;
                z-index: 999999 !important;
                padding: 10px 12px !important;
                border-radius: 12px !important;
                background: white !important;
                box-shadow: 0 6px 18px rgba(0,0,0,0.15) !important;
                width: 350px !important;
            }

            /* Input field styling */
            div[data-testid="stTextInput"] input {
                font-size: 18px !important;
                padding: 10px 14px !important;
                background: white !important;
                border-radius: 10px !important;
            }

            /* Leave space at bottom so content isn't hidden */
            .appview-container, .block-container, .main {
                padding-bottom: 120px !important;
            }

            /* Hide "Press Enter to Apply" */
            div[data-testid="InputInstructions"] > span:nth-child(1) {
                visibility: hidden !important;
            }
            </style>
            """

def get_keyboard_focus():
    return r"""<script>
        const setupAutoFocus = () => {
            const parentDoc = window.parent.document;
            const input = parentDoc.querySelector('input[aria-label="input"]');
            
            if (!input) {
                setTimeout(setupAutoFocus, 100);
                return;
            }
            
            // Focus immediately
            input.focus();
            
            // Capture keyboard events
            parentDoc.addEventListener('keydown', (e) => {
                // Skip if modifier keys are pressed
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                
                const active = parentDoc.activeElement;
                if (active && active !== input && 
                    (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || 
                    active.tagName === 'BUTTON' || active.isContentEditable)) {
                    return;
                }
                
                // Allow only letters and numbers
                const allowed = /^\p{L}|\p{N}$/u;
                if (e.key.length === 1 && !allowed.test(e.key)) {
                    e.preventDefault(); // Block the key
                } else if (e.key === 'Backspace' || e.key === 'Delete') {
                    // Allow deletion
                    input.focus();
                } else if (e.key.length === 1) {
                    input.focus();
                }
            }, true);
            
            // Keep refocusing
            setInterval(() => {
                const active = parentDoc.activeElement;
                if (!active || (active.tagName !== 'INPUT' && active.tagName !== 'BUTTON' && 
                                active.tagName !== 'TEXTAREA')) {
                    input.focus();
                }
            }, 500);
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupAutoFocus);
        } else {
            setupAutoFocus();
        }
        </script>
    """

def get_guess_feedback(color, content):
    return f"""
        <style>
        .feedback-box {{
            position: fixed;
            bottom: 1.5rem;
            left: 400px;
            max-width: 1500px;
            z-index: 999999;
            background: rgba(255,255,255,0.95);
            padding: 0.95rem 1.2rem;
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
            font-size: 1.2rem;
            font-weight: 500;
            min-height: 50px;
        }}
        .feedback-box p {{
            margin: 0;
        }}
        </style>
        <div class="feedback-box">
            <p style='color:{color}'>{content}</p>
        </div>
    """

def get_main_menu_button():
    return """
        <style>
        .stButton > button {
            height: 60px !important;
        }
        .stButton > button p {
            font-size: 25px !important;
        }
        </style>
    """
