import qrcode
import io
import base64

# ---------------------------------------------------------
# SECCIÓN QR INCRUSTADO EN BASE64 (SÍNCRONO Y LOCAL)
# ---------------------------------------------------------
st.markdown("<br><hr style='border:1px solid rgba(255,34,34,0.2);'><br>", unsafe_allow_html=True)

st.markdown("""
    <div class='qr-container'>
        <h2 style='color:#ff2222; margin-bottom:5px; font-weight:800;'>📱 ¡Escanea o comparte para poner tu música!</h2>
        <p style='color:#cccccc; font-size:0.95rem; margin-top:0;'>Apunta con la cámara de tu teléfono o copia el enlace directo para enviarlo por WhatsApp.</p>
    </div>
""", unsafe_allow_html=True)

# URL objetivo de tu app (cámbiala por tu dominio público al desplegar en Streamlit Cloud)
URL_APP = "http://localhost:8501"

def generar_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

qr_b64 = generar_qr_base64(URL_APP)

html_qr = f"""
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    body {{
        background-color: transparent;
        color: #ffffff;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        text-align: center;
        margin: 0;
        padding: 10px;
    }}
    .qr-box {{
        background-color: #ffffff;
        padding: 14px;
        border-radius: 16px;
        display: inline-block;
        box-shadow: 0 0 20px rgba(255, 34, 34, 0.25);
        margin-top: 5px;
    }}
    .qr-box img {{
        display: block;
        width: 190px;
        height: 190px;
        border-radius: 6px;
    }}
    .url-text {{
        color: #a0a0a0;
        font-size: 0.85rem;
        margin-top: 12px;
        word-break: break-all;
        font-weight: 500;
    }}
    .btn-copy {{
        background-color: #25D366;
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 10px 18px;
        font-size: 0.9rem;
        font-weight: 700;
        cursor: pointer;
        margin-top: 12px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
    }}
</style>
</head>
<body>
    <div class="qr-box">
        <img src="data:image/png;base64,{qr_b64}" alt="Código QR">
    </div>
    <div class="url-text">{URL_APP}</div>
    <div>
        <button class="btn-copy" onclick="copiarEnlace()">
            <i class="fab fa-whatsapp"></i> Copiar enlace para WhatsApp
        </button>
    </div>

    <script>
        function copiarEnlace() {{
            navigator.clipboard.writeText("{URL_APP}").then(function() {{
                alert("¡Enlace copiado al portapapeles!");
            }}).catch(function() {{
                var dummy = document.createElement("input");
                document.body.appendChild(dummy);
                dummy.value = "{URL_APP}";
                dummy.select();
                document.execCommand("copy");
                document.body.removeChild(dummy);
                alert("¡Enlace copiado al portapapeles!");
            }});
        }}
    </script>
</body>
</html>
"""

components.html(html_qr, height=350)
