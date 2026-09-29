# ---------------------------------------------------------
# SECCIÓN QR GENERADO LOCALMENTE (INMUNE A BLOQUEADORES)
# ---------------------------------------------------------
st.markdown("<br><hr style='border:1px solid rgba(255,34,34,0.2);'><br>", unsafe_allow_html=True)

st.markdown("""
    <div class='qr-container'>
        <h2 style='color:#ff2222; margin-bottom:5px; font-weight:800;'>📱 ¡Escanea o comparte para poner tu música!</h2>
        <p style='color:#cccccc; font-size:0.95rem; margin-top:0;'>Apunta con la cámara de tu teléfono o copia el enlace directo para enviarlo por WhatsApp.</p>
    </div>
""", unsafe_allow_html=True)

html_qr_autodetect = """
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<!-- Librería para renderizar el QR cliente/canvas localmente -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
    body {
        background-color: transparent;
        color: #ffffff;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        text-align: center;
        margin: 0;
        padding: 10px;
    }
    .qr-box {
        background-color: #ffffff;
        padding: 14px;
        border-radius: 16px;
        display: inline-block;
        box-shadow: 0 0 20px rgba(255, 34, 34, 0.25);
        margin-top: 5px;
    }
    #qrcode canvas, #qrcode img {
        margin: 0 auto;
        border-radius: 6px;
        display: block;
    }
    .url-text {
        color: #a0a0a0;
        font-size: 0.85rem;
        margin-top: 12px;
        word-break: break-all;
        max-width: 90%;
        margin-left: auto;
        margin-right: auto;
        font-weight: 500;
    }
    .btn-copy {
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
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
    }
    .btn-copy:hover {
        background-color: #20ba5a;
        transform: translateY(-1px);
    }
</style>
</head>
<body>
    <div class="qr-box">
        <div id="qrcode"></div>
    </div>
    <div class="url-text" id="url-display">Cargando enlace...</div>
    <div>
        <button class="btn-copy" onclick="copiarEnlace()">
            <i class="fab fa-whatsapp"></i> Copiar enlace para WhatsApp
        </button>
    </div>

    <script>
        var actualUrl = "";

        function obtenerUrlReal() {
            var url = "";
            try {
                if (window.top !== window.self && document.referrer) {
                    url = document.referrer;
                }
            } catch (e) {}

            if (!url || url.indexOf("about:") === 0 || url === "null") {
                try {
                    if (window.parent && window.parent.location && window.parent.location.href) {
                        url = window.parent.location.href;
                    }
                } catch(e) {}
            }

            if (!url || url.indexOf("about:") === 0 || url === "null") {
                url = window.location.href;
            }

            if (url) {
                url = url.split('?')[0].split('#')[0];
            }

            if (!url || url.indexOf("about:") === 0 || url === "null" || url.indexOf("blob:") === 0) {
                var host = window.location.host;
                if (host && host !== "null") {
                    url = window.location.protocol + "//" + host;
                } else {
                    url = "http://localhost:8501";
                }
            }
            return url;
        }

        actualUrl = obtenerUrlReal();
        document.getElementById('url-display').innerText = actualUrl;

        function generarQR() {
            var qrContainer = document.getElementById("qrcode");
            qrContainer.innerHTML = "";
            new QRCode(qrContainer, {
                text: actualUrl,
                width: 200,
                height: 200,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.H
            });
        }

        // Ejecutar renderizado
        if (typeof QRCode !== 'undefined') {
            generarQR();
        } else {
            // Cargar de CDN secundario si el principal estuviera bloqueado
            var s = document.createElement('script');
            s.src = "https://cdn.jsdelivr.net/gh/davidshimjs/qrcodejs/qrcode.min.js";
            s.onload = generarQR;
            document.head.appendChild(s);
        }

        function copiarEnlace() {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(actualUrl).then(function() {
                    alert("¡Enlace copiado al portapapeles!\nPégalo en WhatsApp.");
                }).catch(function() {
                    fallbackCopy();
                });
            } else {
                fallbackCopy();
            }
        }

        function fallbackCopy() {
            var dummy = document.createElement("input");
            document.body.appendChild(dummy);
            dummy.value = actualUrl;
            dummy.select();
            document.execCommand("copy");
            document.body.removeChild(dummy);
            alert("¡Enlace copiado al portapapeles!\nPégalo en WhatsApp.");
        }
    </script>
</body>
</html>
"""

components.html(html_qr_autodetect, height=350)
